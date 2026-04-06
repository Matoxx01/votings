# Generated manually
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("voting", "0013_create_initial_roles"),
    ]

    operations = [
        migrations.AlterField(
            model_name="militanteregistrationtoken",
            name="expires_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
