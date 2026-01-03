# apps/admin_panel/migrations/0001_initial.py
from django.db import migrations, models
import django.db.models.deletion
from django.utils import timezone
import django.utils.timezone


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('accounts', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='AdminSettings',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('theme_mode', models.CharField(choices=[('light', 'Light'), ('dark', 'Dark'), ('system', 'System')], default='system', max_length=20)),
                ('site_email', models.EmailField(blank=True, max_length=254, null=True)),
                ('support_contact', models.CharField(blank=True, max_length=64, null=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name='TaskCategory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('code', models.CharField(max_length=32, unique=True, choices=[('video_ads', 'Video Ads'), ('survey', 'Survey'), ('app_install', 'App Install'), ('other', 'Other')])),
                ('name', models.CharField(max_length=64)),
                ('description', models.TextField(blank=True)),
                ('reward_amount', models.DecimalField(max_digits=12, decimal_places=2)),
                ('max_daily_completions', models.PositiveIntegerField(default=0)),
                ('active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name='UserProfile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('invitation_code', models.CharField(max_length=64, unique=True, blank=True, null=True)),
                ('invited_by', models.CharField(max_length=150, blank=True, null=True)),
                ('subscription_status', models.CharField(max_length=20, choices=[('trial', 'Trial'), ('active', 'Active'), ('expired', 'Expired')], default='trial')),
                ('trial_expiry', models.DateTimeField(blank=True, null=True)),
                ('balance', models.DecimalField(max_digits=14, decimal_places=2, default=0)),
                ('account_number', models.CharField(max_length=64, blank=True, null=True)),
                ('age', models.PositiveIntegerField(blank=True, null=True)),
                ('gender', models.CharField(max_length=20, blank=True, null=True)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='profile', to='accounts.user')),
            ],
        ),
        migrations.CreateModel(
            name='RewardLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('amount', models.DecimalField(max_digits=12, decimal_places=2)),
                ('source_ref', models.CharField(max_length=128, blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='reward_logs', to='accounts.user')),
                ('category', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='admin_panel.taskcategory')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='TransactionLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('actor', models.CharField(default='system', max_length=32)),
                ('amount', models.DecimalField(max_digits=14, decimal_places=2)),
                ('txn_type', models.CharField(max_length=20, choices=[('reward', 'Reward'), ('withdrawal', 'Withdrawal'), ('subscription', 'Subscription'), ('system', 'System')])),
                ('status', models.CharField(default='pending', max_length=16, choices=[('pending', 'Pending'), ('success', 'Success'), ('failed', 'Failed')])),
                ('details', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('processed_at', models.DateTimeField(blank=True, null=True)),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='accounts.user')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='AdminLoginAudit',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('username_entered', models.CharField(blank=True, max_length=150)),
                ('ip_address', models.GenericIPAddressField(blank=True, null=True)),
                ('user_agent', models.CharField(blank=True, max_length=512)),
                ('success', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('admin_user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='accounts.user')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='PendingManualUser',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255)),
                ('age', models.PositiveIntegerField()),
                ('gender', models.CharField(max_length=20, choices=[('male', 'Male'), ('female', 'Female'), ('other', 'Other')])),
                ('email', models.EmailField(max_length=254)),
                ('account_number', models.CharField(max_length=64)),
                ('invitation_code', models.CharField(max_length=64, blank=True, null=True)),
                ('temporary_password', models.CharField(max_length=128, blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('verified', models.BooleanField(default=False)),
            ],
            options={
                'indexes': [models.Index(fields=['email'], name='admin_panel_pendingmanualuser_email_idx')],
            },
        ),
        migrations.CreateModel(
            name='ManualUserOTP',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('otp_code', models.CharField(max_length=8)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('expires_at', models.DateTimeField()),
                ('pending_user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='otps', to='admin_panel.pendingmanualuser')),
            ],
        ),
        migrations.CreateModel(
            name='Notification',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=255)),
                ('message', models.TextField()),
                ('category', models.CharField(default='general', max_length=64)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='notifications', to='accounts.user')),
            ],
        ),
        migrations.CreateModel(
            name='AdminNotification',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=255)),
                ('message', models.TextField()),
                ('category', models.CharField(default='system', max_length=64)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.CreateModel(
            name='GiftOffer',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=255)),
                ('description', models.TextField(blank=True, null=True)),
                ('reward_amount', models.DecimalField(max_digits=12, decimal_places=2)),
                ('required_invites', models.PositiveIntegerField(default=0)),
                ('time_limit_hours', models.PositiveIntegerField(default=0)),
                ('extra_video_count', models.PositiveIntegerField(default=0)),
                ('earning_per_extra_video', models.DecimalField(max_digits=12, decimal_places=2, default=0)),
                ('active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name='TaskControl',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('videos_count', models.PositiveIntegerField(default=0)),
                ('video_earning', models.DecimalField(max_digits=12, decimal_places=2, default=0)),
                ('surveys_count', models.PositiveIntegerField(default=0)),
                ('survey_earning', models.DecimalField(max_digits=12, decimal_places=2, default=0)),
                ('app_tests_count', models.PositiveIntegerField(default=0)),
                ('app_test_earning', models.DecimalField(max_digits=12, decimal_places=2, default=0)),
                ('invite_cost', models.DecimalField(max_digits=12, decimal_places=2, default=0)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name='PayrollEntry',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255)),
                ('account_number', models.CharField(max_length=64)),
                ('amount', models.DecimalField(max_digits=14, decimal_places=2)),
                ('auto_withdraw', models.BooleanField(default=False)),
                ('enabled', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
        ),
    ]
