# Generated migration to add plaintext_password field

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('locations', '0003_populate_lga_acronyms'),
    ]

    operations = [
        migrations.AddField(
            model_name='pollingunit',
            name='plaintext_password',
            field=models.CharField(blank=True, max_length=20, null=True, help_text='Store plaintext password for printing/display purposes'),
        ),
    ]
