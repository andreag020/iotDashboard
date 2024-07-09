import json
import logging
import os

import pyrebase
from dotenv import load_dotenv
from flask import Flask, flash, redirect, render_template, request, url_for, jsonify
from flask_cors import CORS
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_socketio import SocketIO, emit, join_room

from model.app_model import get_tuya_devices, create_user, get_devices_for_user, get_all_users, \
    update_device_status_tuya, db

# Load environment variables from the .env file
load_dotenv()

# Initialize the Flask application
app = Flask(__name__)
# Configure the secret key for session management
app.secret_key = os.getenv("SECRET_KEY")
# Initialize the login manager
login_manager = LoginManager()
login_manager.init_app(app)
# Configure CORS to allow requests from localhost:5000
CORS(app, origins=["http://localhost:5000"])
# Initialize SocketIO for real-time communication
socketio = SocketIO(app)

# Initialize Firebase app with configuration from a JSON file
pb = pyrebase.initialize_app(json.load(open('model/firebase/iot-dashboard-firebase.json')))

# Get all users from the database
users = get_all_users()


# Define the User class for user handling with Flask-Login
class User(UserMixin):
    pass


# Define the function to load a user by their ID
@login_manager.user_loader
def user_loader(user_id):
    user = User()
    user.id = user_id
    return user


# Route for handling login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('login.html')
    if request.method == "POST":
        email = request.form['email']
        password = request.form['password']
        try:
            user = pb.auth().sign_in_with_email_and_password(email, password)
            if user:
                user_obj = User()
                user_obj.id = user['localId']
                login_user(user_obj)
                return redirect(url_for('dashboard'))
        except Exception as e:
            flash('Invalid email or password')
            return redirect(url_for('login'))


# Route to display the dashboard with devices
@app.route('/dashboard')
@login_required  # Require login to access this route
def dashboard():
    return render_template('dashboard.html')


# Route to display the dashboard with devices
@app.route('/devices')
@login_required  # Require login to access this route
def devices():
    devices_tuya = get_tuya_devices()
    devices_db = get_devices_for_user(current_user.id)
    return render_template('index.html', devices_tuya=devices_tuya, devices_db=devices_db)

@app.route('/consumption')
@login_required  # Require login to access this route
def consumption():
    # Aquí puedes obtener datos reales de consumo si es necesario
    return render_template('consumption.html')

# Route for handling logout
@app.route('/logout', methods=['GET', 'POST'])
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


# Route for registering new users
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        # Check if passwords match
        if password != confirm_password:
            error = "Passwords do not match"
            return render_template('registration.html', error=error)

        try:
            # Create the user
            user_id = create_user(email, password)
            user = User()
            user.id = user_id
            login_user(user)
            return redirect(url_for('dashboard'))
        except Exception as e:
            error = f"An error occurred: {e}"
            return render_template('registration.html', error=error)
    else:
        return render_template('registration.html')


# Route to get updated devices for the current user
@app.route('/get_updated_devices')
@login_required  # Require login to access this route
def get_updated_devices():
    devices_db = get_devices_for_user(current_user.id)
    return jsonify(devices_db=devices_db)


# Route to update the status of a device
@app.route('/update_device_status', methods=['POST'])
@login_required  # Require login to access this route
def update_device_status():
    device_id = request.form['device_id']
    new_status = request.form['new_status'] == 'true'

    try:
        response = update_device_status_tuya(device_id, new_status)
        if response:
            device_ref = db.collection('Device').document(device_id)
            device_ref.update({'status': [{'code': 'switch_1', 'value': new_status}]})
            devices_db = get_devices_for_user(current_user.id)
            socketio.emit('updated_devices', {'devices_db': devices_db}, namespace='/', room=current_user.id)
            return jsonify(success=True)
        else:
            return jsonify(success=False, error="Failed to update status in Tuya")
    except Exception as e:
        logging.error(f"Error updating device status: {e}")
        return jsonify(success=False, error=str(e))


# Function to handle device updates from Firestore
def on_device_update(docs, changes, read_time):
    for change in changes:
        if change.type.name == 'MODIFIED':
            device = change.document.to_dict()
            user_id = device.get('user_id')
            if user_id:
                current_status = device['status'][0]['value']
                devices_db = get_devices_for_user(user_id)
                # Emit dashboard update
                socketio.emit('updated_devices', {'devices_db': devices_db}, namespace='/', room=user_id)

                # Check if the status has actually changed before sending the POST request
                device_ref = db.collection('Device').document(device['id'])
                device_doc = device_ref.get()
                if device_doc.exists:
                    stored_status = device_doc.to_dict()['status'][0]['value']
                    if stored_status != current_status:
                        update_device_status_tuya(device['id'], current_status)
                    else:
                        # If the status hasn't changed, still send the POST request to ensure synchronization
                        update_device_status_tuya(device['id'], current_status)


# Register Firestore listener for updates in the 'Device' collection
db.collection('Device').on_snapshot(on_device_update)


# Handle new client connections via SocketIO
@socketio.on('connect')
def handle_connect():
    if current_user and current_user.is_authenticated:
        join_room(current_user.id)
        devices_db = get_devices_for_user(current_user.id)
        emit('updated_devices', {'devices_db': devices_db})
    else:
        logging.warning("No authenticated user found for handle_connect")


# Root route that redirects to log in or dashboard depending on user's authentication status
@app.route('/')
def index():
    if not current_user.is_authenticated:
        return redirect(url_for('login'))
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    else:
        return redirect(url_for('login'))


# Run the Flask application with support for SocketIO
if __name__ == '__main__':
    socketio.run(app, debug=True)
