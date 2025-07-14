from django.shortcuts import render
from habil.models import Sensor, AQIAnalytics, PollutionTrend, SensorHealth, PollutionForecast, RawSensorData, AQIData
from django.db.models import Avg
from django.utils import timezone

def get_sensor_health(sensor_id):
    sensor = Sensor.objects.get(id=sensor_id)
    last_data = RawSensorData.objects.filter(sensor=sensor).order_by('-timestamp').first()
    uptime = SensorHealth.objects.filter(sensor=sensor).order_by('-timestamp').first()
    return {
        'uptime': f"{round(uptime.uptime_percent, 1)}%" if uptime else "N/A",
        'last_active': last_data.timestamp if last_data else None,
        'battery': last_data.battery_level if last_data else None,
        'signal': last_data.signal_strength if last_data else None,
    }

def analytics_dashboard(request):
    sensors = Sensor.objects.all()
    selected_sensor = sensors.first()
    pollutant_list = ['pm2_5', 'pm10', 'co', 'no2', 'nh3', 'ch4']

    # Real-time AQI
    latest_analytics = AQIAnalytics.objects.filter(sensor=selected_sensor).order_by('-timestamp').first()

    # Trends
    trends = PollutionTrend.objects.filter(sensor=selected_sensor, period='daily').order_by('-start_date')[:7]
    trends_data = [
        {'date': t.start_date.strftime('%Y-%m-%d'), 'avg': t.avg_value, 'max': t.max_value, 'std': t.std_dev}
        for t in trends
    ][::-1]

    # Exposure Index
    exposure_index = latest_analytics.exposure_index if latest_analytics else None

    # Sensor Health
    health = SensorHealth.objects.filter(sensor=selected_sensor).order_by('-timestamp').first()

    # Forecast
    forecast = PollutionForecast.objects.filter(sensor=selected_sensor).order_by('timestamp')[:3]

    # Hotspots (last 7 days)
    hotspots = AQIAnalytics.objects.filter(sensor=selected_sensor, pollution_hotspot=True).order_by('-timestamp')[:7]

    context = {
        "sensors": sensors,
        "selected_sensor": selected_sensor,
        "pollutant_list": pollutant_list,
        "latest_analytics": latest_analytics,
        "trends": trends_data,
        "exposure_index": exposure_index,
        "health": health,
        "forecast": forecast,
        "hotspots": hotspots,
    }
    return render(request, "analytics.html", context)

def generate_leaderboard(metric='aqi', top_n=5, reverse=False):
    if metric == 'aqi':
        qs = AQIData.objects.values('sensor').annotate(avg_aqi=Avg('aqi_value'))
        sorted_qs = sorted(qs, key=lambda x: x['avg_aqi'], reverse=not reverse)
    else:
        sorted_qs = []
    return sorted_qs[:top_n]

def sensor_dashboard(request):
    sensors = Sensor.objects.all()
    health = [get_sensor_health(sensor.id) for sensor in sensors]
    colors = ["bg-primary", "bg-success", "bg-warning", "bg-info", "bg-danger", "bg-secondary"]
    sensor_health = zip(sensors, health, colors * ((len(sensors) // len(colors)) + 1))
    leaderboard = generate_leaderboard()
    context = {
        'sensor_health': sensor_health,
        'leaderboard': leaderboard,
    }
    return render(request, 'sensors.html', context)