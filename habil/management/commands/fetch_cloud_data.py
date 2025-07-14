from django.core.management.base import BaseCommand
from habil.models import Sensor, RawSensorData
from django.utils import timezone
from django.conf import settings
import requests

ARDUINO_THING_ID = "8c8865ae-413a-45e1-8368-11bd7fdfb165"
PROPERTY_IDS = {
    "temperature": "9cbddf7c-f451-46e6-952d-eb9823d66168",
    "humidity": "8fbf8a3b-7077-45c1-a82a-00dc108bf035",
    "pm2_5": "d2ed842d-3bc3-4832-800c-64f468da66f2",
    "pm10": "a633e558-e5da-4915-a0ab-9d22aa0ebe04",
    "nh3": "54c981c0-be42-4a8b-9bbe-93a30e260956",
    "ch4": "b403f4ee-f580-4ca6-9f99-124acb0f3e05",
    "co": "cd269ddf-b75f-4278-a247-94a2cff548d2",
    "no2": "afcedf1d-2e50-4d73-a01a-5a294a1ff74b",
    "battery_level": "b22e7dbb-1570-42fd-b4ce-5e1d2cc0b367",
    "signal_strength": "8dc076b2-7a45-4c55-bdd2-555adb7201c7",
}

def get_arduino_access_token():
    url = "https://api2.arduino.cc/iot/v1/clients/token"
    data = {
        "grant_type": "client_credentials",
        "client_id": settings.ARDUINO_CLIENT_ID,
        "client_secret": settings.ARDUINO_CLIENT_SECRET,
        "audience": "https://api2.arduino.cc/iot"
    }
    resp = requests.post(url, data=data)
    resp.raise_for_status()
    return resp.json()["access_token"]

def fetch_all_properties():
    token = get_arduino_access_token()
    headers = {"Authorization": f"Bearer {token}"}
    values = {}
    for key, prop_id in PROPERTY_IDS.items():
        url = f"https://api2.arduino.cc/iot/v2/things/{ARDUINO_THING_ID}/properties/{prop_id}"
        resp = requests.get(url, headers=headers)
        if resp.status_code == 200:
            values[key] = resp.json().get("last_value")
        else:
            values[key] = None
    return values

class Command(BaseCommand):
    help = "Fetch all Arduino Cloud properties and store in RawSensorData"

    def handle(self, *args, **kwargs):
        sensor = Sensor.objects.first()  # Assumes only one sensor
        if not sensor:
            self.stdout.write(self.style.ERROR("No sensor found in the database."))
            return

        values = fetch_all_properties()
        print("Fetched values:", values)
        obj = RawSensorData.objects.create(
            sensor=sensor,
            timestamp=timezone.now(),
            temperature=values.get("temperature"),
            humidity=values.get("humidity"),
            pm2_5=values.get("pm2_5"),
            pm10=values.get("pm10"),
            nh3=values.get("nh3"),
            ch4=values.get("ch4"),
            co=values.get("co"),
            no2=values.get("no2"),
            battery_level=values.get("battery_level"),
            signal_strength=values.get("signal_strength"),
        )
        print(f"Created RawSensorData: {obj}")
        self.stdout.write(self.style.SUCCESS("Fetched and stored latest data from Arduino Cloud."))