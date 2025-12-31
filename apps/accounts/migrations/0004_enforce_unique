from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0003_create_admin_user"),
    ]

    operations = [
        migrations.AlterField(
            model_name="user",
            name="account_number",
            field=models.CharField(
                max_length=15,
                unique=True,
                null=False,
                blank=False
            ),
        ),
    ]
