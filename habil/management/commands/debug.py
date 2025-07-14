import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'projectc.settings')
django.setup()
from django.core.management.base import BaseCommand
from habil.models import RawSensorData, Sensor
from django.utils.dateparse import parse_datetime
import requests
from django.conf import settings

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

class Command(BaseCommand):
    help = "Fetch last 90 values for all properties and store in RawSensorData"

    def handle(self, *args, **kwargs):
        # Get access token
        url = "https://api2.arduino.cc/iot/v1/clients/token"
        data = {
            "grant_type": "client_credentials",
            "client_id": settings.ARDUINO_CLIENT_ID,
            "client_secret": settings.ARDUINO_CLIENT_SECRET,
            "audience": "https://api2.arduino.cc/iot"
        }
        resp = requests.post(url, data=data)
        resp.raise_for_status()
        token = resp.json()["access_token"]

        headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}

        # Fetch timeseries for each property
        all_data = {}
        for key, prop_id in PROPERTY_IDS.items():
            prop_url = f"https://api2.arduino.cc/iot/v2/things/{ARDUINO_THING_ID}/properties/{prop_id}/timeseries?limit=90"
            prop_resp = requests.get(prop_url, headers=headers)
            if prop_resp.status_code == 200:
                data = prop_resp.json()
                print(f"{key} timeseries sample:", str(data)[:300])
                # Use the correct key for the list of values
                if isinstance(data, dict) and "data" in data:
                    data = data["data"]
                for entry in data:
                    if not isinstance(entry, dict):
                        continue
                    ts = parse_datetime(entry.get('time'))
                    if ts not in all_data:
                        all_data[ts] = {}
                    all_data[ts][key] = entry.get('value')
            else:
                print(f"Failed to fetch {key}: {prop_resp.status_code}")

        sensor = Sensor.objects.first()
        if not sensor:
            print("No sensor found in the database.")
            return

        count = 0
        for ts, values in all_data.items():
            RawSensorData.objects.update_or_create(
                sensor=sensor,
                timestamp=ts,
                defaults=values
            )
            count += 1
        print(f"Imported {count} records from Arduino Cloud (last 90 values per property).")
