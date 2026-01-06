from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.apps import apps


# -------------------------------------------------
# PHONE NORMALIZATION
# -------------------------------------------------
def normalize_phone(phone: str, default_country_code="256"):
    """
    Normalize phone number to international format.
    Examples:
    0700123456    -> +256700123456
    700123456     -> +256700123456
    +256700123456 -> +256700123456
    """
    if not phone:
        return None

    phone = phone.strip().replace(" ", "")

    if phone.startswith("+"):
        digits = phone[1:]
    else:
        digits = phone
        if digits.startswith("0"):
            digits = digits[1:]
        digits = default_country_code + digits

    if not digits.isdigit():
        raise forms.ValidationError("Invalid phone number format.")

    if len(digits) < 11 or len(digits) > 15:
        raise forms.ValidationError("Invalid phone number length.")

    return f"+{digits}"


def get_user_model():
    return apps.get_model("accounts", "User")


# -------------------------------------------------
# LOGIN FORM
# -------------------------------------------------
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


# -------------------------------------------------
# SIGNUP FORM (NO OTP)
# -------------------------------------------------
class SignupForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            "class": "form-control",
            "placeholder": "Enter password",
        }),
        required=True,
    )

    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            "class": "form-control",
            "placeholder": "Confirm password",
        }),
        required=True,
    )

    account_number = forms.CharField(
        required=True,
        max_length=15,
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "Phone number (e.g. +2567XXXXXXXX)",
        }),
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
                "placeholder": "Full name",
            }),
            "gender": forms.Select(attrs={"class": "form-control"}),
            "age": forms.NumberInput(attrs={
                "class": "form-control",
                "placeholder": "Age",
            }),
            "email": forms.EmailInput(attrs={
                "class": "form-control",
                "placeholder": "Email address",
            }),
            "invitation_code": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Invitation code (required)",
            }),
        }

    # -------------------------------------------------
    # VALIDATIONS
    # -------------------------------------------------
    def clean_email(self):
        email = self.cleaned_data.get("email")

        if not email:
            raise forms.ValidationError("Email is required.")

        User = get_user_model()
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("This email is already registered.")

        return email

    def clean_account_number(self):
        raw_phone = self.cleaned_data.get("account_number")

        if not raw_phone:
            raise forms.ValidationError("Phone number is required.")

        phone = normalize_phone(raw_phone)

        User = get_user_model()
        if User.objects.filter(account_number=phone).exists():
            raise forms.ValidationError("This phone number is already registered.")

        return phone

    def clean_invitation_code(self):
        code = self.cleaned_data.get("invitation_code")

        if not code:
            raise forms.ValidationError("Invitation code is required.")

        User = get_user_model()
        if not User.objects.filter(invitation_code=code).exists():
            raise forms.ValidationError("Invalid invitation code.")

        return code

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm = cleaned_data.get("confirm_password")

        if password and confirm and password != confirm:
            raise forms.ValidationError("Passwords do not match.")

        return cleaned_data
