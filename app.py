import logging
import os

from firebase_admin import auth, exceptions
from flask import Flask, render_template, request, redirect, url_for, send_from_directory
from dotenv import load_dotenv
from model.app_model import get_tuya_devices, get_firestore_devices, create_user, add_device_to_user, \
    get_devices_for_user, get_all_users, get_all_types
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import json
from flask import Flask, flash, redirect, render_template, request, session, abort, url_for
from flask import jsonify
import pyrebase
from flask_cors import CORS
from tuya_connector import TuyaOpenAPI, TUYA_LOGGER
from model.app_model import get_active_time_by_hour

load_dotenv()

#app = Flask(__name__, static_folder='frontend/build/static', template_folder='frontend/build')
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")
login_manager = LoginManager()
login_manager.init_app(app)
CORS(app)
CORS(app, origins=["http://localhost:5000"])


class User(UserMixin):
    pass


pb = pyrebase.initialize_app(json.load(open('model/firebase/iot-dashboard-firebase.json')))

users = get_all_users()


ACCESS_ID = "3ujca7y7apppqpcjjmdt"
ACCESS_KEY = "e719ad0396c74b64bad8510c8baa491c"
API_ENDPOINT = "https://openapi.tuyaus.com"
#DEVICE_ID = "vdevo170000581142241"

@login_manager.user_loader
def user_loader(user_id):
    if user_id not in users:
        return
    user = User()
    user.id = user_id
    return user


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        print('Cargar la pagina')
        return render_template('login.html')
    if request.method == "POST":  # Only if data has been posted
        print('Procesar la informacion')
        email = request.form['email']
        password = request.form['password']
        print(email, password)
        try:
            # Try signing in the user with the given information
            print('Intentar iniciar sesion')
            user = pb.auth().sign_in_with_email_and_password(email, password)
            # print(user)
            if user:
                user_obj = User()
                user_obj.id = user['localId']  # use the user id from the response
                login_user(user_obj)  # log the user in
                return redirect('/dashboard')
        except Exception as e:
            # If there is any error, redirect back to login and display the error
            flash('Usuario o contraseña incorrectos')
            print(e)  # print the error to the console for debugging
            return redirect(url_for('login'))


@app.route('/dashboard')
@login_required
def dashboard():
    print('Usuario autenticado')
    devices_tuya = get_tuya_devices()
    devices_db = get_devices_for_user(current_user.id)  # Get devices for the authenticated user
    return render_template('index.html', devices_tuya=devices_tuya, devices_db=devices_db)


@app.route('/logout', methods=['GET', 'POST'])
def logout():
    logout_user()
    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user_id = create_user(email, password)
        user = User()
        user.id = user_id
        login_user(user)
        return redirect(url_for('dashboard'))
    else:
        return render_template('registration.html')

@app.route('/assets/<path:path>')
def serve_assets(path):
    return send_from_directory(app.static_folder + '/assets', path)

@app.route('/static/<path:path>')
def serve_static_files(path):
    return send_from_directory(app.static_folder, path)

# @app.route('/')
# @app.route('/<path:path>')
# def serve_react_app(path=None):
#     if path and (path.startswith('static') or path.startswith('assets') or '.' in path):
#         return send_from_directory(app.static_folder, path)
#     return send_from_directory(app.template_folder, 'index.html')
@app.route('/')
def index():
    if not current_user.is_authenticated:
        '''user_id = create_user('newuser@example.com', 'password123')
        user = User()
        user.id = user_id
        login_user(user)'''
        return redirect(url_for('login'))
    if current_user.is_authenticated:
        # user_id = create_user('andrea0202@example.com', 'password123')
        # device_id = 'device1'  # Replace with the actual device ID
        # add_device_to_user('', {'prueba': 'Funciona!'})
        return redirect(url_for('dashboard'))
    else:
        return redirect(url_for('login'))


@app.route('/add_device', methods=['GET', 'POST'])
@login_required
def add_device():
    if request.method == 'POST':
        device_name = request.form['device_name']
        device_type = request.form['device_type']
        add_device_to_user(current_user.id, device_name, device_type)
        return redirect(url_for('dashboard'))
    else:
        types = get_all_types()
        return render_template('add_device.html', types=types)


@app.route('/get_updated_devices')
@login_required
def get_updated_devices():
    devices_db = get_devices_for_user(current_user.id)
    return jsonify(devices_db=devices_db)


@app.route('/update_device_status', methods=['POST'])
@login_required
def update_device_status():
    from model.app_model import db, update_device_status_tuya  # Import the Firestore client and the new function

    device_id = request.form['device_id']
    new_status = request.form['new_status'] == 'true'  # Convert the string to a boolean

    try:
        # Update the device status in Tuya
        response = update_device_status_tuya(device_id, new_status)
        if response:
            # If the POST request was successful, update the device status in Firestore
            device_ref = db.collection('Device').document(device_id)
            device_ref.update({'status': [{'code': 'switch_1', 'value': new_status}]})
            return jsonify(success=True)
        else:
            return jsonify(success=False, error="Failed to update status in Tuya")
    except Exception as e:
        logging.error(f"Error updating device status: {e}")
        return jsonify(success=False, error=str(e))


'''def initialize_app():
    user_id = create_user('andrea@example.com', 'password123')
    add_device_to_user(user_id, {'device_name': 'Device 1', 'device_type': 'Type 1'})
    devices = get_devices_for_user(user_id)

    for device in devices:
        print(f"Device ID: {device.id}, Device Info: {device.to_dict()}")'''


@app.route('/get_data', methods=['GET'])
def get_data():
    # Aquí debes obtener los datos de tu base de datos
    data = {
        'labels': ['January', 'February', 'March', 'April', 'May', 'June'],
        'data': [65, 59, 80, 81, 56, 55]
    }
    return jsonify(data)


@app.route('/get_device_data', methods=['GET'])
@login_required
def get_device_data():
    devices = get_devices_for_user(current_user.id)
    device_data = [{'id': device['id'], 'labels': ['January', 'February', 'March', 'April', 'May', 'June'], 'data': [65, 59, 80, 81, 56, 55]} for device in devices]
    return jsonify(device_data=device_data)


@app.route('/get_active_time_by_hour', methods=['GET'])
@login_required
def active_time_by_hour():
    data = get_active_time_by_hour(current_user.id)
    return jsonify(data)


if __name__ == '__main__':
    app.run(debug=True)
