from django import forms
from django.core.exceptions import ValidationError
from voting.models import UserData, VotingRecord
import re


def format_rut(rut_raw):
    """
    Formatea un RUT quitando puntos y guiones, y agregando el guión antes del dígito verificador.
    """
    rut_clean = str(rut_raw).strip().replace('.', '').replace('-', '').replace(' ', '')
    
    if len(rut_clean) < 2:
        return rut_clean.upper()
    
    cuerpo = rut_clean[:-1]
    dv = rut_clean[-1]
    
    return f"{cuerpo}-{dv.upper()}"


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


class MilitanteRegistrationForm(forms.Form):
    """Formulario para registro de militantes con token"""
    rut = forms.CharField(
        max_length=20,
        label="RUT",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ej: 12345678-K'
        }),
        help_text="Ingrese su RUT sin puntos y con guión"
    )
    password = forms.CharField(
        label="Contraseña",
        min_length=8,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Mínimo 8 caracteres'
        }),
        help_text="Mínimo 8 caracteres, 1 número, 1 símbolo y 1 mayúscula"
    )
    password_confirm = forms.CharField(
        label="Confirmar Contraseña",
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Repita su contraseña'
        })
    )

    def clean_rut(self):
        """Valida y formatea el RUT"""
        rut = self.cleaned_data.get('rut')
        if not rut:
            raise ValidationError("El RUT es requerido.")
        
        # Formatear el RUT
        rut_formatted = format_rut(rut)
        
        # Validar formato
        rut_pattern = r'^\d{1,8}-[0-9kK]$'
        if not re.match(rut_pattern, rut_formatted):
            raise ValidationError("El RUT debe tener el formato correcto (Ej: 12345678-K)")
        
        return rut_formatted

    def clean_password(self):
        """Valida la contraseña"""
        password = self.cleaned_data.get('password')
        if not password:
            raise ValidationError("La contraseña es requerida.")
        
        if len(password) < 8:
            raise ValidationError("La contraseña debe tener al menos 8 caracteres.")
        
        if not re.search(r'[A-Z]', password):
            raise ValidationError("La contraseña debe tener al menos una mayúscula.")
        
        if not re.search(r'[0-9]', password):
            raise ValidationError("La contraseña debe tener al menos un número.")
        
        if not re.search(r'[!@#$%^&*(),.?":{}|<>_\-+=\[\]\\;\'`~]', password):
            raise ValidationError("La contraseña debe tener al menos un símbolo.")
        
        return password

    def clean(self):
        """Valida que las contraseñas coincidan"""
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        password_confirm = cleaned_data.get('password_confirm')
        
        if password and password_confirm and password != password_confirm:
            raise ValidationError("Las contraseñas no coinciden.")
        
        return cleaned_data


class MilitanteLoginForm(forms.Form):
    """Formulario de login para militantes"""
    rut = forms.CharField(
        max_length=20,
        label="RUT",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ej: 12345678-K'
        })
    )
    password = forms.CharField(
        label="Contraseña",
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ingrese su contraseña',
            'id': 'password-input'
        })
    )

    def clean_rut(self):
        """Valida y formatea el RUT"""
        rut = self.cleaned_data.get('rut')
        if not rut:
            raise ValidationError("El RUT es requerido.")
        
        # Formatear el RUT
        rut_formatted = format_rut(rut)
        
        # Validar formato
        rut_pattern = r'^\d{1,8}-[0-9kK]$'
        if not re.match(rut_pattern, rut_formatted):
            raise ValidationError("El RUT debe tener el formato correcto (Ej: 12345678-K)")
        
        return rut_formatted


class MilitantePasswordResetRequestForm(forms.Form):
    """Formulario para solicitar recuperación de contraseña"""
    rut = forms.CharField(
        max_length=20,
        label="RUT",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ej: 12345678-K'
        })
    )

    def clean_rut(self):
        """Valida y formatea el RUT"""
        rut = self.cleaned_data.get('rut')
        if not rut:
            raise ValidationError("El RUT es requerido.")
        
        rut_formatted = format_rut(rut)
        
        rut_pattern = r'^\d{1,8}-[0-9kK]$'
        if not re.match(rut_pattern, rut_formatted):
            raise ValidationError("El RUT debe tener el formato correcto (Ej: 12345678-K)")
        
        return rut_formatted


class MilitantePasswordResetForm(forms.Form):
    """Formulario para restablecer contraseña de militante"""
    password = forms.CharField(
        label="Nueva Contraseña",
        min_length=8,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Mínimo 8 caracteres'
        }),
        help_text="Mínimo 8 caracteres, 1 número, 1 símbolo y 1 mayúscula"
    )
    password_confirm = forms.CharField(
        label="Confirmar Contraseña",
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Repita su contraseña'
        })
    )

    def clean_password(self):
        """Valida la contraseña"""
        password = self.cleaned_data.get('password')
        if not password:
            raise ValidationError("La contraseña es requerida.")
        
        if len(password) < 8:
            raise ValidationError("La contraseña debe tener al menos 8 caracteres.")
        
        if not re.search(r'[A-Z]', password):
            raise ValidationError("La contraseña debe tener al menos una mayúscula.")
        
        if not re.search(r'[0-9]', password):
            raise ValidationError("La contraseña debe tener al menos un número.")
        
        if not re.search(r'[!@#$%^&*(),.?":{}|<>_\-+=\[\]\\;\'`~]', password):
            raise ValidationError("La contraseña debe tener al menos un símbolo.")
        
        return password

    def clean(self):
        """Valida que las contraseñas coincidan"""
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        password_confirm = cleaned_data.get('password_confirm')
        
        if password and password_confirm and password != password_confirm:
            raise ValidationError("Las contraseñas no coinciden.")
        
        return cleaned_data
