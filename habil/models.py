# -*- coding: utf-8 -*-
# habil/models.py
from django.db import models
from django.contrib.auth.models import AbstractUser, User
from django.db.models.signals import post_save
from django.dispatch import receiver

from django.conf import settings
BASE_DIR = settings.BASE_DIR

from .ml_utility import get_lstm_model, get_scaler, predict_next_steps
from habil.aqi_engine import calculate_aqi
import os
import numpy as np
import joblib
from tensorflow.keras.models import load_model


MODEL_PATH = os.path.join(BASE_DIR, 'model', 'lstm_multi_forecast.keras')
SCALER_PATH = os.path.join(BASE_DIR, 'model', 'pollutant_scaler.pkl')
POLLUTANTS = ['ch4', 'co', 'nh3', 'no2', 'humidity', 'temperature', 'pm2_5', 'pm10']

lstm_model = load_model(MODEL_PATH)

class Sensor(models.Model):
    name = models.CharField(max_length=100, unique=True)
    location = models.CharField(max_length=200)
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    installation_date = models.DateField()
    is_active = models.BooleanField(default=True)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.name} ({self.location})"
    # This model represents a sensor with its attributes like name, location, coordinates, installation date, and status.
    # The __str__ method provides a readable string representation of the sensor instance.
class RawSensorData(models.Model):
    sensor = models.ForeignKey(Sensor, on_delete=models.CASCADE, related_name='raw_data')
    timestamp = models.DateTimeField(auto_now_add=True)
    temperature = models.FloatField()
    humidity = models.FloatField()
    pm2_5 = models.FloatField()
    pm10 = models.FloatField()
    nh3 = models.FloatField()
    ch4 = models.FloatField()
    co = models.FloatField()
    no2 = models.FloatField()  # <-- Add this line
    battery_level = models.FloatField()
    signal_strength = models.FloatField()  # <-- Change to FloatField for safety

    class Meta:
        ordering = ['-timestamp']
        verbose_name_plural = 'Raw Sensor Data'

    def __str__(self):
        return f"{self.sensor.name} - {self.timestamp}"

class AQIData(models.Model):
    sensor = models.ForeignKey(Sensor, on_delete=models.CASCADE, related_name='aqi_data')
    timestamp = models.DateTimeField(auto_now_add=True)
    aqi_value = models.IntegerField(null=True, blank=True)
    aqi_category = models.CharField(max_length=50)

    class Meta:
        ordering = ['-timestamp']
        verbose_name_plural = 'AQI Data'

    def __str__(self):
        return f"{self.sensor.name} - AQI: {self.aqi_value} ({self.aqi_category})"

class PredictedValues(models.Model):
    sensor = models.ForeignKey(Sensor, on_delete=models.CASCADE, related_name='predictions')
    timestamp = models.DateTimeField()
    predicted_temperature = models.FloatField()
    predicted_humidity = models.FloatField()
    predicted_pm2_5 = models.FloatField()
    predicted_pm10 = models.FloatField()
    predicted_nh3 = models.FloatField()
    predicted_ch4 = models.FloatField()
    predicted_co = models.FloatField()
    predicted_no2 = models.FloatField()

    class Meta:
        ordering = ['-timestamp']
        verbose_name_plural = 'Predicted Values'

    def __str__(self):
        return f"{self.sensor.name} - Prediction: {self.timestamp}"

class AQIResult(models.Model):
    timestamp = models.DateTimeField()
    location = models.CharField(max_length=100)
    pollutant = models.CharField(max_length=10)
    concentration = models.FloatField()
    aqi_value = models.IntegerField(null=True, blank=True)  # <-- allow nulls
    category = models.CharField(max_length=20)
    color_code = models.CharField(max_length=10)

    def __str__(self):
        return f"{self.timestamp} {self.location} {self.pollutant} AQI: {self.aqi_value}"


MODEL_PATH = os.path.join(BASE_DIR, 'model', 'lstm_multi_forecast.keras')
SCALER_PATH = os.path.join(BASE_DIR, 'model', 'pollutant_scaler.pkl')
POLLUTANTS = ['ch4', 'co', 'nh3', 'no2', 'humidity', 'temperature', 'pm2_5', 'pm10']

@receiver(post_save, sender=RawSensorData)
def create_aqi_and_prediction(sender, instance, created, **kwargs):
    if not created:
        return

    # --- AQIResult logic (as you already have) ---
    for pollutant in ["pm2_5", "pm10", "co", "no2", "so2", "o3", "nh3", "ch4"]:
        value = getattr(instance, pollutant, None)
        if value is not None:
            result = calculate_aqi(pollutant, value)
            if result:
                AQIResult.objects.update_or_create(
                    timestamp=instance.timestamp,
                    location=instance.sensor.location,
                    pollutant=pollutant,
                    defaults={
                        "concentration": value,
                        "aqi_value": result["aqi"],
                        "category": result["category"],
                        "color_code": result["color"],
                    }
                )

    # --- LSTM Prediction logic ---
    # Get last 10 readings for this sensor, ordered oldest to newest
    last_10 = RawSensorData.objects.filter(sensor=instance.sensor).order_by('-timestamp')[:10]
    if last_10.count() < 10:
        return  # Not enough data yet

    # Reverse to chronological order
    last_10 = list(last_10)[::-1]

    # Prepare input for model: shape (1, 10, num_features)
    X = np.array([[getattr(r, p) for p in POLLUTANTS] for r in last_10])
    scaler = joblib.load(SCALER_PATH)
    X_scaled = scaler.transform(X)
    X_scaled = np.expand_dims(X_scaled, axis=0)  # shape (1, 10, num_features)

    # Load the model before prediction
    lstm_model = load_model(MODEL_PATH)
    preds_scaled = lstm_model.predict(X_scaled)
    preds_scaled = preds_scaled.reshape(3, len(POLLUTANTS))
    preds = scaler.inverse_transform(preds_scaled)

    # Store predictions in PredictedValues
    from datetime import timedelta

    base_time = instance.timestamp
    pollutant_fields = ['ch4', 'co', 'nh3', 'no2', 'humidity', 'temperature', 'pm2_5', 'pm10']
    for i in range(3):
        pred_time = base_time + timedelta(hours=i+1)
        pred_kwargs = {
            'sensor': instance.sensor,
            'timestamp': pred_time,
            'predicted_ch4': preds[i][pollutant_fields.index('ch4')],
            'predicted_co': preds[i][pollutant_fields.index('co')],
            'predicted_nh3': preds[i][pollutant_fields.index('nh3')],
            'predicted_no2': preds[i][pollutant_fields.index('no2')],
            'predicted_humidity': preds[i][pollutant_fields.index('humidity')],
            'predicted_temperature': preds[i][pollutant_fields.index('temperature')],
            'predicted_pm2_5': preds[i][pollutant_fields.index('pm2_5')],
            'predicted_pm10': preds[i][pollutant_fields.index('pm10')],
        }
        PredictedValues.objects.update_or_create(
            sensor=instance.sensor,
            timestamp=pred_time,
            defaults=pred_kwargs
        )

@receiver(post_save, sender=RawSensorData)
def run_lstm_prediction(sender, instance, created, **kwargs):
    if not created:
        return

    # Fetch last 10 readings for this sensor
    last_10 = RawSensorData.objects.filter(sensor=instance.sensor).order_by('-timestamp')[:10]
    if last_10.count() < 10:
        return  # Not enough data

    # Prepare input: shape (1, 10, num_features)
    pollutant_fields = ['ch4', 'co', 'nh3', 'no2', 'humidity', 'temperature', 'pm2_5', 'pm10']
    last_10 = list(last_10)[::-1]  # oldest first
    input_seq = np.array([[getattr(r, f) for f in pollutant_fields] for r in last_10])
    input_seq = input_seq.reshape(1, 10, len(pollutant_fields))

    # Predict next 3 steps
    model = get_lstm_model()
    scaler = get_scaler()
    preds = predict_next_steps(input_seq, model=model, scaler=scaler)  # shape (3, num_features)

    # Save predictions
    from datetime import timedelta
    for i in range(3):
        pred_time = instance.timestamp + timedelta(hours=i+1)
        pred_vals = dict(zip(pollutant_fields, preds[i]))
        PredictedValues.objects.create(
            sensor=instance.sensor,
            timestamp=pred_time,
            predicted_ch4=preds[i][pollutant_fields.index('ch4')],
            predicted_co=preds[i][pollutant_fields.index('co')],
            predicted_nh3=preds[i][pollutant_fields.index('nh3')],
            predicted_no2=preds[i][pollutant_fields.index('no2')],
            predicted_humidity=preds[i][pollutant_fields.index('humidity')],
            predicted_temperature=preds[i][pollutant_fields.index('temperature')],
            predicted_pm2_5=preds[i][pollutant_fields.index('pm2_5')],
            predicted_pm10=preds[i][pollutant_fields.index('pm10')],
        )

class Profile(models.Model):
    USER_ROLES = (
        ('admin', 'Admin'),
        ('user', 'Registered User'),
    )
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=10, choices=USER_ROLES, default='user')
    # ...other fields...

from django.db import models
from habil.models import Sensor
#from habil.models import Alert  # Import Alert model

class Alert(models.Model):
    ALERT_TYPES = (
        ('sensor_health', 'Sensor Health'),
        ('pollution', 'Pollution'),
    )
    sensor = models.ForeignKey(Sensor, on_delete=models.CASCADE)
    type = models.CharField(max_length=20, choices=ALERT_TYPES)
    message = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ['-timestamp']

@receiver(post_save, sender=RawSensorData)
def create_alerts_on_data_save(sender, instance, created, **kwargs):
    if not created:
        return

    # --- Sensor Health Alerts ---
    # Signal strength low
    if instance.signal_strength < 20:
        Alert.objects.create(
            sensor=instance.sensor,
            type='sensor_health',
            message=f"Signal strength low: {instance.signal_strength}",
            is_read=False,
        )
    # Last seen > 2 hours (check previous record)
    from django.utils import timezone
    from datetime import timedelta
    last = RawSensorData.objects.filter(sensor=instance.sensor).order_by('-timestamp')[1:2].first()
    if last and (instance.timestamp - last.timestamp) > timedelta(hours=2):
        Alert.objects.create(
            sensor=instance.sensor,
            type='sensor_health',
            message="Sensor not seen for over 2 hours.",
            is_read=False,
        )

    # --- Pollution Alerts ---
    # Example: PM2.5 high
    if instance.pm2_5 > 150:
        Alert.objects.create(
            sensor=instance.sensor,
            type='pollution',
            message=f"PM2.5 high: {instance.pm2_5}",
            is_read=False,
        )
    # Add similar checks for other pollutants as needed

from django.db import models
from django.utils import timezone

class AQIAnalytics(models.Model):
    sensor = models.ForeignKey('Sensor', on_delete=models.CASCADE, related_name='aqi_analytics')
    timestamp = models.DateTimeField(default=timezone.now)
    overall_aqi = models.IntegerField()
    aqi_category = models.CharField(max_length=20)
    exposure_index = models.FloatField()
    sensor_health_score = models.FloatField()
    forecast_json = models.JSONField(default=dict)  # {hour: {pollutant: value}}
    pollution_hotspot = models.BooleanField(default=False)
    health_risk_alert = models.CharField(max_length=100, blank=True, null=True)
    source_attribution = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.sensor.name} - AQI: {self.overall_aqi} ({self.aqi_category}) @ {self.timestamp}"

class PollutionTrend(models.Model):
    sensor = models.ForeignKey('Sensor', on_delete=models.CASCADE, related_name='pollution_trends')
    period = models.CharField(max_length=10)  # 'daily', 'weekly', 'monthly'
    pollutant = models.CharField(max_length=10)
    avg_value = models.FloatField()
    max_value = models.FloatField()
    min_value = models.FloatField()
    std_dev = models.FloatField()
    start_date = models.DateField()
    end_date = models.DateField()

    class Meta:
        ordering = ['-start_date']

class SensorHealth(models.Model):
    sensor = models.ForeignKey('Sensor', on_delete=models.CASCADE, related_name='health')
    timestamp = models.DateTimeField(default=timezone.now)
    uptime_percent = models.FloatField()
    data_completeness = models.FloatField()
    latency_seconds = models.FloatField()
    erratic_flag = models.BooleanField(default=False)

    class Meta:
        ordering = ['-timestamp']

class PollutionForecast(models.Model):
    sensor = models.ForeignKey('Sensor', on_delete=models.CASCADE, related_name='forecasts')
    timestamp = models.DateTimeField()
    pollutant = models.CharField(max_length=10)
    predicted_value = models.FloatField()
    horizon_hours = models.IntegerField()  # e.g., 1, 2, 3 hours ahead

    class Meta:
        ordering = ['-timestamp']