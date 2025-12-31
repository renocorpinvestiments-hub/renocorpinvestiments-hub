from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.apps import apps
import random
import string
def normalize_phone(phone: str, default_country_code="256"):
    """
    Normalize phone number to international format.
    Examples:
    0700123456  -> +256700123456
    700123456   -> +256700123456
    +256700123456 -> +256700123456
    """
    if not phone:
        return None

    phone = phone.strip().replace(" ", "")

    # Already international
    if phone.startswith("+"):
        digits = phone[1:]
    else:
        digits = phone

        # Remove leading zero
        if digits.startswith("0"):
            digits = digits[1:]

        # Prepend country code
        digits = default_country_code + digits

    if not digits.isdigit():
        raise forms.ValidationError("Invalid phone number format.")

    if len(digits) < 11 or len(digits) > 15:
        raise forms.ValidationError("Invalid phone number length.")

    return f"+{digits}"

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
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["username"].widget.attrs.update({
            "class": "form-control",
            "placeholder": "Enter username",
        })

        self.fields["password"].widget.attrs.update({
            "class": "form-control",
            "placeholder": "Enter password",
        })


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

    account_number = forms.CharField(
        required=True,
        max_length=15,
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "Phone number (e.g. +2567XXXXXXXX)"
        })
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
            "username": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Full name"
            }),
            "gender": forms.Select(attrs={"class": "form-control"}),
            "age": forms.NumberInput(attrs={
                "class": "form-control",
                "placeholder": "Age"
            }),
            "email": forms.EmailInput(attrs={
                "class": "form-control",
                "placeholder": "Email address"
            }),
            "invitation_code": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Invitation code (required)"
            }),
        }

    # ------------------------------
    # VALIDATIONS
    # ------------------------------
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
            raise forms.ValidationError("Phone number is required.")

        # Allow digits and optional +
        if not acct.replace("+", "").isdigit():
            raise forms.ValidationError("Enter a valid phone number.")

        # Length check (international standard)
        digits = acct.replace("+", "")
        if len(digits) < 9 or len(digits) > 15:
            raise forms.ValidationError(
                "Phone number must be between 9 and 15 digits."
            )

        User = get_user_model()
        if User.objects.filter(account_number=acct).exists():
            raise forms.ValidationError(
                "This phone number is already registered."
            )

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
