from django.core.management.base import BaseCommand
from habil.models import RawSensorData, PredictedValues, Sensor
from habil.ml_utility import get_lstm_model, get_scaler, predict_next_steps
import numpy as np
from datetime import timedelta

class Command(BaseCommand):
    help = "Backfill predictions for all existing RawSensorData"

    def handle(self, *args, **options):
        model = get_lstm_model()
        scaler = get_scaler()
        pollutant_fields = ['ch4', 'co', 'nh3', 'no2', 'humidity', 'temperature', 'pm2_5', 'pm10']  # adjust if needed

        for sensor in Sensor.objects.all():
            raw_qs = RawSensorData.objects.filter(sensor=sensor).order_by('timestamp')
            if raw_qs.count() < 10:
                self.stdout.write(self.style.WARNING(f"Sensor {sensor} has less than 10 records, skipping."))
                continue

            raw_list = list(raw_qs)
            for idx in range(len(raw_list) - 9):
                last_10 = raw_list[idx:idx+10]
                input_seq = np.array([[getattr(r, f) for f in pollutant_fields] for r in last_10])
                input_seq = input_seq.reshape(1, 10, len(pollutant_fields))

                preds = predict_next_steps(input_seq, model=model, scaler=scaler)  # shape (3, num_features)
                base_time = last_10[-1].timestamp

                for i in range(3):
                    pred_time = base_time + timedelta(hours=i+1)
                    pred_kwargs = {
                        'sensor': sensor,
                        'timestamp': pred_time,
                        'predicted_temperature': preds[i][pollutant_fields.index('temperature')],
                        'predicted_humidity': preds[i][pollutant_fields.index('humidity')],
                        'predicted_pm2_5': preds[i][pollutant_fields.index('pm2_5')],
                        'predicted_pm10': preds[i][pollutant_fields.index('pm10')],
                        'predicted_nh3': preds[i][pollutant_fields.index('nh3')],
                        'predicted_ch4': preds[i][pollutant_fields.index('ch4')],
                        'predicted_co': preds[i][pollutant_fields.index('co')],
                        'predicted_no2': preds[i][pollutant_fields.index('no2')],
                    }
                    PredictedValues.objects.update_or_create(
                        sensor=sensor,
                        timestamp=pred_time,
                        defaults=pred_kwargs
                    )
            self.stdout.write(self.style.SUCCESS(f"Predictions backfilled for sensor {sensor}."))

        self.stdout.write(self.style.SUCCESS("Backfilling complete."))