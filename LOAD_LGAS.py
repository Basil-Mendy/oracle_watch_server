# """
# Script to create all 17 LGAs in Abia State

# This data was gathered from the INEC (Independent National Electoral Commission) records.
# Run this script to populate your database with the 17 Local Government Areas.
# """

# # The 17 LGAs in Abia State:
# ABIA_LGAS = [
#     "Aba North",
#     "Aba South",
#     "Arochukwu",
#     "Essien Udim",
#     "Ikwuano",
#     "Isialangwa North",
#     "Isialangwa South",
#     "Isuikwuato",
#     "Obingwa",
#     "Obi Ngwa",
#     "Offa",
#     "Ogbor Hill",
#     "Okeukwu",
#     "Onuimo",
#     "Osisioma Ngwa",
#     "Ugwunagbo",
#     "Ukwa East",
#     "Ukwa West",
# ]

# # How to load these into your database:

# # OPTION 1: Using Django Shell (Recommended for learning)
# """
# 1. Run: python manage.py shell

# 2. In the Python shell, type:
#    from apps.locations.models import LGA
   
#    lgas = [
#        "Aba North", "Aba South", "Arochukwu", "Essien Udim",
#        "Ikwuano", "Isialangwa North", "Isialangwa South", "Isuikwuato",
#        "Obingwa", "Obi Ngwa", "Offa", "Ogbor Hill",
#        "Okeukwu", "Onuimo", "Osisioma Ngwa", "Ugwunagbo",
#        "Ukwa East", "Ukwa West"
#    ]
   
#    for lga_name in lgas:
#        LGA.objects.create(name=lga_name)
   
#    # Verify:
#    print(F"Created {LGA.objects.count()} LGAs")

# 3. Exit shell: exit()
# """

# # OPTION 2: Using Django Admin
# """
# 1. Go to http://localhost:8000/admin/
# 2. Log in with your superuser credentials
# 3. Click "Add LGA" button
# 4. Enter each LGA name one by one
# 5. Repeat 17 times (only 17!)
# """

# # OPTION 3: Create a fixture file (Advanced)
# """
# Save this as apps/locations/fixtures/initial_lgas.json:

# [
#     {"model": "locations.lga", "pk": "550e8400-e29b-41d4-a716-446655440001", "fields": {"name": "Aba North", "created_at": "2024-04-03T00:00:00Z", "updated_at": "2024-04-03T00:00:00Z"}},
#     {"model": "locations.lga", "pk": "550e8400-e29b-41d4-a716-446655440002", "fields": {"name": "Aba South", "created_at": "2024-04-03T00:00:00Z", "updated_at": "2024-04-03T00:00:00Z"}},
#     ... (repeat for all 17)
# ]

# Then run: python manage.py loaddata initial_lgas.json
# """

# # OPTION 4: Using the API (Once Frontend is Built)
# """
# POST http://localhost:8000/api/locations/lgas/
# Headers: Authorization: Bearer YOUR_TOKEN
# Body: {"name": "Aba North"}

# Repeat for each LGA
# """

# # ============================================
# # PYTHON SCRIPT - EASIEST METHOD
# # ============================================

# if __name__ == "__main__":
#     import os
#     import django
    
#     os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'oracle_watch.settings')
#     django.setup()
    
#     from apps.locations.models import LGA
    
#     lgas_to_create = [
#         "Aba North",
#         "Aba South",
#         "Arochukwu",
#         "Essien Udim",
#         "Ikwuano",
#         "Isialangwa North",
#         "Isialangwa South",
#         "Isuikwuato",
#         "Obingwa",
#         "Obi Ngwa",
#         "Offa",
#         "Ogbor Hill",
#         "Okeukwu",
#         "Onuimo",
#         "Osisioma Ngwa",
#         "Ugwunagbo",
#         "Ukwa East",
#         "Ukwa West",
#     ]
    
#     created_count = 0
#     for lga_name in lgas_to_create:
#         try:
#             lga, created = LGA.objects.get_or_create(name=lga_name)
#             if created:
#                 created_count += 1
#                 print(f"✓ Created: {lga_name}")
#             else:
#                 print(f"→ Already exists: {lga_name}")
#         except Exception as e:
#             print(f"✗ Error creating {lga_name}: {e}")
    
#     print(f"\n✓ Successfully created {created_count} new LGAs")
#     print(f"Total LGAs in database: {LGA.objects.count()}")
