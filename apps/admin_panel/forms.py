# apps/admin_panel/forms.py
from django.core.exceptions import ValidationError
from django import forms
from .models import (
    GiftOffer,
    TaskControl,
    AdminSettings,
    PayrollEntry,
    PendingManualUser
    
)
from django.contrib.auth import get_user_model




# ============================================================
# ADMIN SETTINGS FORM
# ============================================================
class AdminSettingsForm(forms.ModelForm):
    new_password = forms.CharField(
        label="New Password",
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        required=False,
    )
    confirm_password = forms.CharField(
        label="Confirm Password",
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        required=False,
    )

    class Meta:
        model = AdminSettings
        fields = ['theme_mode', 'support_contact']
        widgets = {
            'theme_mode': forms.Select(attrs={'class': 'form-select'}),
            'support_contact': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Support WhatsApp/Phone Number'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        pwd = cleaned_data.get("new_password")
        confirm = cleaned_data.get("confirm_password")
        if pwd or confirm:
            if pwd != confirm:
                raise ValidationError("Passwords do not match.")
        return cleaned_data

# ============================================================
# GIFT OFFER FORM
# ============================================================
class GiftOfferForm(forms.ModelForm):
    class Meta:
        model = GiftOffer
        fields = [
            'title', 'description', 'reward_amount',
            'required_invites', 'time_limit_hours',
            'extra_video_count', 'earning_per_extra_video',
            'active'
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'reward_amount': forms.NumberInput(attrs={'class': 'form-control'}),
            'required_invites': forms.NumberInput(attrs={'class': 'form-control'}),
            'time_limit_hours': forms.NumberInput(attrs={'class': 'form-control'}),
            'extra_video_count': forms.NumberInput(attrs={'class': 'form-control'}),
            'earning_per_extra_video': forms.NumberInput(attrs={'class': 'form-control'}),
            'active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


# ============================================================
# TASK CONTROL FORM
# ============================================================
class TaskControlForm(forms.ModelForm):
    class Meta:
        model = TaskControl
        fields = [
            'videos_count', 'video_earning',
            'surveys_count', 'survey_earning',
            'app_tests_count', 'app_test_earning',
            'invite_cost'
        ]
        widgets = {
            'videos_count': forms.NumberInput(attrs={'class': 'form-control'}),
            'video_earning': forms.NumberInput(attrs={'class': 'form-control'}),
            'surveys_count': forms.NumberInput(attrs={'class': 'form-control'}),
            'survey_earning': forms.NumberInput(attrs={'class': 'form-control'}),
            'app_tests_count': forms.NumberInput(attrs={'class': 'form-control'}),
            'app_test_earning': forms.NumberInput(attrs={'class': 'form-control'}),
            'invite_cost': forms.NumberInput(attrs={'class': 'form-control'}),
        }


# ============================================================
# PAYROLL ENTRY FORM
# ============================================================
class PayrollEntryForm(forms.ModelForm):
    class Meta:
        model = PayrollEntry
        fields = [
            'name', 'account_number', 'amount',
            'auto_withdraw', 'enabled'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'account_number': forms.TextInput(attrs={'class': 'form-control'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control'}),
            'auto_withdraw': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'enabled': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


User = get_user_model()

class PendingManualUserForm(forms.ModelForm):

    class Meta:
        model = PendingManualUser
        fields = ["name", "age", "gender", "account_number", "email"]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'age': forms.NumberInput(attrs={'class': 'form-control'}),
            'gender': forms.Select(attrs={'class': 'form-select'}),
            'account_number': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
        }
        
    def clean_email(self):
        email = self.cleaned_data["email"].lower().strip()

        # 🔐 Block ONLY if a REAL user exists
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError("This email already belongs to a registered user.")
        if PendingManualUser.objects.filter(email__iexact=email, verified=False).exists():
            raise ValidationError("This email already has a pending verification.")
        # 🟢 Allow reuse if only PendingManualUser exists
        return email
        
class AdminPasswordConfirmForm(forms.Form):
    password = forms.CharField(
        label="Confirm your password",
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
    )

    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

    def clean_password(self):
        password = self.cleaned_data.get("password")
        if not self.user.check_password(password):
            raise ValidationError("Incorrect admin password.")
        return password
