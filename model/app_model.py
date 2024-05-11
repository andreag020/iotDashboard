# app_model.py

import logging
import firebase_admin
from tuya_connector import TuyaOpenAPI, TUYA_LOGGER
from firebase_admin import firestore, credentials, auth, exceptions
from flask_login import LoginManager, UserMixin
from google.cloud.firestore_v1.base_query import FieldFilter
from flask_login import UserMixin

# Fetch the service account key JSON file contents
cred = credentials.Certificate('model/firebase/iot-dashboard-firebase.json')

# Initialize the app with a service account, granting admin privileges
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://console.firebase.google.com/project/iot-dashboard-737c8/firestore'
})

ACCESS_ID = "3ujca7y7apppqpcjjmdt"
ACCESS_KEY = "e719ad0396c74b64bad8510c8baa491c"
API_ENDPOINT = "https://openapi.tuyaus.com"
DEVICE_ID = "vdevo170000581142241"

db = firestore.client()

login_manager = LoginManager()


class User(UserMixin):
    pass


def get_tuya_devices():
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

    return device_ids


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


def add_device_to_user(user_id, device_name, device_type):
    device_ref = db.collection('Device').document()
    device_ref.set({'name': device_name, 'type': device_type, 'user_id': user_id})


'''def get_devices_for_user(user_id):
    devices_ref = db.collection('Device')
    devices = devices_ref.where(filter=FieldFilter('user_id', '==', user_id)).stream()
    device_list = [device.to_dict() for device in devices]
    return device_list'''


def get_devices_for_user(user_id):
    devices_ref = db.collection('Device')
    devices = devices_ref.where(filter=FieldFilter('user_id', '==', user_id)).stream()
    device_list = [{'id': device.id, **device.to_dict()} for device in devices]
    return device_list


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
