import csv
from django.core.management.base import BaseCommand
from habil.models import RawSensorData, Sensor
from django.utils.dateparse import parse_datetime

class Command(BaseCommand):
    help = "Import RawSensorData from a CSV file"

    def add_arguments(self, parser):
        parser.add_argument('csv_file', type=str, help='Path to the CSV file')

    def handle(self, *args, **kwargs):
        csv_file = kwargs['csv_file']
        with open(csv_file, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            count = 0
            for row in reader:
                sensor = Sensor.objects.get(id=row['sensor_id'])
                RawSensorData.objects.create(
                    sensor=sensor,
                    timestamp=parse_datetime(row['timestamp']),
                    temperature=row['temperature'],
                    humidity=row['humidity'],
                    pm2_5=row['pm2_5'],
                    pm10=row['pm10'],
                    nh3=row['nh3'],
                    ch4=row['ch4'],
                    co=row['co'],
                    no2=row['no2'],
                    battery_level=row['battery_level'],
                    signal_strength=row['signal_strength'],
                )
                count += 1
        self.stdout.write(self.style.SUCCESS(f"Imported {count} rows from {csv_file}"))