from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse
from dashboard.services.dashboard_engine import get_latest_sensor_data, get_latest_aqi
from habil.models import Sensor, RawSensorData, Alert, PredictedValues
from django.db.models import Q, Min, Max, Avg
import csv
import json 
import pandas as pd
from django.views.decorators.csrf import csrf_exempt
from .form import UserCreateForm, SensorCreateForm
from django.contrib.auth.models import User
from django.template.loader import render_to_string
import datetime
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.platypus import Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from django.utils import timezone


@login_required
def dashboard_home(request):
    sensors = Sensor.objects.all()
    sensor_data = []
    for sensor in sensors:
        latest = sensor.raw_data.order_by('-timestamp').first()
        predicted = sensor.predictions.order_by('-timestamp').first()
        sensor_data.append({
            'sensor': sensor,
            'latest_readings': latest,
            'predicted_values': predicted,
        })
    context = {
        'sensor_data': sensor_data,
        'sensors': sensors,  # for cards if you still want them
    }
    return render(request, "dashboard/dashboard.html", context)

def get_item(obj, key):
    # Handles both model attributes and dict keys
    return getattr(obj, key, '')

def data_management(request):
    sensors = Sensor.objects.all()
    # Use model field names for pollutants
    pollutants = [
        'pm2_5', 'pm10', 'co', 'no2', 'nh3', 'ch4', 'humidity', 'temperature'
    ]
    pollutant_labels = {
        'pm2_5': 'PM2.5',
        'pm10': 'PM10',
        'co': 'CO',
        'no2': 'NO2',
        'nh3': 'NH3',
        'ch4': 'CH4',
        'humidity': 'Humidity',
        'temperature': 'Temperature'
    }

    data = RawSensorData.objects.select_related('sensor').all()

    sensor_id = request.GET.get('sensor')
    pollutant = request.GET.get('pollutant')
    start = request.GET.get('start')
    end = request.GET.get('end')

    if sensor_id:
        data = data.filter(sensor_id=sensor_id)
    if start:
        data = data.filter(timestamp__gte=start)
    if end:
        data = data.filter(timestamp__lte=end)
    if pollutant and pollutant in pollutants:
        pollutants = [pollutant]

    if request.GET.get('export') == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="export.csv"'
        writer = csv.writer(response)
        writer.writerow(['Date/Time', 'Sensor'] + [pollutant_labels[p] for p in pollutants])
        for row in data:
            writer.writerow([row.timestamp, row.sensor.name] + [getattr(row, p, '') for p in pollutants])
        return response

    elif request.GET.get('export') == 'json':
        export_data = []
        for row in data:
            export_data.append({
                'timestamp': row.timestamp.isoformat(),
                'sensor': row.sensor.name,
                **{pollutant_labels[p]: getattr(row, p, '') for p in pollutants}
            })
        response = HttpResponse(json.dumps(export_data, indent=2), content_type='application/json')
        response['Content-Disposition'] = 'attachment; filename="export.json"'
        return response

    elif request.GET.get('export') == 'excel':
        rows = []
        for row in data:
            row_dict = {
                'Date/Time': row.timestamp,
                'Sensor': row.sensor.name,
            }
            for p in pollutants:
                row_dict[pollutant_labels[p]] = getattr(row, p, '')
            rows.append(row_dict)
        df = pd.DataFrame(rows)
        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = 'attachment; filename="export.xlsx"'
        with pd.ExcelWriter(response, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False)
        return response

    return render(request, 'data_management.html', {
        'sensors': sensors,
        'pollutants': [pollutant_labels[p] for p in pollutants],
        'pollutant_keys': pollutants,
        'data': data,
        'get_item': get_item,
        'request': request,
    })

def alert_management(request):
    alerts = Alert.objects.all()

    return render(request, 'alerts.html', {
        'alerts': alerts,
    })

def alerts(request):
    # Mark all as read when visiting the page
    Alert.objects.filter(is_read=False).update(is_read=True)
    alerts = Alert.objects.all()[:100]  # Show latest 100 alerts
    return render(request, 'dashboard/alerts.html', {'alerts': alerts})

def get_alert_count():
    return Alert.objects.filter(is_read=False).count()


@login_required
def alerts(request):
    Alert.objects.filter(is_read=False).update(is_read=True)
    alerts = Alert.objects.all()[:100]
    sensors = Sensor.objects.all()
    return render(request, 'dashboard/alerts.html', {'alerts': alerts, 'sensors': sensors})

@csrf_exempt
def chatbot_api(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        user_msg = data.get('message', '').lower()
        # Simple logic: you can expand this or connect to an AI model
        if 'average' in user_msg and 'pm2.5' in user_msg:
            avg = RawSensorData.objects.all().aggregate(avg_pm2_5=models.Avg('pm2_5'))['avg_pm2_5']
            reply = f"The average PM2.5 is {avg:.2f} µg/m³." if avg else "No data available."
        elif 'highest' in user_msg and 'temperature' in user_msg:
            max_temp = RawSensorData.objects.all().aggregate(max_temp=models.Max('temperature'))['max_temp']
            reply = f"The highest recorded temperature is {max_temp:.2f}°C." if max_temp else "No data available."
        elif 'sensor' in user_msg and 'offline' in user_msg:
            from django.utils import timezone
            from datetime import timedelta
            offline = RawSensorData.objects.filter(timestamp__lt=timezone.now()-timedelta(hours=2)).values_list('sensor__name', flat=True).distinct()
            reply = "Offline sensors: " + ", ".join(offline) if offline else "All sensors are online."
        else:
            reply = "Sorry, I can answer questions about air quality, sensor status, or trends. Try asking about average PM2.5, highest temperature, or offline sensors."
        return JsonResponse({'reply': reply})
    return JsonResponse({'reply': 'Invalid request.'})

def is_admin(user):
    return user.is_superuser or user.is_staff

@user_passes_test(is_admin)
def add_user(request):
    if request.method == 'POST':
        form = UserCreateForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password'])
            user.save()
            return redirect('dashboard:dashboard')
    else:
        form = UserCreateForm()
    return render(request, 'dashboard/add_user.html', {'form': form})

@user_passes_test(is_admin)
def sensor_management(request):
    if request.method == 'POST':
        form = SensorCreateForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('dashboard:sensor_management')
    else:
        form = SensorCreateForm()
    sensors = Sensor.objects.all()
    return render(request, 'dashboard/sensor_management.html', {'form': form, 'sensors': sensors})

@user_passes_test(is_admin)
def toggle_sensor_status(request, sensor_id):
    sensor = get_object_or_404(Sensor, id=sensor_id)
    sensor.is_active = not sensor.is_active
    sensor.save()
    return redirect('dashboard:sensor_management')

@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def user_management(request):
    users = User.objects.all()
    return render(request, 'dashboard/user_management.html', {'users': users})

@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def deactivate_user(request, user_id):
    user = get_object_or_404(User, id=user_id)
    if request.method == 'POST':
        user.is_active = False
        user.save()
    return redirect('dashboard:user_management')

@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def delete_user(request, user_id):
    user = get_object_or_404(User, id=user_id)
    if request.method == 'POST':
        user.delete()
    return redirect('dashboard:user_management')

@user_passes_test(lambda u: u.is_superuser or u.is_staff)
def delete_sensor(request, sensor_id):
    sensor = get_object_or_404(Sensor, id=sensor_id)
    if request.method == 'POST':
        sensor.delete()
    return redirect('dashboard:sensor_management')

@login_required
def download_report(request):
    sensor_id = request.GET.get('sensor_id')
    params = request.GET.getlist('param') or request.GET.get('param', '').split(',')
    date_from = request.GET.get('from')
    date_to = request.GET.get('to')

    sensor = get_object_or_404(Sensor, id=sensor_id)
    date_from = datetime.datetime.strptime(date_from, '%Y-%m-%d').date()
    date_to = datetime.datetime.strptime(date_to, '%Y-%m-%d').date()

    raw_qs = RawSensorData.objects.filter(
        sensor=sensor,
        timestamp__date__gte=date_from,
        timestamp__date__lte=date_to
    )

    summary = []
    pollutant_summaries = []
    all_pollutants = ['pm2_5', 'pm10', 'nh3', 'ch4', 'co', 'no2']
    params = request.GET.getlist('param') or request.GET.get('param', '').split(',')
    if not params or 'all' in params:
        params = all_pollutants
    for param in params:
        daily = (
            raw_qs.values('timestamp__date')
            .annotate(
                min_val=Min(param),
                max_val=Max(param),
                avg_val=Avg(param)
            )
            .order_by('timestamp__date')
        )
        values = [row['avg_val'] for row in daily if row['avg_val'] is not None]
        if values:
            overall_avg = sum(values) / len(values)
            max_day = max(daily, key=lambda x: x['max_val'] or 0)
            min_day = min(daily, key=lambda x: x['min_val'] or float('inf'))
            # Simple AQI logic
            def aqi_cat(val):
                if val is None:
                    return '-'
                if val < 50: return 'Good'
                if val < 100: return 'Moderate'
                return 'Unhealthy'
            pollutant_summaries.append({
                'param': param.upper(),
                'overall_avg': round(overall_avg, 1),
                'max_val': max_day['max_val'],
                'max_date': max_day['timestamp__date'],
                'min_val': min_day['min_val'],
                'min_date': min_day['timestamp__date'],
                'aqi_category': aqi_cat(overall_avg),
            })
        for row in daily:
            avg_val = row['avg_val']
            summary.append({
                'date': row['timestamp__date'],
                'parameter': param.upper(),
                'min': round(row['min_val'], 1) if row['min_val'] is not None else '-',
                'max': round(row['max_val'], 1) if row['max_val'] is not None else '-',
                'avg': round(avg_val, 1) if avg_val is not None else '-',
                'aqi': round(avg_val, 1) if avg_val is not None else '-',
                'aqi_category': aqi_cat(avg_val),
            })

    # Build a more detailed summary statement
    summary_lines = [
        f"Between {date_from.strftime('%b %d, %Y')} and {date_to.strftime('%b %d, %Y')}, sensor '{sensor.name}' at {sensor.location} monitored {', '.join([p['param'] for p in pollutant_summaries])}."
    ]
    for p in pollutant_summaries:
        summary_lines.append(
            f"For {p['param']}: The average value was {p['overall_avg']} ({p['aqi_category']}), "
            f"with the highest ({p['max_val']}) on {p['max_date']} and lowest ({p['min_val']}) on {p['min_date']}."
        )
    summary_lines.append("Refer to the table above for daily details. For health, avoid outdoor activities during high AQI periods.")

    summary_text = " ".join(summary_lines)

    # Render HTML template
    html_string = render_to_string('dashboard/report_pdf.html', {
        'sensor': sensor,
        'params': [p['param'] for p in pollutant_summaries],
        'date_from': date_from,
        'date_to': date_to,
        'summary': summary,
        'summary_text': summary_text,
        'user': request.user,
        'now': timezone.now(),
    })

    # PDF response
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="tanair_report_{sensor.name}_{date_from}_{date_to}.pdf"'

    # Create PDF
    p = canvas.Canvas(response, pagesize=A4)
    width, height = A4
    styles = getSampleStyleSheet()
    y = height - 50

    # Title
    p.setFont("Helvetica-Bold", 18)
    p.drawString(50, y, "TANAIR Pollution Summary Report")
    y -= 30

    # Metadata
    p.setFont("Helvetica", 11)
    p.drawString(50, y, f"Sensor: {sensor.name}   Location: {sensor.location}")
    y -= 18
    p.drawString(50, y, f"Parameters: {', '.join(params)}")
    y -= 18
    p.drawString(50, y, f"Period: {date_from} to {date_to}")
    y -= 18
    p.drawString(50, y, f"Generated by: {request.user.username}")
    y -= 30

    # Table
    table_data = [['Date', 'Parameter', 'Min', 'Max', 'Avg', 'AQI Category']]
    for row in summary:
        table_data.append([
            str(row['date']),
            row['parameter'],
            row['min'],
            row['max'],
            row['avg'],
            row['aqi_category'],
        ])
    table = Table(table_data, repeatRows=1)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#f5f6fa')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.HexColor('#1976d2')),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 11),
        ('BOTTOMPADDING', (0,0), (-1,0), 8),
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
    ]))
    w, h = table.wrapOn(p, width-100, y)
    table.drawOn(p, 50, y-h)
    y -= h + 20

    # Summary
    p.setFont("Helvetica-Bold", 12)
    p.drawString(50, y, "Summary:")
    y -= 16
    p.setFont("Helvetica", 11)
    text = p.beginText(50, y)
    for line in summary_text.splitlines():
        text.textLine(line)
    p.drawText(text)
    y = text.getY() - 20

    # Recommendations
    p.setFont("Helvetica-Oblique", 10)
    p.drawString(50, y, "Recommendations: Limit outdoor activity during pollution spikes. Refer to AQI guidelines for health advice.")
    y -= 30

    # Footer
    p.setFont("Helvetica", 8)
    p.drawRightString(width-50, 30, f"Generated on {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}  © TANAIR")

    p.showPage()
    p.save()
    return response

from django.contrib.auth.decorators import login_required
from habil.models import Sensor

@login_required
def report_form(request):
    sensors = Sensor.objects.all()
    return render(request, 'dashboard/report_form.html', {'sensors': sensors})