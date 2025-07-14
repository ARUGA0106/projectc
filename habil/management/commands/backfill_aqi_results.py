from django.core.management.base import BaseCommand
from habil.models import RawSensorData, AQIResult
from habil.aqi_engine import calculate_aqi

class Command(BaseCommand):
    help = "Calculate and store AQI results for all RawSensorData in the database."

    def handle(self, *args, **kwargs):
        count = 0
        pollutants = ["pm2_5", "pm10", "co", "no2", "nh3", "ch4"]
        for data in RawSensorData.objects.all():
            for pollutant in pollutants:
                value = getattr(data, pollutant, None)
                if value is not None:
                    result = calculate_aqi(pollutant, value)
                    if result and result["aqi"] is not None:
                        AQIResult.objects.update_or_create(
                            timestamp=data.timestamp,
                            location=data.sensor.location,
                            pollutant=pollutant,
                            defaults={
                                "concentration": value,
                                "aqi_value": result["aqi"],
                                "category": result["category"],
                                "color_code": result["color"],
                            }
                        )
                        count += 1
        self.stdout.write(self.style.SUCCESS(f"Backfilled AQI results for {count} pollutant readings."))