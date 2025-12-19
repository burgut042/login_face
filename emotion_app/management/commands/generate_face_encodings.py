"""
Management command to generate face encodings for all persons with photos
"""
from django.core.management.base import BaseCommand
from emotion_app.models import Person
import face_recognition


class Command(BaseCommand):
    help = 'Barcha rasmli Person yozuvlari uchun face encoding yaratish'

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('\nFace encoding yaratilmoqda...\n'))

        # Rasmli lekin face_encoding'i bo'lmagan Person'larni topish
        persons = Person.objects.exclude(photo='').exclude(photo=None)
        total = persons.count()

        self.stdout.write(f"Jami rasmli Person: {total}\n")

        generated_count = 0
        skipped_count = 0
        error_count = 0

        for person in persons:
            # Agar face_encoding allaqachon bo'lsa, o'tkazib yuborish
            if person.face_encoding:
                skipped_count += 1
                continue

            try:
                # Face encoding yaratish
                image = face_recognition.load_image_file(person.photo.path)
                encodings = face_recognition.face_encodings(image)

                if encodings:
                    person.face_encoding = encodings[0].tolist()
                    person.save()
                    generated_count += 1
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"  ✅ {person.full_name} (ID: {person.id})"
                        )
                    )
                else:
                    error_count += 1
                    self.stdout.write(
                        self.style.WARNING(
                            f"  ⚠️  Yuz topilmadi: {person.full_name} (ID: {person.id})"
                        )
                    )
            except Exception as e:
                error_count += 1
                self.stdout.write(
                    self.style.ERROR(
                        f"  ❌ Xatolik ({person.full_name}): {str(e)[:100]}"
                    )
                )

        self.stdout.write(self.style.SUCCESS(f"\n{'='*60}"))
        self.stdout.write(self.style.SUCCESS(f"✅ Yakunlandi!"))
        self.stdout.write(self.style.SUCCESS(f"{'='*60}"))
        self.stdout.write(f"📊 Jami: {total}")
        self.stdout.write(self.style.SUCCESS(f"✅ Yaratildi: {generated_count}"))
        self.stdout.write(f"⏭️  O'tkazib yuborildi (allaqachon mavjud): {skipped_count}")
        self.stdout.write(self.style.ERROR(f"❌ Xatolar: {error_count}\n"))
