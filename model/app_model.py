# app_model.py

import locale
import logging
import os

from datetime import datetime, timedelta

import firebase_admin
from firebase_admin import firestore, credentials, auth
from flask_login import LoginManager, current_user
from flask_login import UserMixin
from google.cloud.firestore_v1.base_query import FieldFilter

from tuya_connector import TuyaOpenAPI, TUYA_LOGGER


# Establecer la localización en español para que los nombres de los meses sean en español
locale.setlocale(locale.LC_TIME, 'es_ES.UTF-8')
# Obtener la fecha actual y los meses correspondientes
today = datetime.today()
current_month = today.strftime('%B').capitalize()  # Obtener el mes actual en español y capitalizar
previous_month = (today.replace(day=1) - timedelta(days=1)).strftime(
    '%B').capitalize()  # Obtener el mes anterior en español y capitalizar

# Fetch the service account key JSON file contents
cred = credentials.Certificate('model/firebase/iot-dashboard-firebase.json')

# Get the database URL from environment variables
database_url = os.getenv("DATABASE_URL")

# Initialize the app with a service account, granting admin privileges
firebase_admin.initialize_app(cred, {
    'databaseURL': database_url
})

# Initialize Firestore
db = firestore.client()

# Initialize the login manager
login_manager = LoginManager()


class User(UserMixin):
    pass


def get_firestore_devices():
    try:
        # Get reference to the "Device" collection
        devices_ref = db.collection('Device')

        # Fetch all documents in the collection
        devices = devices_ref.stream()

        # List to store device IDs
        device_ids = []

        # Iterate over each document and get its ID
        for device in devices:
            device_id = device.id
            device_ids.append(device_id)

        return device_ids
    except Exception as e:
        print("Error retrieving devices from Firestore:", e)
        return []


def create_user(email, password):
    user = auth.create_user(email=email, password=password)
    return user.uid


def get_all_users():
    # Get a reference to the auth service
    auth = firebase_admin.auth

    # Get the first page of users
    page = auth.list_users()

    # List to store user IDs
    user_ids = []

    # Iterate over all users in the page
    for user in page.iterate_all():
        user_ids.append(user.uid)

    return user_ids


def get_all_types():
    # Get reference to the "Type" collection
    types_ref = db.collection('Type')

    # Fetch all documents in the collection
    types = types_ref.stream()

    # List to store types
    type_list = [{'id': type_.id, 'name': type_.to_dict()['name']} for type_ in types]
    return type_list


@login_manager.user_loader
def user_loader(user_id):
    user = auth.get_user(user_id)
    if user:
        user_obj = User()
        user_obj.id = user.uid
        return user_obj
    return None


def add_device_to_firestore(device_id, device_info):
    # Add or update a device in Firestore
    device_ref = db.collection('Device').document(device_id)
    device_ref.set(device_info, merge=True)

        # Fetch all documents in the collection
        devices = devices_ref.stream()

        # List to store device IDs
        device_ids = []

        # Iterate over each document and get its ID
        for device in devices:
            device_id = device.id
            device_ids.append(device_id)

        return device_ids
    except Exception as e:
        print("Error retrieving devices from Firestore:", e)
        return []

def create_user(email, password):
    user = auth.create_user(email=email, password=password)
    return user.uid

def get_all_users():
    # Get a reference to the auth service
    auth = firebase_admin.auth

    # Get the first page of users
    page = auth.list_users()

    # List to store user IDs
    user_ids = []

    # Iterate over all users in the page
    for user in page.iterate_all():
        user_ids.append(user.uid)

    return user_ids

def get_all_types():
    # Get reference to the "Type" collection
    types_ref = db.collection('Type')

    # Fetch all documents in the collection
    types = types_ref.stream()

    # List to store types
    type_list = [{'id': type_.id, 'name': type_.to_dict()['name']} for type_ in types]
    return type_list

@login_manager.user_loader
def user_loader(user_id):
    user = auth.get_user(user_id)
    if user:
        user_obj = User()
        user_obj.id = user.uid
        return user_obj
    return None

def add_device_to_firestore(device_id, device_info):
    # Add or update a device in Firestore
    device_ref = db.collection('Device').document(device_id)
    device_ref.set(device_info, merge=True)

def get_tuya_devices():
    TUYA_LOGGER.setLevel(logging.DEBUG)
    openapi = TuyaOpenAPI(os.getenv("API_ENDPOINT"), os.getenv("ACCESS_ID"), os.getenv("ACCESS_KEY"))
    openapi.connect()

    # Get all devices
    response = openapi.get("/v2.0/cloud/thing/device?page_size=3")

    # List to store device IDs
    device_ids = []

    # Extract and store the device ID for each device in the list
    for device in response.get("result", []):
        device_id = device.get("id")
        device_info = device

        # Make a GET request to the device's URL
        device_status_response = openapi.get("/v1.0/iot-03/devices/{}/status".format(device_id))

        # Store the response in Firebase
        if device_status_response.get('success', False):
            device_status = device_status_response.get('result', {})
            device_info['status'] = device_status  # Assume the device status is in 'result'
        else:
            device_info['status'] = {}  # If the request fails, assume the device has no status

        # Check if the device already exists in Firebase
        device_ref = db.collection('Device').document(device_id)
        device_doc = device_ref.get()

        if device_doc.exists:
            # If the device exists, update only the fields obtained from the Tuya API
            device_ref.update(device_info)
        else:
            # If the device does not exist, add it to the database with the current user's ID
            device_info['user_id'] = current_user.id
            device_info['customName'] = device_info.get('customName', device_info.get('name'))  # Add customName field
            device_ref.set(device_info)

        device_ids.append(device_id)

    return device_ids

def add_device_to_user(user_id, device_name, device_type):
    # Add a new device for the user in Firestore
    device_ref = db.collection('Device').document()
    device_ref.set({'name': device_name, 'type': device_type, 'user_id': user_id, 'is_active': False})

def add_device_to_user(user_id, device_name, device_type):
    # Add a new device for the user in Firestore
    device_ref = db.collection('Device').document()
    device_ref.set({'name': device_name, 'type': device_type, 'user_id': user_id, 'is_active': False})


def get_devices_for_user(user_id):
    # Get all devices for a specific user
    devices_ref = db.collection('Device')
    devices = devices_ref.where(filter=FieldFilter('user_id', '==', user_id)).stream()
    device_list = [{'id': device.id, **device.to_dict()} for device in devices]
    return device_list


# Obtener numero de dispositivos por usuario
def get_device_count_for_user(user_id):
    try:
        # Get reference to the "Device" collection
        devices_ref = db.collection('Device')
        devices = devices_ref.where(filter=FieldFilter('user_id', '==', user_id)).stream()
        device_count = sum(1 for _ in devices)  # Count the number of devices
        return device_count
    except Exception as e:
        print("Error counting devices for user:", e)
        return 0


def update_device_status_tuya(device_id, new_status):
    TUYA_LOGGER.setLevel(logging.DEBUG)
    openapi = TuyaOpenAPI(os.getenv("API_ENDPOINT"), os.getenv("ACCESS_ID"), os.getenv("ACCESS_KEY"))
    openapi.connect()

    # Get the current status of the device
    device_status_response = openapi.get(f"/v1.0/iot-03/devices/{device_id}/status")

    if device_status_response.get('success', False):
        device_status = device_status_response.get('result', {})

        # Find the command codes for switch_1 and switch_led
        command_codes = [d['code'] for d in device_status if d['code'] in ['switch_1', 'switch_led']]

        if not command_codes:
            logging.error(f"Neither switch_1 nor switch_led found in device {device_id} status")
            return False

        # Create commands for each found command code
        commands = {"commands": [{"code": code, "value": new_status} for code in command_codes]}
        response = openapi.post(f'/v1.0/iot-03/devices/{device_id}/commands', commands)

        if response.get('success', False):
            return True
        else:
            logging.error(f"Failed to update device {device_id} status: {response}")
            return False
    else:
        logging.error(f"Failed to get device {device_id} status: {device_status_response}")
        return False


def get_device_watts_and_time():
    try:
        # Get reference to the "Device" collection
        devices_ref = db.collection('Device')

        # Fetch all documents in the collection
        devices = devices_ref.stream()

        # List to store watts and time for each device
        devices_info = []

        # Iterate over each document and get the required fields
        for device in devices:
            device_data = device.to_dict()
            watts = device_data.get('watts', 0)  # Default to 0 if not found
            times = device_data.get('times', {})  # Default to empty dict if not found

            # Initialize time array
            time_array = []

            if times:
                # Navigate to the specific month (e.g., July 2024)
                time_array = times.get('2024', {}).get("Julio", [])

            # Append the info to the list
            devices_info.append({
                'id': device.id,
                'watts': watts,
                'time': time_array  # Use the time array for the specific month
            })

        return devices_info
    except Exception as e:
        print("Error retrieving device information from Firestore:", e)
        return []


# Función para calcular las emeisiones diariaqs de carbono
def calculate_daily_co2_emissions(energy_kwh_array, emission_factor=0.5015):
    try:
        co2_emissions_array = [energy_kwh * emission_factor for energy_kwh in energy_kwh_array]
        return co2_emissions_array
    except Exception as e:
        print("Error calculating daily CO2 emissions:", e)
        return []


# Function to get the total energy consumption for specific months
def get_total_energy_consumption(year='2024', months=None):
    try:
        # Obtener la información de los dispositivos para los meses y año especificados
        devices_info = get_device_watts_and_time_for_months(year=year, months=months)
        total_energy = 0

        # Iterar sobre cada dispositivo y calcular el consumo total de energía
        for device in devices_info:
            for month in months:
                daily_energy = calculate_daily_energy(device['watts'], device['times'][month])
                total_energy += sum(
                    daily_energy)  # Sumar la energía diaria para obtener el total de energía por dispositivo

        total_energy = round(total_energy, 2)  # Redondear a dos decimales
        return total_energy
    except Exception as e:
        print("Error calculating total energy consumption:", e)
        return 0


def get_total_emission(year='2024', months=None):
    try:
        # Obtener la información de los dispositivos para los meses y año especificados
        devices_info = get_device_watts_and_time_for_months(year=year, months=months)
        total_emissions = 0

        for device in devices_info:
            # Obtener los tiempos del mes especificado
            time_array = device['times'][months[0]]  # Suponiendo que solo pasas un mes en la lista
            daily_energy = calculate_daily_energy(device['watts'], time_array)
            daily_emissions = calculate_daily_co2_emissions(daily_energy)
            total_emissions += sum(daily_emissions)  # Sumar las emisiones diarias para obtener el total por dispositivo

        total_emissions = round(total_emissions, 2)  # Redondear a dos decimales
        return total_emissions
    except Exception as e:
        print("Error calculating total CO2 emissions:", e)
        return 0


# Funcion para obtener el tipo de dispositivo por su id
def get_device_type():
    try:
        # Get reference to the "Device" collection
        devices_ref = db.collection('Device')

        # Fetch all documents in the collection
        devices = devices_ref.stream()

        # List to store watts and time for each device
        devices_info = []

        # Iterate over each document and get the required fields
        for device in devices:
            device_data = device.to_dict()
            type = device_data.get('type')

            # Append the info to the list
            devices_info.append({
                'id': device.id,
                'type': type,
            })

        return devices_info
    except Exception as e:
        print("Error retrieving device information from Firestore:", e)
        return []


def get_device_watts_and_time_for_months(year='2024', months=None):
    try:
        devices_ref = db.collection('Device')
        devices = devices_ref.stream()
        devices_info = []

        for device in devices:
            device_data = device.to_dict()
            watts = device_data.get('watts', 0)
            times = device_data.get('times', {})

            # Si no se especifican meses, tomar todos los disponibles
            if not months:
                available_months = times.get(year, {}).keys()
                monthly_times = {month: times.get(year, {}).get(month, []) for month in available_months}
            else:
                monthly_times = {month: times.get(year, {}).get(month, []) for month in months}

            devices_info.append({
                'id': device.id,
                'watts': watts,
                'times': monthly_times
            })

        return devices_info
    except Exception as e:
        print("Error retrieving device information from Firestore:", e)
        return []


###################################################################
# Function to calculate daily energy consumption
def calculate_daily_energy(watts, time_array):
    try:
        energy_array = [watts * time for time in time_array]  # Energy in watt-hours (Wh) for each day
        energy_kwh_array = [energy / 1000 for energy in energy_array]  # Convert Wh to kWh
        return energy_kwh_array
    except Exception as e:
        print("Error calculating daily energy consumption:", e)
        return []


def calculate_energy_savings(devices_info, months=['Month1', 'Month2']):
    try:
        total_energy_by_month = {month: 0 for month in months}

        for device in devices_info:
            for month in months:
                daily_energy = calculate_daily_energy(device['watts'], device['times'][month])
                total_energy_by_month[month] += sum(daily_energy)

        energy_savings = total_energy_by_month[months[0]] - total_energy_by_month[months[1]]
        return total_energy_by_month, energy_savings
    except Exception as e:
        print("Error calculating energy savings:", e)
        return {}, 0


def calculate_economic_cost(energy_kwh_array, price_per_kwh=0.10):
    try:
        cost_array = [energy_kwh * price_per_kwh for energy_kwh in energy_kwh_array]
        return cost_array
    except Exception as e:
        print("Error calculating economic cost:", e)
        return []


def calculate_economic_savings(devices_info, months=['Junio', 'Julio'], price_per_kwh=0.10):
    try:
        total_cost_by_month = {month: 0 for month in months}

        for device in devices_info:
            for month in months:
                daily_energy = calculate_daily_energy(device['watts'], device['times'][month])
                total_energy = sum(daily_energy)
                monthly_cost = total_energy * price_per_kwh
                total_cost_by_month[month] += monthly_cost

        economic_savings = total_cost_by_month[months[0]] - total_cost_by_month[months[1]]
        return total_cost_by_month, economic_savings
    except Exception as e:
        print("Error calculating economic savings:", e)
        return {}, 0


# FUNICON PARA OBTENER LOS MESES DISPONIBLES
def get_available_months(year='2024'):
    try:
        devices_ref = db.collection('Device')
        devices = devices_ref.stream()
        months_set = set()

        for device in devices:
            device_data = device.to_dict()
            times = device_data.get('times', {})

            # Añadir los meses disponibles en el año especificado al conjunto
            available_months = times.get(year, {}).keys()
            months_set.update(available_months)

        return sorted(months_set)
    except Exception as e:
        print("Error retrieving available months from Firestore:", e)
        return []

def calculate_economic_savings(devices_info, months=['Junio', 'Julio'], price_per_kwh=0.10):
    try:
        total_cost_by_month = {month: 0 for month in months}

        for device in devices_info:
            for month in months:
                daily_energy = calculate_daily_energy(device['watts'], device['times'][month])
                total_energy = sum(daily_energy)
                monthly_cost = total_energy * price_per_kwh
                total_cost_by_month[month] += monthly_cost

        economic_savings = total_cost_by_month[months[0]] - total_cost_by_month[months[1]]
        return total_cost_by_month, economic_savings
    except Exception as e:
        print("Error calculating economic savings:", e)
        return {}, 0

    