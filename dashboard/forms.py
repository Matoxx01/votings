from django import forms
from django.contrib.auth.hashers import make_password
from django.db.models import Case, When, IntegerField
from voting.models import Voting, Subject, Maintainer, Region


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


class VotingForm(forms.ModelForm):
    """Formulario para crear/editar votaciones"""
    class Meta:
        model = Voting
        fields = ['title', 'description', 'image', 'id_region', 'start_date', 'finish_date', 'is_active']
        labels = {
            'title': 'Título',
            'description': 'Descripción',
            'image': 'Imagen',
            'id_region': 'Región',
            'start_date': 'Fecha de Inicio',
            'finish_date': 'Fecha de Finalización',
            'is_active': 'Activa',
        }
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'image': forms.FileInput(attrs={'class': 'form-control'}),
            'id_region': forms.Select(attrs={'class': 'form-control'}),
            'start_date': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'finish_date': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Ordenar regiones: S/Region (17) primero, luego por id ascendente
        regions = Region.objects.annotate(
            order=Case(
                When(id=17, then=0),
                default='id',
                output_field=IntegerField()
            )
        ).order_by('order')
        self.fields['id_region'].queryset = regions
        self.fields['id_region'].initial = 17  # S/Region por defecto


class SubjectForm(forms.ModelForm):
    """Formulario para crear/editar subjects"""
    class Meta:
        model = Subject
        fields = ['name', 'description']
        labels = {
            'name': 'Nombre',
            'description': 'Descripción',
        }
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class UserDataUploadForm(forms.Form):
    """Formulario para cargar datos de usuarios desde Excel"""
    voting_id = forms.IntegerField(
        label="Seleccione una Votación",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    file = forms.FileField(
        label="Archivo Excel",
        widget=forms.FileInput(attrs={'class': 'form-control'})
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['voting_id'].widget = forms.Select(
            choices=[(v.id, v.title) for v in Voting.objects.all()],
            attrs={'class': 'form-control'}
        )


class MilitanteInviteForm(forms.Form):
    """Formulario para enviar invitaciones de registro a militantes desde Excel"""
    file = forms.FileField(
        label="Archivo Excel",
        widget=forms.FileInput(attrs={'class': 'form-control'}),
        help_text="Columna A: RUT, Columna B: Nombre, Columna C: Correo"
    )


class MaintainerEditForm(forms.ModelForm):
    """Formulario para editar administradores (sin cambiar contraseña)"""
    class Meta:
        model = Maintainer
        fields = ['name', 'lastname', 'mail', 'id_role', 'is_active']
        labels = {
            'name': 'Nombre',
            'lastname': 'Apellido',
            'mail': 'Correo Electrónico',
            'id_role': 'Rol',
            'is_active': 'Activo',
        }
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'lastname': forms.TextInput(attrs={'class': 'form-control'}),
            'mail': forms.EmailInput(attrs={'class': 'form-control'}),
            'id_role': forms.Select(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class MaintainerCreateForm(forms.ModelForm):
    """Formulario para crear nuevos administradores"""
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        label='Contraseña',
        help_text='La contraseña será almacenada de forma segura.'
    )
    
    class Meta:
        model = Maintainer
        fields = ['name', 'lastname', 'mail', 'id_role', 'password', 'is_active']
        labels = {
            'name': 'Nombre',
            'lastname': 'Apellido',
            'mail': 'Correo Electrónico',
            'id_role': 'Rol',
            'is_active': 'Activo',
        }
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'lastname': forms.TextInput(attrs={'class': 'form-control'}),
            'mail': forms.EmailInput(attrs={'class': 'form-control'}),
            'id_role': forms.Select(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def save(self, commit=True):
        maintainer = super().save(commit=False)
        # Hashear la contraseña usando make_password de Django
        maintainer.password = make_password(self.cleaned_data['password'])
        if commit:
            maintainer.save()
        return maintainer

