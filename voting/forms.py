from django import forms
from django.core.exceptions import ValidationError
from voting.models import UserData, VotingRecord
import re


class VoterRegistrationForm(forms.Form):
    """Formulario para que los votantes se registren y voten"""
    name = forms.CharField(
        max_length=100,
        label="Nombre",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ingrese su nombre'
        })
    )
    lastname = forms.CharField(
        max_length=100,
        label="Apellido",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ingrese su apellido'
        })
    )
    rut = forms.CharField(
        max_length=20,
        label="RUT",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ej: 12345678-K'
        })
    )
    mail = forms.EmailField(
        label="Correo Electrónico",
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ingrese su correo electrónico'
        }),
        help_text="Es importante proporcionar un correo válido. Se enviará un correo de confirmación."
    )

    def clean_rut(self):
        """Valida el formato del RUT chileno"""
        rut = self.cleaned_data.get('rut')
        if not rut:
            raise ValidationError("El RUT es requerido.")
        
        # Formato simple de validación RUT chileno
        rut_pattern = r'^\d{1,8}-[0-9kK]$'
        if not re.match(rut_pattern, rut):
            raise ValidationError("El RUT debe tener el formato correcto (Ej: 12345678-K)")
        
        return rut.upper()

    def clean_mail(self):
        """Valida el correo electrónico"""
        mail = self.cleaned_data.get('mail')
        if not mail:
            raise ValidationError("El correo electrónico es requerido.")
        return mail.lower()


class MaintainerLoginForm(forms.Form):
    """Formulario de login para maintainers"""
    mail = forms.EmailField(
        label="Correo Electrónico",
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ingrese su correo'
        })
    )
    password = forms.CharField(
        label="Contraseña",
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ingrese su contraseña'
        })
    )
