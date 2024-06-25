import json
import logging
import os

import pyrebase
from dotenv import load_dotenv
from flask import Flask, flash, redirect, render_template, request, url_for, jsonify
from flask_cors import CORS
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_socketio import SocketIO, emit, join_room

from model.app_model import get_tuya_devices, create_user, add_device_to_user, get_devices_for_user, get_all_users, get_all_types, update_device_status_tuya, db

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")
login_manager = LoginManager()
login_manager.init_app(app)
CORS(app, origins=["http://localhost:5000"])
socketio = SocketIO(app)

pb = pyrebase.initialize_app(json.load(open('model/firebase/iot-dashboard-firebase.json')))

users = get_all_users()

class User(UserMixin):
    pass

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
                return redirect('/dashboard')
        except Exception as e:
            flash('Usuario o contraseña incorrectos')
            return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    devices_tuya = get_tuya_devices()
    devices_db = get_devices_for_user(current_user.id)
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


def on_device_update(docs, changes, read_time):
    for change in changes:
        if change.type.name == 'MODIFIED':
            device = change.document.to_dict()
            user_id = device.get('user_id')
            if user_id:
                current_status = device['status'][0]['value']
                devices_db = get_devices_for_user(user_id)
                # Emitir actualización del dashboard
                socketio.emit('updated_devices', {'devices_db': devices_db}, namespace='/', room=user_id)

                # Verificar si el estado ha cambiado realmente antes de enviar la solicitud POST
                device_ref = db.collection('Device').document(device['id'])
                device_doc = device_ref.get()
                if device_doc.exists:
                    stored_status = device_doc.to_dict()['status'][0]['value']
                    if stored_status != current_status:
                        update_device_status_tuya(device['id'], current_status)
                    else:
                        # Si el estado no ha cambiado, igual enviar la solicitud POST para asegurar la sincronización
                        update_device_status_tuya(device['id'], current_status)


# Register Firestore listener
db.collection('Device').on_snapshot(on_device_update)

@socketio.on('connect')
def handle_connect():
    if current_user and current_user.is_authenticated:
        join_room(current_user.id)
        devices_db = get_devices_for_user(current_user.id)
        emit('updated_devices', {'devices_db': devices_db})
    else:
        logging.warning("No authenticated user found for handle_connect")

@app.route('/')
def index():
    if not current_user.is_authenticated:
        return redirect(url_for('login'))
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    else:
        return redirect(url_for('login'))

if __name__ == '__main__':
    socketio.run(app, debug=True)
