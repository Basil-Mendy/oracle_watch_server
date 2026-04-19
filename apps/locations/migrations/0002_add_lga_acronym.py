# Generated migration

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('locations', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='lga',
            name='acronym',
            field=models.CharField(blank=True, default='', max_length=10),
            preserve_default=True,
        ),
    ]
