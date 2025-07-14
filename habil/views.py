from django.shortcuts import render, get_object_or_404, redirect
from .models import RawSensorData, Sensor, PredictedValues, AQIData, AQIResult
import json
from django.contrib.auth.decorators import login_required
from django.contrib.auth import views as auth_views
from django.urls import path
import os
import requests
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from django.conf import settings
from habil.models import AQIResult
from habil.aqi_engine import calculate_aqi
from django.db.models.functions import TruncHour, TruncDay, TruncWeek, TruncMonth, TruncQuarter, TruncYear
from django.db.models import Avg
from django.utils.dateparse import parse_date
from .ml_utility import get_lstm_model



# Home Page View
def home(request):
    return render(request, 'home.html') 

def aqi_data(request):
  
    sensors = AQIData.objects.values('sensor_id').distinct()  # Get unique sensors
    sensor_aqi_data = []

    for sensor in sensors:
        sensor_id = sensor['sensor_id']
        # Fetch the last 5 AQI readings for each sensor
        readings = AQIData.objects.filter(sensor_id=sensor_id).order_by('-timestamp')[:5]
        readings = readings[::-1]  # Reverse to show oldest first

        if readings:
            sensor_details = {
                'name': readings[0].sensor.name,
                'location': readings[0].sensor.location,
                'latitude': readings[0].sensor.latitude,
                'longitude': readings[0].sensor.longitude,
            }
            aqi_readings = {
                'timestamps': [reading.timestamp.strftime('%Y-%m-%d %H:%M') for reading in readings],
                'aqi_values': [reading.aqi_value for reading in readings],
            }
            sensor_aqi_data.append({'details': sensor_details, 'aqi_readings': aqi_readings})

    return render(request, 'aqi_data.html', {'sensor_aqi_data': sensor_aqi_data})

def predicted_values(request):
    return render(request, 'predicted_values.html')  #

def about(request):
    # Fetch all sensors and their latest data
    sensor_data = []
    sensors = Sensor.objects.prefetch_related('raw_data', 'predictions').all()

    for sensor in sensors:
        # Fetch the latest raw data for the sensor
        latest_raw_data = sensor.raw_data.order_by('-timestamp').first()

        # Fetch the latest predicted values for the sensor
        latest_predictions = sensor.predictions.order_by('-timestamp').first()

        # Append sensor details, latest raw data, and predictions
        sensor_data.append({
            'sensor': {
                'id': sensor.id,
                'name': sensor.name,
                'location': sensor.location,
                'latitude': sensor.latitude,
                'longitude': sensor.longitude,
                'installation_date': sensor.installation_date,
                'is_active': sensor.is_active,
                'description': sensor.description,
            },
            'latest_readings': {
                'temperature': latest_raw_data.temperature if latest_raw_data else None,
                'humidity': latest_raw_data.humidity if latest_raw_data else None,
                'pm2_5': latest_raw_data.pm2_5 if latest_raw_data else None,
                'pm10': latest_raw_data.pm10 if latest_raw_data else None,
                'nh3': latest_raw_data.nh3 if latest_raw_data else None,
                'ch4': latest_raw_data.ch4 if latest_raw_data else None,
                'co': latest_raw_data.co if latest_raw_data else None,
                'battery_level': latest_raw_data.battery_level if latest_raw_data else None,
                'signal_strength': latest_raw_data.signal_strength if latest_raw_data else None,
            },
            'predicted_values': {
                'temperature': latest_predictions.predicted_temperature if latest_predictions else None,
                'humidity': latest_predictions.predicted_humidity if latest_predictions else None,
                'pm2_5': latest_predictions.predicted_pm2_5 if latest_predictions else None,
                'pm10': latest_predictions.predicted_pm10 if latest_predictions else None,
                'nh3': latest_predictions.predicted_nh3 if latest_predictions else None,
                'ch4': latest_predictions.predicted_ch4 if latest_predictions else None,
                'co': latest_predictions.predicted_co if latest_predictions else None,
            }
        })

    context = {
        'sensor_data': sensor_data,
    }
    return render(request, 'about.html', context)

# Sensor Data Page View
def raw_sensor_data(request):
    # Fetch all sensors
    sensors = Sensor.objects.prefetch_related('raw_data').all()

    # Prepare data for each sensor
    sensor_data = []
    for sensor in sensors:
        readings = sensor.raw_data.order_by('-timestamp')[:50]  # Fetch latest 50 readings for each sensor
        sensor_data.append({
            'details': {
                'name': sensor.name,
                'location': sensor.location,
                'latitude': sensor.latitude,
                'longitude': sensor.longitude,
            },
            'readings': {
                'timestamps': [entry.timestamp.strftime('%Y-%m-%d %H:%M') for entry in readings],
                'temperature': [entry.temperature for entry in readings],
                'humidity': [entry.humidity for entry in readings],
                'pm2_5': [entry.pm2_5 for entry in readings],
                'pm10': [entry.pm10 for entry in readings],
                'nh3': [entry.nh3 for entry in readings],
                'ch4': [entry.ch4 for entry in readings],
                'co': [entry.co for entry in readings],
                'battery_level': [entry.battery_level for entry in readings],
                'signal_strength': [entry.signal_strength for entry in readings],
            }
        })

    context = {
        'sensor_data': sensor_data,  # Pass grouped sensor data to the template
    }
    return render(request, 'raw_sensor_data.html', context)

# Predicted Values Page View
import json
from .models import PredictedValues  # Ensure model name matches

def predicted_values(request):
    # Fetch all sensors
    sensors = Sensor.objects.prefetch_related('predictions').all()

    # Prepare data for each sensor
    sensor_predictions = []
    for sensor in sensors:
        predictions = sensor.predictions.order_by('-timestamp')[:50]  # Fetch latest 50 predictions for each sensor
        sensor_predictions.append({
            'details': {
                'name': sensor.name,
                'location': sensor.location,
                'latitude': sensor.latitude,
                'longitude': sensor.longitude,
            },
            'predictions': {
                'dates': [entry.timestamp.strftime('%Y-%m-%d') for entry in predictions],
                'temperature': [entry.predicted_temperature for entry in predictions],
                'humidity': [entry.predicted_humidity for entry in predictions],
                'pm2_5': [entry.predicted_pm2_5 for entry in predictions],
                'pm10': [entry.predicted_pm10 for entry in predictions],
                'nh3': [entry.predicted_nh3 for entry in predictions],
                'ch4': [entry.predicted_ch4 for entry in predictions],
                'co': [entry.predicted_co for entry in predictions],
            }
        })

    context = {
        'sensor_predictions': sensor_predictions,  # Pass grouped predictions to the template
    }
    return render(request, 'predicted_values.html', context)

def sensor_detail(request, sensor_id):
    # Fetch the sensor by ID
    sensor = get_object_or_404(Sensor, id=sensor_id)

    # Fetch related data (e.g., latest raw data and AQI data)
    latest_raw_data = sensor.raw_data.order_by('-timestamp').first()
    latest_aqi_data = sensor.aqi_data.order_by('-timestamp').first()

    context = {
        'sensor': sensor,
        'latest_raw_data': latest_raw_data,
        'latest_aqi_data': latest_aqi_data,
    }
    return render(request, 'sensor_detail.html', context)

@login_required
def dashboard(request):
    return render(request, 'dashboard.html')

@login_required
def sensor_data(request):
    return render(request, 'sensor_data.html')

@login_required
def predicted_data(request):
    return render(request, 'predicted_data.html')

def aqi_data(request):
    # Fetch AQI data for all sensors
    sensors = AQIData.objects.values('sensor_id').distinct()  # Get unique sensors
    sensor_aqi_data = []

    for sensor in sensors:
        sensor_id = sensor['sensor_id']
        # Fetch the last 5 AQI readings for each sensor
        readings = AQIData.objects.filter(sensor_id=sensor_id).order_by('-timestamp')[:5]
        readings = readings[::-1]  # Reverse to show oldest first

        if readings:
            sensor_details = {
                'name': readings[0].sensor.name,
                'location': readings[0].sensor.location,
                'latitude': readings[0].sensor.latitude,
                'longitude': readings[0].sensor.longitude,
            }
            aqi_readings = {
                'timestamps': [reading.timestamp.strftime('%Y-%m-%d %H:%M') for reading in readings],
                'aqi_values': [reading.aqi_value for reading in readings],
            }
            sensor_aqi_data.append({'details': sensor_details, 'aqi_readings': aqi_readings})

    return render(request, 'aqi_data.html', {'sensor_aqi_data': sensor_aqi_data})

@login_required
def reports(request):
    return render(request, 'reports.html')

@login_required
def sensor_manager(request):
    return render(request, 'sensor_manager.html')

@login_required
def analytics(request):
    return render(request, 'analytics.html')

from django.shortcuts import render, redirect
#from .forms import CustomUserCreationForm, ProfileForm
from django.contrib.auth import login

def signup(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Create a profile for the user
            Profile.objects.create(user=user)
            return redirect('habil:login')
    else:
        form = CustomUserCreationForm()
    return render(request, 'signup.html', {'form': form})

from django.contrib.auth import get_user_model
from django.utils.http import urlsafe_base64_decode
from django.contrib.auth.tokens import default_token_generator

def activate(request, uidb64, token):
    User = get_user_model()
    try:
        uid
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and default_token_generator.check_token(user, token):
        user.is_active = True
        user.save()
        return redirect('habil:login')
    else:
        return render(request, 'activation_invalid.html')

urlpatterns = [
    path('logout/', auth_views.LogoutView.as_view(next_page='/login/'), name='logout'),
]

ARDUINO_THING_ID = "8c8865ae-413a-45e1-8368-11bd7fdfb165"
PROPERTY_IDS = {
    "ch4": "b403f4ee-f580-4ca6-9f99-124acb0f3e05",
    "co": "cd269ddf-b75f-4278-a247-94a2cff548d2",
    "humidity": "8fbf8a3b-7077-45c1-a82a-00dc108bf035",
    "nh3": "54c981c0-be42-4a8b-9bbe-93a30e260956",
    "no2": "afcedf1d-2e50-4d73-a01a-5a294a1ff74b",
    "pm10": "a633e558-e5da-4915-a0ab-9d22aa0ebe04",
    "pm2_5": "d2ed842d-3bc3-4832-800c-64f468da66f2",
    "power_level": "b22e7dbb-1570-42fd-b4ce-5e1d2cc0b367",
    "signal_strength": "8dc076b2-7a45-4c55-bdd2-555adb7201c7",
    "temperature": "9cbddf7c-f451-46e6-952d-eb9823d66168",
}

def get_arduino_access_token():
    url = "https://api2.arduino.cc/iot/v1/clients/token"
    data = {
        "grant_type": "client_credentials",
        "client_id": settings.ARDUINO_CLIENT_ID,
        "client_secret": settings.ARDUINO_CLIENT_SECRET,
        "audience": "https://api2.arduino.cc/iot"
    }
    resp = requests.post(url, data=data)
    resp.raise_for_status()
    return resp.json()["access_token"]

def fetch_arduino_data():
    token = get_arduino_access_token()
    headers = {"Authorization": f"Bearer {token}"}
    values = {}
    for key, prop_id in PROPERTY_IDS.items():
        url = f"https://api2.arduino.cc/iot/v2/things/{ARDUINO_THING_ID}/properties/{prop_id}/lastValue"
        resp = requests.get(url, headers=headers)
        if resp.status_code == 200:
            values[key] = resp.json().get("value")
        else:
            values[key] = None
    return values

def store_sensor_data(sensor, values):
    RawSensorData.objects.create(
        sensor=sensor,
        timestamp=timezone.now(),
        temperature=values.get("temperature"),
        humidity=values.get("humidity"),
        pm2_5=values.get("pm2_5"),
        pm10=values.get("pm10"),
        nh3=values.get("nh3"),
        ch4=values.get("ch4"),
        co=values.get("co"),
        no2=values.get("no2"),
        battery_level=values.get("power_level"),
        signal_strength=values.get("signal_strength"),
    )

@require_GET
def fetch_and_store_sensor_data(request, sensor_id):
    # On marker click: fetch from Arduino, store, and return latest
    try:
        sensor = Sensor.objects.get(pk=sensor_id)
        values = fetch_arduino_data()
        store_sensor_data(sensor, values)
        latest = RawSensorData.objects.filter(sensor=sensor).order_by('-timestamp').first()
        data = {
            "temperature": latest.temperature,
            "humidity": latest.humidity,
            "pm2_5": latest.pm2_5,
            "pm10": latest.pm10,
            "nh3": latest.nh3,
            "ch4": latest.ch4,
            "co": latest.co,
            "no2": latest.no2,
            "battery_level": latest.battery_level,
            "signal_strength": latest.signal_strength,
            "timestamp": latest.timestamp,
        }
        return JsonResponse(data)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

def fetch_sensor_data(request, sensor_id):
    # ... your code ...
    latest = RawSensorData.objects.filter(sensor_id=sensor_id).order_by('-timestamp').first()
    if not latest:
        return JsonResponse({"error": "No data found."})
    return JsonResponse({
        "temperature": latest.temperature,
        "humidity": latest.humidity,
        "pm2_5": latest.pm2_5,
        "pm10": latest.pm10,
        "nh3": latest.nh3,
        "ch4": latest.ch4,
        "co": latest.co,
        "no2": latest.no2,
        "battery_level": latest.battery_level,
        "signal_strength": latest.signal_strength,
        "timestamp": latest.timestamp,
    })

def process_aqi_for_sensor_data(instance):
    for pollutant in ["pm2_5", "pm10", "co", "no2", "nh3", "ch4"]:
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

def aqi_data_view(request):
    results = AQIResult.objects.all().order_by('-timestamp')
    return render(request, "aqi_data.html", {"aqi_results": results})

from django.shortcuts import render
from .models import AQIResult

def aqi_results(request):
    results = AQIResult.objects.all().order_by('-timestamp')
    return render(request, 'aqi_results.html', {'aqi_results': results})

from django.http import JsonResponse
from .models import AQIResult, Sensor

def aqi_trend_data(request):
    sensor_id = request.GET.get('sensor_id')
    pollutants = request.GET.getlist('pollutants[]')
    start_datetime = request.GET.get('start_datetime')
    end_datetime = request.GET.get('end_datetime')
    sensor = Sensor.objects.get(id=sensor_id)
    data = {}

    # DateTime filtering
    qs_base = AQIResult.objects.filter(location=sensor.location)
    if start_datetime:
        qs_base = qs_base.filter(timestamp__gte=start_datetime)
    if end_datetime:
        qs_base = qs_base.filter(timestamp__lte=end_datetime)

    for pollutant in pollutants:
        qs = qs_base.filter(pollutant=pollutant).order_by('timestamp')
        timestamps = [r.timestamp.strftime("%Y-%m-%d %H:%M") for r in qs]
        concentrations = [r.concentration for r in qs]
        colors = [r.color_code for r in qs]  # Assuming AQIResult has color_code field
        data[pollutant] = {
            "timestamps": timestamps,
            "concentrations": concentrations,
            "colors": colors,  # Add this line
        }

    # Mean metrics from RawSensorData for the selected range
    raw_qs = RawSensorData.objects.filter(sensor=sensor)
    if start_datetime:
        raw_qs = raw_qs.filter(timestamp__gte=start_datetime)
    if end_datetime:
        raw_qs = raw_qs.filter(timestamp__lte=end_datetime)
    mean_metrics = raw_qs.aggregate(
        mean_temp=Avg('temperature'),
        mean_humidity=Avg('humidity'),
        mean_battery=Avg('battery_level'),
        mean_signal=Avg('signal_strength')
    )
    data["mean_metrics"] = {
        "temperature": round(mean_metrics["mean_temp"], 2) if mean_metrics["mean_temp"] is not None else None,
        "humidity": round(mean_metrics["mean_humidity"], 2) if mean_metrics["mean_humidity"] is not None else None,
        "battery_level": round(mean_metrics["mean_battery"], 2) if mean_metrics["mean_battery"] is not None else None,
        "signal_strength": round(mean_metrics["mean_signal"], 2) if mean_metrics["mean_signal"] is not None else None,
    }
    return JsonResponse(data)

from .models import Sensor

def aqi_trend(request):
    sensors = Sensor.objects.all()
    pollutants = ["pm2_5", "pm10", "co", "nh3"]
    return render(request, "aqi_trend.html", {"sensors": sensors, "pollutants": pollutants})

from django.views import View

class AnalyticsDashboardView(View):
    def get(self, request, *args, **kwargs):
        return render(request, 'analytics_dashboard.html')
