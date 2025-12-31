from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0001_initial'),
    ]

    operations = [

        # 1️⃣ Account number added as NULLABLE (NO UNIQUE YET)
        migrations.AddField(
            model_name='user',
            name='account_number',
            field=models.CharField(
                max_length=15,
                null=True,
                blank=True,
                help_text="User phone number for withdrawals"
            ),
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
    ]
