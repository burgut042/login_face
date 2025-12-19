"""
Management command:
Person maʼlumotlari asosida Django User (admin) account yaratish

LOGIN  -> PASSPORT_SERIYA + PASSPORT_RA QAMI
PAROL  -> TUG‘ILGAN SANA (YYYYMMDD)
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from emotion_app.models import Person


class Command(BaseCommand):
    help = "Person jadvalidagi maʼlumotlardan admin User yaratadi"

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING(
            "\n🚀 Person lar uchun User account yaratish boshlandi...\n"
        ))

        persons = Person.objects.all()
        total = persons.count()

        created = 0
        updated = 0
        skipped = 0

        self.stdout.write(f"📊 Jami Person: {total}\n")

        for person in persons:
            full_name = getattr(person, "full_name", f"{person.first_name}{person.last_name}")

            # =============================
            # PASSPORT TEKSHIRISH
            # =============================
            if not person.passport_series or not person.passport_number:
                skipped += 1
                self.stdout.write(
                    self.style.WARNING(
                        f"⏭️ Passport yo‘q → {full_name}"
                    )
                )
                continue

            username = f"{person.passport_series}{person.passport_number}"

            # =============================
            # TUG‘ILGAN SANA TEKSHIRISH
            # =============================
            if not person.birth_date:
                skipped += 1
                self.stdout.write(
                    self.style.WARNING(
                        f"⏭️ Tug‘ilgan sana yo‘q → {full_name}"
                    )
                )
                continue

            password = person.birth_date.strftime("%Y%m%d")

            try:
                user, is_created = User.objects.get_or_create(
                    username=username,
                    defaults={
                        "first_name": person.first_name,
                        "last_name": person.last_name,
                        "is_staff": True,
                        "is_superuser": True,
                        "is_active": True,
                    }
                )

                # =============================
                # YANGI USER
                # =============================
                if is_created:
                    user.set_password(password)
                    user.save()

                    created += 1
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"✅ YARATILDI → {full_name} | "
                            f"login: {username} | parol: {password}"
                        )
                    )

                # =============================
                # MAVJUD USER
                # =============================
                else:
                    need_update = False

                    if not user.is_staff:
                        user.is_staff = True
                        need_update = True

                    if not user.is_superuser:
                        user.is_superuser = True
                        need_update = True

                    if not user.is_active:
                        user.is_active = True
                        need_update = True

                    if user.first_name != person.first_name:
                        user.first_name = person.first_name
                        need_update = True

                    if user.last_name != person.last_name:
                        user.last_name = person.last_name
                        need_update = True

                    if need_update:
                        user.set_password(password)
                        user.save()
                        updated += 1

                        self.stdout.write(
                            self.style.WARNING(
                                f"🔄 YANGILANDI → {full_name} | "
                                f"login: {username} | parol: {password}"
                            )
                        )
                    else:
                        skipped += 1
                        self.stdout.write(
                            f"⏭️ MAVJUD → {full_name}"
                        )

            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(
                        f"❌ XATOLIK → {full_name} | {e}"
                    )
                )

        # =============================
        # YAKUNIY HISOBOT
        # =============================
        self.stdout.write(self.style.SUCCESS("\n" + "=" * 60))
        self.stdout.write(self.style.SUCCESS("✅ BUYRUQ MUVAFFAQIYATLI YAKUNLANDI"))
        self.stdout.write(self.style.SUCCESS("=" * 60))
        self.stdout.write(f"📊 Jami Person        : {total}")
        self.stdout.write(self.style.SUCCESS(f"✅ Yaratildi         : {created}"))
        self.stdout.write(self.style.WARNING(f"🔄 Yangilandi        : {updated}"))
        self.stdout.write(f"⏭️ O‘tkazib yuborildi : {skipped}")
        self.stdout.write("\n🔐 LOGIN  : PASSPORT_SERIYA + RAQAM")
        self.stdout.write("🔐 PAROL  : TUG‘ILGAN SANA (YYYYMMDD)\n")
