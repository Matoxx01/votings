from django import forms
from voting.models import Voting, Subject


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
        fields = ['title', 'description', 'image', 'start_date', 'finish_date', 'is_active']
        labels = {
            'title': 'Título',
            'description': 'Descripción',
            'image': 'Imagen',
            'start_date': 'Fecha de Inicio',
            'finish_date': 'Fecha de Finalización',
            'is_active': 'Activa',
        }
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'image': forms.FileInput(attrs={'class': 'form-control'}),
            'start_date': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'finish_date': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


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
