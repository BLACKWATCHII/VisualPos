from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.contrib.auth.forms import AuthenticationForm
from customer.models import Cliente
from django.core.validators import RegexValidator
from django.core.exceptions import ValidationError

class CustomUserCreationForm(UserCreationForm):
    username = forms.CharField(
        label="Nombre de usuario",
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    password1 = forms.CharField(
        label="Contraseña",
        widget=forms.PasswordInput(attrs={'class': 'form-control'})
    )
    password2 = forms.CharField(
        label="Confirmar contraseña",
        widget=forms.PasswordInput(attrs={'class': 'form-control'})
    )

    class Meta:
        model = User
        fields = ("username", "password1", "password2")

class CustomAuthenticationForm(AuthenticationForm):
    username = forms.CharField(
        label="Nombre de usuario",
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    password = forms.CharField(
        label="Contraseña",
        widget=forms.PasswordInput(attrs={'class': 'form-control'})
    )
    
class NumericCedulaField(forms.CharField):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.validators.append(RegexValidator(
            regex=r'^\d{8,10}$',
            message='Ingrese una cédula válida de entre 8 y 10 dígitos.',
            code='invalid_cedula'
        ))

class ClienteForm(forms.ModelForm):
    cedula = NumericCedulaField(
        label="Cédula",
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        error_messages={
            'invalid': 'Este campo solo permite números y debe tener entre 8 y 10 dígitos.'
        }
    )

    class Meta:
        model = Cliente
        fields = ['name', 'lastname', 'address', 'city', 'cedula', 'phone', 'email', 'pdf']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'lastname': forms.TextInput(attrs={'class': 'form-control'}),
            'address': forms.TextInput(attrs={'class': 'form-control'}),
            'city': forms.TextInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'pdf': forms.FileInput(attrs={'class': 'form-control'}),
        }

    def clean_cedula(self):
        cedula = self.cleaned_data.get('cedula')
        if not cedula.isdigit() or not (8 <= len(cedula) <= 10):
            raise ValidationError('Ingrese una cédula válida de entre 8 y 10 dígitos.')
        if Cliente.objects.filter(cedula=cedula).exists():
            raise ValidationError('La cédula ya está registrada.')
        return cedula
