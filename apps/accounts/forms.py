
from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.apps import apps
import random
import string
def get_user_model():
    return apps.get_model("accounts", "User")
# ------------------------------
# Helper: OTP generator
# ------------------------------
def generate_otp(length=6):
    """Generate a 6-digit OTP code."""
    return ''.join(random.choices(string.digits, k=length))

# ------------------------------
# LOGIN FORM (for both admin & users)
# ------------------------------
class LoginForm(AuthenticationForm):
    username = forms.CharField(
        label="Username",
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "Enter username",
        })
    )
    password = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={
            "class": "form-control",
            "placeholder": "Enter password",
        })
    )

# ------------------------------
# USER SIGNUP FORM
# ------------------------------
class SignupForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            "class": "form-control",
            "placeholder": "Enter password",
        }),
        required=True
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            "class": "form-control",
            "placeholder": "Confirm password",
        }),
        required=True
    )

    class Meta:
        model = get_user_model()
        fields = [
            "username",
            "gender",
            "age",
            "account_number",
            "email",
            "invitation_code",
        ]
        widgets = {
            "username": forms.TextInput(attrs={"class": "form-control", "placeholder": "Full name"}),
            "gender": forms.Select(attrs={"class": "form-control"}),
            "age": forms.NumberInput(attrs={"class": "form-control", "placeholder": "Age"}),
            "account_number": forms.TextInput(attrs={"class": "form-control", "placeholder": "Account number"}),
            "email": forms.EmailInput(attrs={"class": "form-control", "placeholder": "Email address"}),
            "invitation_code": forms.TextInput(attrs={"class": "form-control", "placeholder": "Invitation code (required)"}),
        }

    def clean_email(self):
        email = self.cleaned_data.get("email")
        if not email:
            raise forms.ValidationError("Email is required.")
        User = get_user_model()
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("This email is already registered.")
        return email

    def clean_account_number(self):
        acct = self.cleaned_data.get("account_number")
        if not acct:
            raise forms.ValidationError("Account number is required.")
        User = get_user_model()
        if User.objects.filter(account_number=acct).exists():
            raise forms.ValidationError("Account number already exists.")
        return acct

    def clean_invitation_code(self):
        code = self.cleaned_data.get("invitation_code")
        if not code:
            raise forms.ValidationError("Invitation code is required.")
        User = get_user_model()
        inviter = User.objects.filter(invitation_code=code).first()
        if inviter is None:
            raise forms.ValidationError("Invalid invitation code.")
        return code

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm = cleaned_data.get("confirm_password")
        if password and confirm and password != confirm:
            raise forms.ValidationError("Passwords do not match.")
        return cleaned_data

# ------------------------------
# OTP VERIFICATION FORM
# ------------------------------
class OTPVerificationForm(forms.Form):
    otp = forms.CharField(
        max_length=6,
        label="OTP",
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "Enter OTP",
        })
    )
