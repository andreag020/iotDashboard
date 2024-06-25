# app_model.py

import logging
import firebase_admin
import os
import  requests
from tuya_connector import TuyaOpenAPI, TUYA_LOGGER
from firebase_admin import firestore, credentials, auth, exceptions
from flask_login import LoginManager, UserMixin, current_user
from google.cloud.firestore_v1.base_query import FieldFilter
from flask_login import UserMixin
import datetime

# Fetch the service account key JSON file contents
cred = credentials.Certificate('model/firebase/iot-dashboard-firebase.json')

database_url = os.getenv("DATABASE_URL")

# Initialize the app with a service account, granting admin privileges
firebase_admin.initialize_app(cred, {
    'databaseURL': database_url
})

db = firestore.client()

login_manager = LoginManager()


class User(UserMixin):
    pass


'''def get_tuya_devices():
    TUYA_LOGGER.setLevel(logging.DEBUG)
    openapi = TuyaOpenAPI(API_ENDPOINT, ACCESS_ID, ACCESS_KEY)
    openapi.connect()

    # Get the info of one device with ID
    # response = openapi.get("/v1.0/iot-03/devices/{}".format(DEVICE_ID))

    # Get all devices
    response = openapi.get("/v2.0/cloud/thing/device?page_size=3")

    # Lista para almacenar los IDs de los dispositivos
    device_ids = []

    # Extraer e almacenar el ID del dispositivo para cada dispositivo en la lista
    for device in response.get("result", []):
        device_id = device.get("id")
        device_ids.append(device_id)

    return device_ids'''


def get_firestore_devices():
    try:
        # Get reference to the "Device" collection
        devices_ref = db.collection('Device')

        # Fetch all documents in the collection
        devices = devices_ref.stream()

        # Lista para almacenar los IDs de los dispositivos
        device_ids = []

        # Recorrer cada documento y obtener su ID
        for device in devices:
            device_id = device.id
            device_ids.append(device_id)

        return device_ids
    except Exception as e:
        print("Error al obtener los dispositivos de Firestore:", e)
        return []


def create_user(email, password):
    user = auth.create_user(email=email, password=password)
    return user.uid


def get_all_users():
    # Get a reference to the auth service
    auth = firebase_admin.auth

    # Get the first page of users
    page = auth.list_users()

    # List to store the emails
    user_ids = []

    # Iterate over all users in the page
    for user in page.iterate_all():
        user_ids.append(user.uid)

    return user_ids


'''def add_device_to_user(user_id, device_info):
    device_info['user_id'] = user_id
    device_ref = db.collection('Device').document(device_info)
    device_ref.update({'user_id': user_id})'''


'''def add_device_to_user(user_id, device_name, device_type):
    device_ref = db.collection('Device').document()
    device_ref.set({'name': device_name, 'type': device_type, 'user_id': user_id})


def get_devices_for_user(user_id):
    devices_ref = db.collection('Device')
    devices = devices_ref.where(filter=FieldFilter('user_id', '==', user_id)).stream()
    device_list = [{'id': device.id, **device.to_dict()} for device in devices]
    return device_list'''


'''def get_devices_for_user(user_id):
    devices_ref = db.collection('Device')
    devices = devices_ref.where(filter=FieldFilter('user_id', '==', user_id)).stream()
    device_list = [device.to_dict() for device in devices]
    return device_list'''


def get_all_types():
    types_ref = db.collection('Type')
    types = types_ref.stream()
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
    device_ref = db.collection('Device').document(device_id)
    device_ref.set(device_info, merge=True)


'''def get_tuya_devices():
    TUYA_LOGGER.setLevel(logging.DEBUG)
    openapi = TuyaOpenAPI(API_ENDPOINT, ACCESS_ID, ACCESS_KEY)
    openapi.connect()

    # Get all devices
    response = openapi.get("/v2.0/cloud/thing/device?page_size=3")

    # Lista para almacenar los IDs de los dispositivos
    device_ids = []

    # Extraer e almacenar el ID del dispositivo para cada dispositivo en la lista
    for device in response.get("result", []):
        device_id = device.get("id")
        device_info = device  # Aquí pasamos todo el objeto device a la función add_device_to_firestore()
        device_info[
            'user_id'] = current_user.id  # Aquí asumimos que current_user es una variable global que contiene el usuario actual
        add_device_to_firestore(device_id, device_info)
        device_ids.append(device_id)

    return device_ids'''


def get_tuya_devices():
    TUYA_LOGGER.setLevel(logging.DEBUG)
    openapi = TuyaOpenAPI(os.getenv("API_ENDPOINT"), os.getenv("ACCESS_ID"), os.getenv("ACCESS_KEY"))
    openapi.connect()

    # Get all devices
    response = openapi.get("/v2.0/cloud/thing/device?page_size=3")

    # Lista para almacenar los IDs de los dispositivos
    device_ids = []

    # Extraer e almacenar el ID del dispositivo para cada dispositivo en la lista
    for device in response.get("result", []):
        device_id = device.get("id")
        device_info = device

        # Realizar la solicitud GET a la URL del dispositivo
        device_status_response = openapi.get("/v1.0/iot-03/devices/{}/status".format(device_id))

        # Almacenar la respuesta de la solicitud en Firebase
        if device_status_response.get('success', False):
            device_status = device_status_response.get('result', {})
            device_info['status'] = device_status  # Aquí asumimos que el estado del dispositivo se encuentra en 'result'
        else:
            device_info['status'] = {}  # Si la solicitud no es exitosa, asumimos que el dispositivo no tiene estado

            # Verificar si el dispositivo ya existe en Firebase
            device_ref = db.collection('Device').document(device_id)
            device_doc = device_ref.get()

            if device_doc.exists:
                # Si el dispositivo ya existe, actualizamos solo los campos que obtenemos de la API de Tuya
                device_ref.update(device_info)
            else:
                # Si el dispositivo no existe, lo agregamos a la base de datos con el user_id del usuario actual
                device_info['user_id'] = current_user.id
                device_info['customName'] = device_info.get('customName', device_info.get(
                    'name'))  # Aquí agregamos el campo customName
                device_ref.set(device_info)

            device_ids.append(device_id)

        return device_ids

    return device_ids


def add_device_to_user(user_id, device_name, device_type):
    device_ref = db.collection('Device').document()
    device_ref.set({'name': device_name, 'type': device_type, 'user_id': user_id, 'is_active': False})


def get_devices_for_user(user_id):
    devices_ref = db.collection('Device')
    devices = devices_ref.where(filter=FieldFilter('user_id', '==', user_id)).stream()
    device_list = [{'id': device.id, **device.to_dict()} for device in devices]
    return device_list


# def update_device_status_tuya(device_id, new_status):
#     TUYA_LOGGER.setLevel(logging.DEBUG)
#     openapi = TuyaOpenAPI(API_ENDPOINT, ACCESS_ID, ACCESS_KEY)
#     openapi.connect()
#
#     commands = {"commands":[{"code":"switch_led","value":new_status}]}
#     response = openapi.post(f'/v1.0/iot-03/devices/{device_id}/commands', commands)
#
#     if response.get('success', False):
#         return True
#     else:
#         logging.error(f"Failed to update device {device_id} status: {response}")
#         return False
# ... (rest of the code)

def update_device_status_tuya(device_id, new_status):
    TUYA_LOGGER.setLevel(logging.DEBUG)
    openapi = TuyaOpenAPI(os.getenv("API_ENDPOINT"), os.getenv("ACCESS_ID"), os.getenv("ACCESS_KEY"))
    openapi.connect()

    device_status_response = openapi.get(f"/v1.0/iot-03/devices/{device_id}/status")

    if device_status_response.get('success', False):
        device_status = device_status_response.get('result', {})
        command_code = next((d['code'] for d in device_status if d['code'] in ['switch_1', 'switch_led']), None)

        if not command_code:
            logging.error(f"Neither switch_1 nor switch_led found in device {device_id} status")
            return False

        commands = {"commands": [{"code": command_code, "value": new_status}]}
        response = openapi.post(f'/v1.0/iot-03/devices/{device_id}/commands', commands)

        if response.get('success', False):
            return True
        else:
            logging.error(f"Failed to update device {device_id} status: {response}")
            return False
    else:
        logging.error(f"Failed to get device {device_id} status: {device_status_response}")
        return False


def get_active_time_by_hour(user_id):
    devices_ref = db.collection('Device').where('user_id', '==', user_id)
    devices = devices_ref.stream()

    active_time_by_hour = {hour: 0 for hour in range(24)}
    device_names = {hour: [] for hour in range(24)}

    for device in devices:
        device_data = device.to_dict()
        if 'activeTime' in device_data and 'createTime' in device_data:
            active_time = device_data['activeTime']
            create_time = device_data['createTime']
            device_name = device_data.get('name', 'Unknown Device')

            create_time_datetime = datetime.datetime.fromtimestamp(create_time)
            hour = create_time_datetime.hour

            active_time_hours = active_time / 3600  # Convertir a horas

            active_time_by_hour[hour] += active_time_hours
            if device_name not in device_names[hour]:
                device_names[hour].append(device_name)

    return {
        'labels': [f'{hour}:00' for hour in range(24)],  # Etiquetas para cada hora
        'data': list(active_time_by_hour.values()),
        'device_names': {hour: ', '.join(device_names[hour]) for hour in range(24)}
    }
