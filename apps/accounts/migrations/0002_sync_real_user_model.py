from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0001_initial'),
    ]

    operations = [

        # --------- User model new fields ---------
        migrations.AddField(
            model_name='user',
            name='email',
            field=models.EmailField(max_length=254, unique=True, default=''),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='user',
            name='account_number',
            field=models.CharField(max_length=32, unique=True, default='TEMP0000'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='user',
            name='temp_flag',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='user',
            name='age',
            field=models.PositiveIntegerField(null=True, blank=True),
        ),
        migrations.AddField(
            model_name='user',
            name='gender',
            field=models.CharField(max_length=10, default='other'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='user',
            name='invitation_code',
            field=models.CharField(max_length=32, unique=True, null=True, blank=True),
        ),
        migrations.AddField(
            model_name='user',
            name='subscription_status',
            field=models.CharField(max_length=10, default='inactive'),
        ),
        migrations.AddField(
            model_name='user',
            name='balance',
            field=models.DecimalField(max_digits=12, decimal_places=2, default=0),
        ),
        migrations.AddField(
            model_name='user',
            name='invited_by',
            field=models.ForeignKey(
                to='accounts.user',
                null=True,
                blank=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='invited_users'
            ),
        ),

        # --------- EmailOTP table ---------
        migrations.CreateModel(
            name='EmailOTP',
            fields=[
                ('id', models.BigAutoField(primary_key=True, serialize=False)),
                ('email', models.EmailField(max_length=254)),
                ('otp', models.CharField(max_length=8)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('verified', models.BooleanField(default=False)),
                ('attempts', models.PositiveSmallIntegerField(default=0)),
            ],
        ),

        # --------- Indexes ---------
        migrations.AddIndex(
            model_name='user',
            index=models.Index(fields=['username'], name='user_username_idx'),
        ),
        migrations.AddIndex(
            model_name='user',
            index=models.Index(fields=['account_number'], name='user_account_idx'),
        ),
        migrations.AddIndex(
            model_name='user',
            index=models.Index(fields=['email'], name='user_email_idx'),
        ),
        migrations.AddIndex(
            model_name='emailotp',
            index=models.Index(fields=['email'], name='otp_email_idx'),
        ),
        migrations.AddIndex(
            model_name='emailotp',
            index=models.Index(fields=['created_at'], name='otp_created_idx'),
        ),
  ]
