# app_model.py

import logging
import os

import firebase_admin
from firebase_admin import firestore, credentials, auth
from flask_login import LoginManager, current_user
from flask_login import UserMixin
from google.cloud.firestore_v1.base_query import FieldFilter

from tuya_connector import TuyaOpenAPI, TUYA_LOGGER

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


def get_devices_for_user(user_id):
    # Get all devices for a specific user
    devices_ref = db.collection('Device')
    devices = devices_ref.where(filter=FieldFilter('user_id', '==', user_id)).stream()
    device_list = [{'id': device.id, **device.to_dict()} for device in devices]
    return device_list


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
