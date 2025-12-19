"""
Face Recognition Login System - Models
=======================================
Faqat login uchun kerakli modellar.
"""

from django.db import models


class Person(models.Model):
    """
    Shaxs modeli - Login va ma'lumotlar uchun
    """

    # === Asosiy ma'lumotlar ===
    first_name = models.CharField(
        max_length=100,
        verbose_name="Ism",
        db_index=True,
        help_text="Shaxsning ismi"
    )

    last_name = models.CharField(
        max_length=100,
        verbose_name="Familiya",
        db_index=True,
        help_text="Shaxsning familiyasi"
    )

    middle_name = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name="Sharif",
        help_text="Otasining ismi"
    )

    # === Passport ma'lumotlari (Login uchun) ===
    passport_series = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        verbose_name="Passport seriyasi",
        db_index=True,
        help_text="Masalan: AB"
    )

    passport_number = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        verbose_name="Passport raqami",
        help_text="Masalan: 1234567"
    )

    birth_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="Tug'ilgan kun",
        help_text="Masalan: 1990-01-15"
    )

    pinfl = models.CharField(
        max_length=14,
        null=True,
        blank=True,
        unique=True,
        verbose_name="PINFL (JShIR)",
        db_index=True,
        help_text="14 raqamli PINFL/JShIR kod"
    )

    # === Ish ma'lumotlari ===
    position = models.CharField(
        max_length=200,
        null=True,
        blank=True,
        verbose_name="Lavozim",
        help_text="Masalan: Inspektor, Boshliq va hokazo"
    )

    district = models.CharField(
        max_length=200,
        null=True,
        blank=True,
        verbose_name="Biriktirilgan tuman",
        help_text="Qaysi tumanga biriktirilgan"
    )

    department = models.CharField(
        max_length=200,
        null=True,
        blank=True,
        verbose_name="Bo'lim",
        help_text="Qaysi bo'limda ishlaydi"
    )

    phone_number = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name="Telefon raqami",
        help_text="Masalan: +998901234567"
    )

    mahalla = models.CharField(
        max_length=200,
        null=True,
        blank=True,
        verbose_name="Mahalla",
        help_text="Qaysi mahallada istiqomat qiladi"
    )

    jeton_series = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name="Jeton seriyasi",
        help_text="Xizmat jetoni seriyasi"
    )

    # === Rasm (Yuz tanish uchun) ===
    photo = models.ImageField(
        upload_to='faces/',
        null=True,
        blank=True,
        verbose_name='Rasm',
        help_text="Shaxsning yuz rasmi (face login uchun)"
    )

    # === Yuz encodingi (Face recognition uchun) ===
    face_encoding = models.JSONField(
        null=True,
        blank=True,
        verbose_name='Yuz kodlash',
        help_text="Face recognition uchun 128 o'lchamli vektor"
    )

    # === Ro'yxatdan o'tgan vaqt ===
    registered_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Ro'yxatdan o'tgan vaqt",
    )

    class Meta:
        ordering = ['last_name', 'first_name']
        verbose_name = 'Shaxs'
        verbose_name_plural = 'Shaxslar'
        indexes = [
            models.Index(fields=['last_name', 'first_name']),
            models.Index(fields=['passport_series']),
        ]


    @property
    def full_name(self) -> str:
        """To'liq ism-familiya-sharif"""
        parts = [self.last_name, self.first_name]
        if self.middle_name:
            parts.append(self.middle_name)
        return " ".join(filter(None, parts)).strip()

    def save(self, *args, **kwargs):
        """
        Person saqlanganda avtomatik Django User yaratish/yangilash
        """
        # Avval Person'ni saqlash (ID kerak bo'ladi)
        super().save(*args, **kwargs)

        # Django User yaratish/yangilash
        try:
            from django.contrib.auth.models import User

            # USERNAME: passport_series + passport_number
            if self.passport_series and self.passport_number:
                username = f"{self.passport_series}{self.passport_number}"
            else:
                # Fallback: person_ID
                username = f"person_{self.id}"

            # PASSWORD: birth_date (DDMMYYYY)
            password = 'password123'  # Default
            if self.birth_date:
                try:
                    # birth_date must be date object
                    from datetime import date
                    if isinstance(self.birth_date, date):
                        password = str(self.birth_date.strftime('%d%m%Y'))
                    else:
                        password = 'password123'
                except Exception:
                    password = 'password123'

            # Ensure password is string
            password = str(password) if password else 'password123'

            # User yaratish yoki yangilash
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    'first_name': self.first_name,
                    'last_name': self.last_name,
                    'is_staff': True,
                    'is_superuser': True,
                    'is_active': True,
                }
            )

            if not created:
                # Mavjud user'ni yangilash
                user.first_name = self.first_name
                user.last_name = self.last_name
                user.set_password(password)
                user.is_staff = True
                user.is_superuser = True
                user.is_active = True
                user.save()

            if created:
                user.set_password(password)
                user.save()

        except Exception as e:
            # Xatolik bo'lsa ham Person saqlangan bo'ladi
            print(f"Django User yaratishda xatolik (Person {self.id}): {e}")

    def __str__(self) -> str:
        return self.full_name


class LoginLog(models.Model):
    """
    Login loglarini saqlash - kimlar qachon kirgan
    """

    LOGIN_METHOD_CHOICES = [
        ('face', 'Yuz orqali'),
        ('passport', 'Passport orqali'),
    ]

    # === Asosiy ma'lumotlar ===
    person = models.ForeignKey(
        Person,
        on_delete=models.CASCADE,
        related_name='login_logs',
        verbose_name='Shaxs'
    )

    login_method = models.CharField(
        max_length=20,
        choices=LOGIN_METHOD_CHOICES,
        verbose_name='Login usuli'
    )

    # === Login vaqti ===
    login_time = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Kirish vaqti',
        db_index=True
    )

    # === Rasm (login vaqtida olingan) ===
    login_photo = models.ImageField(
        upload_to='login_photos/%Y/%m/%d/',
        null=True,
        blank=True,
        verbose_name='Login vaqtidagi rasm'
    )

    # === Qo'shimcha ma'lumotlar ===
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        verbose_name='IP manzil'
    )

    confidence = models.FloatField(
        null=True,
        blank=True,
        verbose_name='Ishonch darajasi (%)',
        help_text='Face recognition uchun ishonch darajasi'
    )

    success = models.BooleanField(
        default=True,
        verbose_name='Muvaffaqiyatli'
    )

    class Meta:
        ordering = ['-login_time']
        verbose_name = 'Login Log'
        verbose_name_plural = 'Login Loglari'
        indexes = [
            models.Index(fields=['-login_time']),
            models.Index(fields=['person', '-login_time']),
        ]

    def __str__(self) -> str:
        return f"{self.person.full_name} - {self.login_time.strftime('%Y-%m-%d %H:%M:%S')}"
