# Generated by Django 5.2.2 on 2025-07-13 09:22

import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('habil', '0006_alert_profile'),
    ]

    operations = [
        migrations.CreateModel(
            name='AQIAnalytics',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('timestamp', models.DateTimeField(default=django.utils.timezone.now)),
                ('overall_aqi', models.IntegerField()),
                ('aqi_category', models.CharField(max_length=20)),
                ('exposure_index', models.FloatField()),
                ('sensor_health_score', models.FloatField()),
                ('forecast_json', models.JSONField(default=dict)),
                ('pollution_hotspot', models.BooleanField(default=False)),
                ('health_risk_alert', models.CharField(blank=True, max_length=100, null=True)),
                ('source_attribution', models.CharField(blank=True, max_length=100, null=True)),
                ('sensor', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='aqi_analytics', to='habil.sensor')),
            ],
            options={
                'ordering': ['-timestamp'],
            },
        ),
        migrations.CreateModel(
            name='PollutionForecast',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('timestamp', models.DateTimeField()),
                ('pollutant', models.CharField(max_length=10)),
                ('predicted_value', models.FloatField()),
                ('horizon_hours', models.IntegerField()),
                ('sensor', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='forecasts', to='habil.sensor')),
            ],
            options={
                'ordering': ['-timestamp'],
            },
        ),
        migrations.CreateModel(
            name='PollutionTrend',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('period', models.CharField(max_length=10)),
                ('pollutant', models.CharField(max_length=10)),
                ('avg_value', models.FloatField()),
                ('max_value', models.FloatField()),
                ('min_value', models.FloatField()),
                ('std_dev', models.FloatField()),
                ('start_date', models.DateField()),
                ('end_date', models.DateField()),
                ('sensor', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='pollution_trends', to='habil.sensor')),
            ],
            options={
                'ordering': ['-start_date'],
            },
        ),
        migrations.CreateModel(
            name='SensorHealth',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('timestamp', models.DateTimeField(default=django.utils.timezone.now)),
                ('uptime_percent', models.FloatField()),
                ('data_completeness', models.FloatField()),
                ('latency_seconds', models.FloatField()),
                ('erratic_flag', models.BooleanField(default=False)),
                ('sensor', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='health', to='habil.sensor')),
            ],
            options={
                'ordering': ['-timestamp'],
            },
        ),
    ]
