import logging
from flask import Flask, render_template
from tuya_connector import TuyaOpenAPI, TUYA_LOGGER

import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore

# Fetch the service account key JSON file contents
cred = credentials.Certificate('firebase/iot-dashboard-firebase.json')

# Initialize the app with a service account, granting admin privileges
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://console.firebase.google.com/project/iot-dashboard-737c8/firestore'
})

app = Flask(__name__)

ACCESS_ID = "3ujca7y7apppqpcjjmdt"
ACCESS_KEY = "e719ad0396c74b64bad8510c8baa491c"
API_ENDPOINT = "https://openapi.tuyaus.com"
DEVICE_ID = "vdevo170000581142241"


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
    db = firestore.client()

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


@app.route('/')
def index():
    devices_tuya = get_tuya_devices()
    devices_db = get_firestore_devices()
    # logging.info("Response: %s", devices_tuya)
    return render_template('index.html', devices_tuya=devices_tuya, devices_db=devices_db)


if __name__ == '__main__':
    app.run(debug=True)
