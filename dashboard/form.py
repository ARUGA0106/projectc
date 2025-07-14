from django import forms
from django.contrib.auth.models import User
from habil.models import Sensor

class UserCreateForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput)
    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'is_staff', 'is_superuser']

class SensorCreateForm(forms.ModelForm):
    class Meta:
        model = Sensor
        fields = [
            'name',
            'location',
            'latitude',
            'longitude',
            'installation_date',
            'is_active',
            'description',
        ]