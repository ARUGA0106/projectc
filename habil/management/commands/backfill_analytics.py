from django.core.management.base import BaseCommand
from habil.models import Sensor, RawSensorData
from habil.analytics_engine import calculate_analytics_on_new_data

class Command(BaseCommand):
    help = "Backfill analytics tables from existing RawSensorData"

    def handle(self, *args, **options):
        sensors = Sensor.objects.all()
        total = RawSensorData.objects.count()
        processed = 0

        for sensor in sensors:
            print(f"Processing sensor: {sensor.name}")
            raw_data = RawSensorData.objects.filter(sensor=sensor).order_by('timestamp')
            for instance in raw_data:
                # Call the analytics engine as if this data was just created
                calculate_analytics_on_new_data(RawSensorData, instance, created=True)
                processed += 1
                if processed % 100 == 0:
                    print(f"Processed {processed}/{total} records...")

        print(f"Backfill complete. {processed} records processed.")