#!/usr/bin/env python
"""
Database tozalash scripti - barcha Person va LoginLog ma'lumotlarini o'chirish
"""
import os
import django

# Django setup
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from emotion_app.models import Person, LoginLog

def clear_database():
    """Barcha Person va LoginLog ma'lumotlarini o'chirish"""

    print("=" * 60)
    print("DATABASE TOZALASH - BARCHA MA'LUMOTLAR O'CHIRILADI!")
    print("=" * 60)

    # Hozirgi holatni ko'rsatish
    person_count = Person.objects.count()
    loginlog_count = LoginLog.objects.count()

    print(f"\n📊 Hozirgi holat:")
    print(f"   - Person: {person_count} ta")
    print(f"   - LoginLog: {loginlog_count} ta")

    if person_count == 0 and loginlog_count == 0:
        print("\n✅ Database allaqachon bo'sh!")
        return

    # Tasdiqlash
    print(f"\n⚠️  DIQQAT: {person_count} ta Person va {loginlog_count} ta LoginLog o'chiriladi!")
    confirm = input("\nDavom etishni xohlaysizmi? (ha/yo'q): ").strip().lower()

    if confirm not in ['ha', 'yes', 'y']:
        print("❌ Bekor qilindi.")
        return

    print("\n🗑️  O'chirish boshlandi...\n")

    # LoginLog'larni o'chirish (ForeignKey bo'lgani uchun birinchi)
    if loginlog_count > 0:
        print(f"   🔸 LoginLog'lar o'chirilmoqda... ({loginlog_count} ta)")
        deleted_logs = LoginLog.objects.all().delete()
        print(f"   ✅ {deleted_logs[0]} ta LoginLog o'chirildi")

    # Person'larni o'chirish
    if person_count > 0:
        print(f"   🔸 Person'lar o'chirilmoqda... ({person_count} ta)")
        deleted_persons = Person.objects.all().delete()
        print(f"   ✅ {deleted_persons[0]} ta Person o'chirildi")

    # Natija
    print("\n" + "=" * 60)
    print("✅ DATABASE MUVAFFAQIYATLI TOZALANDI!")
    print("=" * 60)
    print(f"\nO'chirilgan ma'lumotlar:")
    print(f"   - Person: {person_count} ta")
    print(f"   - LoginLog: {loginlog_count} ta")
    print("\n📝 Endi Excel'dan qayta yuklashingiz mumkin.\n")

if __name__ == "__main__":
    clear_database()
