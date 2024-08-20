import json
import locale
import logging
import os
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_DOWN
import pyrebase
from dotenv import load_dotenv
from flask import Flask, flash, redirect, render_template, request, url_for, jsonify
from flask_cors import CORS
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_socketio import SocketIO, emit, join_room

from model.app_model import get_tuya_devices, create_user, get_devices_for_user, get_all_users, \
    update_device_status_tuya, calculate_daily_energy, get_total_energy_consumption, \
    get_device_type, calculate_daily_co2_emissions, get_total_emission, get_device_watts_and_time_for_months, \
    calculate_energy_savings, calculate_economic_savings, get_available_months, db

# Establecer la localización en español para que los nombres de los meses sean en español
locale.setlocale(locale.LC_TIME, 'es_ES.UTF-8')
# Obtener la fecha actual y los meses correspondientes
today = datetime.today()
current_month = today.strftime('%B').capitalize()  # Obtener el mes actual en español y capitalizar
previous_month = (today.replace(day=1) - timedelta(days=1)).strftime(
    '%B').capitalize()  # Obtener el mes anterior en español y capitalizar

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


@app.route('/dashboard')
@login_required  # Require login to access this route
def dashboard():
    total_energy = get_total_energy_consumption(year='2024', months=[current_month])
    total_emissions = get_total_emission(year='2024', months=[current_month])
    devices_info = get_device_watts_and_time_for_months(year='2024', months=[previous_month, current_month])
    total_energy_by_month, energy_savings = calculate_energy_savings(devices_info,
                                                                     months=[previous_month, current_month])
    # Calcular los ahorros económicos
    total_cost_by_month, economic_savings = calculate_economic_savings(devices_info,
                                                                       months=[previous_month, current_month],
                                                                       price_per_kwh=0.10)
    # Truncar los ahorros de energía y económicos a dos decimales
    energy_savings = float(Decimal(energy_savings).quantize(Decimal('0.00'), rounding=ROUND_DOWN))
    economic_savings = float(Decimal(economic_savings).quantize(Decimal('0.00'), rounding=ROUND_DOWN))

    return render_template('dashboard.html', total_energy=total_energy, total_emissions=total_emissions,
                           total_energy_by_month=total_energy_by_month,
                           energy_savings=energy_savings, total_cost_by_month=total_cost_by_month,
                           economic_savings=economic_savings)


@app.route('/devices')
@login_required  # Require login to access this route
def devices():
    devices_tuya = get_tuya_devices()
    devices_db = get_devices_for_user(current_user.id)
    device_types = get_device_type()

    # Pasar la información de los tipos de dispositivos a la plantilla
    return render_template('devices.html', devices_tuya=devices_tuya, devices_db=devices_db, device_types=device_types)


#########################RUTA PARA CONSUMO ENERGÉTICO#########################
@app.route('/consumption')
@login_required  # Require login to access this route
def consumption():
    # Obtener los valores de los parámetros GET, o usar el mes actual si no está presente
    selected_month = request.args.get('month', current_month)
    # Obtener los meses disponibles
    available_months = get_available_months(year='2024')
    # Obtener los datos de watts y tiempos para el mes seleccionado
    devices_info = get_device_watts_and_time_for_months(year='2024', months=[selected_month])
    # Calcular el consumo diario de energía para cada dispositivo
    for device in devices_info:
        device['energy_kwh'] = calculate_daily_energy(device['watts'], device['times'][selected_month])

    # Pasar la data al template
    return render_template('consumption.html',
                           devices_info=devices_info,
                           available_months=available_months,
                           selected_month=selected_month)


#########################RUTA EMISIONES DE CO2#########################
@app.route('/emissions')
@login_required  # Require login to access this route
def emissions():
    # Obtener los parámetros del mes seleccionado o usar un mes predeterminado
    selected_month = request.args.get('month', current_month)  # Usa el mes actual como predeterminado

    # Obtener los datos de watts y tiempos para el mes seleccionado
    devices_info = get_device_watts_and_time_for_months(year='2024', months=[selected_month])

    # Calcular el consumo de energía diaria y las emisiones de CO2 para cada dispositivo
    for device in devices_info:
        device['energy_kwh'] = calculate_daily_energy(device['watts'], device['times'][selected_month])
        device['co2_emissions'] = calculate_daily_co2_emissions(device['energy_kwh'])

    # Calcular las emisiones totales de CO2 por día
    if devices_info:
        num_days = len(devices_info[0]['times'][selected_month])
        total_co2_emissions_per_day = [0] * num_days
        for day_index in range(num_days):
            total_co2_emissions_per_day[day_index] = sum(device['co2_emissions'][day_index] for device in devices_info)
    else:
        total_co2_emissions_per_day = []

    # Obtener los meses disponibles
    available_months = get_available_months(year='2024')

    return render_template('emissions.html',
                           total_co2_emissions_per_day=total_co2_emissions_per_day,
                           available_months=available_months,
                           selected_month=selected_month)


########## RUTA PARA AHORRO ENERGÉTICO ########

@app.route('/energy_savings', methods=['GET'])
def energy_savings():
    # Obtener los valores de los parámetros GET, o usar los valores por defecto si no están presentes
    month1 = request.args.get('month1', previous_month)
    month2 = request.args.get('month2', current_month)

    available_months = get_available_months(year='2024')
    # Obtener los datos de watts y tiempos para los meses seleccionados
    devices_info = get_device_watts_and_time_for_months(year='2024', months=[month1, month2])

    # Calcular los ahorros de energía
    total_energy_by_month, energy_savings = calculate_energy_savings(devices_info, months=[month1, month2])

    return render_template('energy_savings.html',
                           total_energy_by_month=total_energy_by_month,
                           energy_savings=energy_savings,
                           available_months=available_months,
                           month1=month1,
                           month2=month2)


################## RUTA PARA AHORRO ECONOMICO ################
@app.route('/economic_savings', methods=['GET'])
@login_required
def economic_savings():
    # Obtener los valores de los parámetros GET, o usar los valores por defecto si no están presentes
    month1 = request.args.get('month1', previous_month)
    month2 = request.args.get('month2', current_month)

    available_months = get_available_months(year='2024')
    # Obtener los datos de watts y tiempos para los meses seleccionados
    devices_info = get_device_watts_and_time_for_months(year='2024', months=[month1, month2])

    # Calcular los ahorros económicos
    total_cost_by_month, economic_savings = calculate_economic_savings(devices_info, months=[month1, month2],
                                                                       price_per_kwh=0.10)

    return render_template('economic_savings.html',
                           total_cost_by_month=total_cost_by_month,
                           economic_savings=economic_savings,
                           available_months=available_months,
                           month1=month1,
                           month2=month2)


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


# Function to handle device updates
def on_device_update(docs, changes, read_time):
    for change in changes:
        if change.type.name == 'MODIFIED':
            device = change.document.to_dict()
            user_id = device.get('user_id')
            if user_id:
                current_status = device['status'][0]['value']
                devices_db = get_devices_for_user(user_id)

                # Emitir actualización al dashboard
                socketio.emit('updated_devices', {'devices_db': devices_db}, namespace='/', room=user_id)

                # Verificar el estado almacenado en la base de datos
                device_ref = db.collection('Device').document(device['id'])
                device_doc = device_ref.get()
                if device_doc.exists:
                    stored_status = device_doc.to_dict()['status'][0]['value']
                    update_device_status_tuya(device['id'], current_status)


# Register Firestore listener for updates in the 'Device' collection
db.collection('Device').on_snapshot(on_device_update)


# Function to emit graph updates
def emit_graph_updates(user_id):
    year = '2024'
    selected_months = [current_month, previous_month]

    # Consumption Data
    devices_info = get_device_watts_and_time_for_months(year=year, months=selected_months)
    total_energy_by_month, energy_savings = calculate_energy_savings(devices_info, months=selected_months)
    socketio.emit('updated_consumption', {'devices_info': devices_info}, namespace='/', room=user_id)

    # Emissions Data
    total_co2_emissions_per_day = []
    for device in devices_info:
        if 'energy_kwh' in device:
            daily_emissions = calculate_daily_co2_emissions(device['energy_kwh'])
            total_co2_emissions_per_day.append(daily_emissions)
    socketio.emit('updated_emissions', {'total_co2_emissions_per_day': total_co2_emissions_per_day}, namespace='/',
                  room=user_id)

    # Economic Savings
    total_cost_by_month, economic_savings = calculate_economic_savings(devices_info, months=selected_months,
                                                                       price_per_kwh=0.10)
    socketio.emit('updated_economic_savings',
                  {'total_cost_by_month': total_cost_by_month, 'economic_savings': economic_savings}, namespace='/',
                  room=user_id)

    # Energy Savings
    socketio.emit('updated_energy_savings',
                  {'total_energy_by_month': total_energy_by_month, 'energy_savings': energy_savings}, namespace='/',
                  room=user_id)


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
