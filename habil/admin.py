# habil/admin.py
from django.contrib import admin
from .models import Sensor, RawSensorData, AQIData, PredictedValues,AQIResult

class RawSensorDataInline(admin.TabularInline):
    model = RawSensorData
    extra = 0
    readonly_fields = ('timestamp',)

class AQIDataInline(admin.TabularInline):
    model = AQIData
    extra = 0
    readonly_fields = ('timestamp',)

class PredictedValuesInline(admin.TabularInline):
    model = PredictedValues
    extra = 0

@admin.register(Sensor)
class SensorAdmin(admin.ModelAdmin):
    list_display = ('name', 'location', 'is_active', 'installation_date')
    list_filter = ('is_active', 'installation_date')
    search_fields = ('name', 'location')
    inlines = [RawSensorDataInline, AQIDataInline, PredictedValuesInline]

admin.site.register(RawSensorData)
admin.site.register(AQIData)
admin.site.register(PredictedValues)
admin.site.register(AQIResult)