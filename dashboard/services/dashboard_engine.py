from habil.models import RawSensorData, AQIData
from django.utils import timezone

def get_latest_sensor_data(sensor=None):
    """
    Returns the latest data point for each sensor (or a specific sensor if one is provided).
    """
    queryset = RawSensorData.objects.all()
    if sensor:
        queryset = queryset.filter(sensor=sensor)
    return queryset.order_by('-timestamp').first()

def get_latest_aqi(sensor=None):
    """
    Returns the latest AQIData instance (optionally for a specific sensor).
    """
    queryset = AQIData.objects.all()
    if sensor:
        queryset = queryset.filter(sensor=sensor)
    latest_aqi = queryset.order_by('-timestamp').first()
    return latest_aqi