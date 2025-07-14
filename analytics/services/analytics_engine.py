# analytics/services/analytics_engine.py
import pandas as pd
from habil.models import RawSensorData, AQIResult, Sensor, PredictedValues
from django.core.cache import cache
from django.db.models import Avg
from datetime import timedelta

def compute_exposure_index(sensor_id):
    data = RawSensorData.objects.filter(sensor_id=sensor_id).order_by('-timestamp')[:168]  # last 7 days hourly
    df = pd.DataFrame(list(data.values('timestamp', 'pm2_5', 'co', 'no2')))
    if df.empty:
        return 0
    df['exposure_index'] = df['pm2_5'] * 1 + df['co'] * 0.8 + df['no2'] * 1.2  # Weightings 
    df['date'] = pd.to_datetime(df['timestamp']).dt.date
    return df.groupby('date')['exposure_index'].sum().to_dict()

def get_trends(sensor_id, pollutant, period='daily'):
    cache_key = f"trend_{sensor_id}_{pollutant}_{period}"
    result = cache.get(cache_key)
    if result is not None:
        return result
    qs = RawSensorData.objects.filter(sensor_id=sensor_id).order_by('timestamp')
    df = pd.DataFrame(list(qs.values('timestamp', pollutant)))
    if df.empty:
        return []
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    if period == 'daily':
        grouped = df.resample('D', on='timestamp').mean()
    elif period == 'weekly':
        grouped = df.resample('W', on='timestamp').mean()
    elif period == 'monthly':
        grouped = df.resample('M', on='timestamp').mean()
    else:
        grouped = df
    result = grouped.reset_index().to_dict(orient='records')
    cache.set(cache_key, result, 60*60)  # cache for 1 hour
    return result

def generate_heatmap_data():
    qs = AQIResult.objects.all()
    df = pd.DataFrame(list(qs.values('location', 'timestamp', 'aqi_value')))
    if df.empty:
        return []
    # Split location and filter for exactly two parts
    split_locs = df['location'].str.split(',', expand=True)
    mask = (split_locs.shape[1] == 2)
    if not mask:
        # Remove rows where split does not yield two columns
        return []
    split_locs.columns = ['lat', 'lon']
    df = df.reset_index(drop=True)
    split_locs = split_locs.reset_index(drop=True)
    df = pd.concat([df, split_locs], axis=1)
    # Remove rows where lat/lon cannot be converted to float
    df = df[pd.to_numeric(df['lat'], errors='coerce').notnull() & pd.to_numeric(df['lon'], errors='coerce').notnull()]
    df['lat'] = df['lat'].astype(float)
    df['lon'] = df['lon'].astype(float)
    return df[['lat', 'lon', 'aqi_value']].to_dict(orient='records')

def get_sensor_health(sensor_id):
    sensor = Sensor.objects.get(id=sensor_id)
    last_data = sensor.raw_data.order_by('-timestamp').first()
    uptime = sensor.raw_data.count()
    battery = getattr(last_data, 'battery_level', None) if last_data else None
    signal = getattr(last_data, 'signal_strength', None) if last_data else None
    return {
        'uptime': uptime,
        'last_active': last_data.timestamp if last_data else None,
        'battery': battery,
        'signal': signal,
    }

def generate_leaderboard(metric='aqi', top_n=5, reverse=False):
    if metric == 'aqi':
        qs = AQIResult.objects.values('sensor').annotate(avg_aqi=Avg('aqi_value'))
        sorted_qs = sorted(qs, key=lambda x: x['avg_aqi'], reverse=reverse)
    else:
        sorted_qs = []
    return sorted_qs[:top_n]

def summarize_exposure(sensor_id=None, location=None):
    qs = RawSensorData.objects.all()
    if sensor_id:
        qs = qs.filter(sensor_id=sensor_id)
    if location:
        qs = qs.filter(sensor__location=location)
    df = pd.DataFrame(list(qs.values('timestamp', 'ch4', 'co', 'nh3', 'no2', 'humidity', 'temperature', 'pm2_5', 'pm10')))
    if df.empty:
        return {}
    exposure = {}
    for col in ['ch4', 'co', 'nh3', 'no2', 'humidity', 'temperature', 'pm2_5', 'pm10']:
        df['hour'] = df['timestamp'].diff().dt.total_seconds().div(3600).fillna(1)
        df['exposure'] = df[col] * df['hour']
        exposure[col] = df['exposure'].sum()
    return exposure

def generate_report(filters, page=1, page_size=100):
    qs = RawSensorData.objects.all()
    # Apply filters (date, sensor, pollutant, etc.)
    if 'sensor_id' in filters:
        qs = qs.filter(sensor_id=filters['sensor_id'])
    if 'start' in filters:
        qs = qs.filter(timestamp__gte=filters['start'])
    if 'end' in filters:
        qs = qs.filter(timestamp__lte=filters['end'])
    df = pd.DataFrame(list(qs.values()))
    # Pagination
    start = (page - 1) * page_size
    end = start + page_size
    return df.iloc[start:end]

def export_report_csv(df):
    import io
    csv_buffer = io.StringIO()
    df.to_csv(csv_buffer, index=False)
    return csv_buffer.getvalue()
