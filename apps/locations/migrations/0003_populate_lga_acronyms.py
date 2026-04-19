# Data migration to populate LGA acronyms

from django.db import migrations


def populate_acronyms(apps, schema_editor):
    """Populate acronym field for existing LGAs"""
    LGA = apps.get_model('locations', 'LGA')
    
    acronyms_map = {
        'Aba North': 'ABN',
        'Aba South': 'ABS',
        'Arochukwu': 'ARO',
        'Bende': 'BEN',
        'Ikwuano': 'IKW',
        'Isiala Ngwa North': 'ISN',
        'Isiala Ngwa South': 'ISS',
        'Isuikwuato': 'ISU',
        'Obingwu': 'OBI',
        'Ohafia': 'OHA',
        'Osisioma': 'OSI',
        'Ugwunagbo': 'UGW',
        'Umuahia North': 'UMN',
        'Ukwa East': 'UKE',
        'Ukwa West': 'UKW',
        'Umuahia South': 'UMS',
        'Umunneochi': 'UNE',
    }
    
    for lga in LGA.objects.all():
        # Try to find matching acronym, otherwise use first 3 letters
        lga.acronym = acronyms_map.get(lga.name, lga.name[:3].upper())
        lga.save()


def reverse_acronyms(apps, schema_editor):
    """Reverse function - clear acronyms"""
    LGA = apps.get_model('locations', 'LGA')
    for lga in LGA.objects.all():
        lga.acronym = ''
        lga.save()


class Migration(migrations.Migration):

    dependencies = [
        ('locations', '0002_add_lga_acronym'),
    ]

    operations = [
        migrations.RunPython(populate_acronyms, reverse_acronyms),
    ]
