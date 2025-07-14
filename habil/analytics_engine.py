from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import RawSensorData, AQIAnalytics, PollutionTrend, SensorHealth, PollutionForecast, Sensor
from django.utils import timezone
from datetime import timedelta
import numpy as np
from habil.aqi_engine import calculate_aqi

@receiver(post_save, sender=RawSensorData)
def calculate_analytics_on_new_data(sender, instance, created, **kwargs):
    if not created:
        return

    sensor = instance.sensor
    now = timezone.now()

    # --- 1. Real-time AQI Levels ---
    # Assume you have a function calculate_aqi(pollutant, value) returning (aqi, category)
    pollutants = ['pm2_5', 'pm10', 'co', 'no2', 'nh3', 'ch4']
    latest_values = {p: getattr(instance, p, None) for p in pollutants}
    aqi_results = [calculate_aqi(p, v) for p, v in latest_values.items() if v is not None]
    overall_aqi = max([r["aqi"] for r in aqi_results if r and r["aqi"] is not None], default=0)
    aqi_category = next((r["category"] for r in aqi_results if r and r["aqi"] == overall_aqi), "Unknown")

    # --- 2. Exposure Index (last 24h) ---
    last_24h = RawSensorData.objects.filter(sensor=sensor, timestamp__gte=now - timedelta(hours=24))
    exposure_index = np.mean([getattr(r, 'pm2_5', 0) for r in last_24h]) if last_24h else 0

    # --- 3. Sensor Health Score ---
    expected = 24
    actual = last_24h.count()
    uptime = (actual / expected) * 100 if expected else 0
    completeness = uptime
    last_record = RawSensorData.objects.filter(sensor=sensor).order_by('-timestamp').first()
    latency = (now - last_record.timestamp).total_seconds() if last_record else 0
    erratic = np.std([getattr(r, 'pm2_5', 0) for r in last_24h]) < 1 if actual > 1 else False
    health_score = (uptime + completeness) / 2 - (latency / 3600)  # Example formula

    # --- 4. Pollution Forecast (dummy, replace with real AI) ---
    forecast = {}
    for h in range(1, 4):
        forecast[h] = {p: (getattr(instance, p, 0) + np.random.normal(0, 1)) for p in pollutants}

    # --- 5. Pollution Hotspot ---
    pollution_hotspot = overall_aqi > 150

    # --- 6. Health Risk Alerts ---
    health_risk_alert = ""
    if overall_aqi > 100:
        health_risk_alert = "Sensitive groups at risk"
    if overall_aqi > 150:
        health_risk_alert = "Unhealthy for all"

    # --- 7. Source Attribution (dummy logic) ---
    source_attribution = "Traffic" if overall_aqi > 120 else "Background"

    # Save analytics
    AQIAnalytics.objects.create(
        sensor=sensor,
        overall_aqi=overall_aqi,
        aqi_category=aqi_category,
        exposure_index=exposure_index,
        sensor_health_score=health_score,
        forecast_json=forecast,
        pollution_hotspot=pollution_hotspot,
        health_risk_alert=health_risk_alert,
        source_attribution=source_attribution,
    )

    # Save sensor health
    SensorHealth.objects.create(
        sensor=sensor,
        uptime_percent=uptime,
        data_completeness=completeness,
        latency_seconds=latency,
        erratic_flag=erratic,
    )

    # Save pollution trends (daily, weekly, monthly)
    for period, delta in [('daily', 1), ('weekly', 7), ('monthly', 30)]:
        start = now - timedelta(days=delta)
        for p in pollutants:
            qs = RawSensorData.objects.filter(sensor=sensor, timestamp__gte=start)
            values = [getattr(r, p, 0) for r in qs]
            if values:
                PollutionTrend.objects.create(
                    sensor=sensor,
                    period=period,
                    pollutant=p,
                    avg_value=np.mean(values),
                    max_value=np.max(values),
                    min_value=np.min(values),
                    std_dev=np.std(values),
                    start_date=start.date(),
                    end_date=now.date(),
                )

    # Save pollution forecast (dummy)
    for h in range(1, 4):
        for p in pollutants:
            PollutionForecast.objects.create(
                sensor=sensor,
                timestamp=now + timedelta(hours=h),
                pollutant=p,
                predicted_value=forecast[h][p],
                horizon_hours=h,
            )