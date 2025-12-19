#!/usr/bin/env python
"""
Barcha Person'lar uchun Django User yaratish yoki yangilash
Username: passport_series + passport_number
Password: birth_date (DDMMYYYY)
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from emotion_app.models import Person
from django.contrib.auth.models import User

def update_all_users():
    """Barcha Person'lar uchun Django User yaratish/yangilash"""

    print("=" * 70)
    print("DJANGO USERS YARATISH/YANGILASH")
    print("=" * 70)

    persons = Person.objects.all()
    total = persons.count()

    print(f"\n📊 Jami Person'lar: {total}")

    created_count = 0
    updated_count = 0
    error_count = 0

    for i, person in enumerate(persons, 1):
        try:
            print(f"\n[{i}/{total}] {person.full_name}...")

            # USERNAME: passport_series + passport_number
            if person.passport_series and person.passport_number:
                username = f"{person.passport_series}{person.passport_number}"
            else:
                username = f"person_{person.id}"
                print(f"   ⚠️  Passport yo'q, fallback username: {username}")

            # PASSWORD: birth_date (DDMMYYYY)
            if person.birth_date:
                password = person.birth_date.strftime('%d%m%Y')
            else:
                password = 'password123'
                print(f"   ⚠️  Tug'ilgan kun yo'q, default password: {password}")

            # User yaratish yoki yangilash
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    'first_name': person.first_name,
                    'last_name': person.last_name,
                    'is_staff': True,
                    'is_superuser': True,
                    'is_active': True,
                }
            )

            if created:
                user.set_password(password)
                user.save()
                created_count += 1
                print(f"   ✅ Yaratildi: {username} / {password}")
            else:
                # Mavjud user'ni yangilash
                user.first_name = person.first_name
                user.last_name = person.last_name
                user.set_password(password)
                user.is_staff = True
                user.is_superuser = True
                user.is_active = True
                user.save()
                updated_count += 1
                print(f"   🔄 Yangilandi: {username} / {password}")

        except Exception as e:
            error_count += 1
            print(f"   ❌ Xatolik: {str(e)}")

    # Natija
    print("\n" + "=" * 70)
    print("NATIJALAR:")
    print("=" * 70)
    print(f"   Jami Person: {total}")
    print(f"   ✅ Yaratildi: {created_count}")
    print(f"   🔄 Yangilandi: {updated_count}")
    print(f"   ❌ Xatoliklar: {error_count}")
    print(f"\n   📊 Jami Django User: {User.objects.count()}")
    print("=" * 70)

if __name__ == "__main__":
    update_all_users()
