"""
Face Recognition Login System - Models
=======================================
Faqat login uchun kerakli modellar.
"""

from django.db import models


class Person(models.Model):
    """
    Shaxs modeli - V1 inspectors jadvaliga ulangan
    """

    # === Primary Key (V1 dan) ===
    id = models.CharField(
        max_length=36,
        primary_key=True,
        verbose_name="ID",
        help_text="UUID format (v1 dan)"
    )

    # === Asosiy ma'lumotlar ===
    first_name = models.CharField(
        max_length=255,
        db_column='first_name_lat',
        verbose_name="Ism",
        help_text="Shaxsning ismi (Lotin alifbosida)"
    )

    last_name = models.CharField(
        max_length=255,
        db_column='last_name_lat',
        verbose_name="Familiya",
        help_text="Shaxsning familiyasi (Lotin alifbosida)"
    )

    middle_name = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        db_column='patronym_lat',
        verbose_name="Sharif",
        help_text="Otasining ismi (Lotin alifbosida)"
    )

    # === Passport ma'lumotlari (Login uchun) ===
    # V1 da birlashgan passport field bor: AB1234567
    passport = models.CharField(
        max_length=255,
        unique=True,
        db_column='passport',
        verbose_name="Passport",
        help_text="To'liq passport: AB1234567"
    )

    birth_date = models.DateField(
        db_column='birth_date',
        verbose_name="Tug'ilgan kun",
        help_text="Masalan: 1990-01-15"
    )

    pinfl = models.CharField(
        max_length=14,
        unique=True,
        db_column='pinfl',
        verbose_name="PINFL (JShIR)",
        help_text="14 raqamli PINFL/JShIR kod"
    )

    # === Ish ma'lumotlari ===
    position = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        db_column='position',
        verbose_name="Lavozim",
        help_text="Masalan: Inspektor, Boshliq va hokazo"
    )

    tuman = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        db_column='tuman',
        verbose_name="Biriktirilgan tuman",
        help_text="Qaysi tumanga biriktirilgan"
    )

    department = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        db_column='department',
        verbose_name="Bo'lim",
        help_text="Qaysi bo'limda ishlaydi"
    )

    phone = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        db_column='phone',
        verbose_name="Telefon raqami",
        help_text="Masalan: +998901234567"
    )

    mahalla = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        db_column='mahalla',
        verbose_name="Mahalla",
        help_text="Qaysi mahallada istiqomat qiladi"
    )

    badge_number = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        db_column='badge_number',
        verbose_name="Jeton raqami",
        help_text="Xizmat jetoni raqami (masalan: A-121000)"
    )

    special_rank = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        db_column='special_rank',
        verbose_name="Maxsus unvon",
        help_text="Masalan: serjant, leytenant"
    )

    # === Rasm (Yuz tanish uchun) - V2 dan qo'shilgan ===
    photo = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        db_column='photo',
        verbose_name='Rasm',
        help_text="Yuz rasmi path (faces/)"
    )

    # === Yuz encodingi (Face recognition uchun) - V2 dan qo'shilgan ===
    face_encoding = models.JSONField(
        null=True,
        blank=True,
        db_column='face_encoding',
        verbose_name='Yuz kodlash',
        help_text="Face recognition uchun 128 o'lchamli vektor"
    )

    # === Ro'yxatdan o'tgan vaqt - V2 dan qo'shilgan ===
    registered_at = models.DateTimeField(
        null=True,
        blank=True,
        db_column='registered_at',
        verbose_name="Ro'yxatdan o'tgan vaqt",
    )

    # === V1 fields ===
    external_person_id = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        db_column='external_person_id',
        verbose_name="Tashqi API ID",
        help_text="Person API dagi ID"
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        db_column='created_at',
        verbose_name="Yaratilgan vaqt"
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        db_column='updated_at',
        verbose_name="O'zgartirilgan vaqt"
    )

    class Meta:
        db_table = 'inspectors'  # V1 jadvaliga ulash
        managed = False  # Django migrations bilan boshqarilmaydi
        ordering = ['last_name', 'first_name']
        verbose_name = 'Inspector'
        verbose_name_plural = 'Inspectors'


    @property
    def full_name(self) -> str:
        """To'liq ism-familiya-sharif"""
        parts = [self.last_name, self.first_name]
        if self.middle_name:
            parts.append(self.middle_name)
        return " ".join(filter(None, parts)).strip()

    @property
    def passport_series(self) -> str:
        """Passport seriyasini ajratib olish (backward compatibility)"""
        if self.passport and len(self.passport) >= 2:
            # AB1234567 -> AB
            return self.passport[:2]
        return ""

    @property
    def passport_number(self) -> str:
        """Passport raqamini ajratib olish (backward compatibility)"""
        if self.passport and len(self.passport) > 2:
            # AB1234567 -> 1234567
            return self.passport[2:]
        return ""

    @property
    def phone_number(self):
        """Telefon raqami (backward compatibility)"""
        return self.phone

    @property
    def district(self):
        """Tuman (backward compatibility)"""
        return self.tuman

    @property
    def jeton_series(self):
        """Jeton seriyasi (backward compatibility)"""
        return self.badge_number

    def save(self, *args, **kwargs):
        """
        Person saqlanganda avtomatik Django User yaratish/yangilash
        V1 database bilan ishlaydi
        """
        # ID yaratish (agar yangi bo'lsa)
        if not self.id:
            import uuid
            self.id = str(uuid.uuid4())

        # Avval Person'ni saqlash
        super().save(*args, **kwargs)

        # Django User yaratish/yangilash
        try:
            from django.contrib.auth.models import User

            # USERNAME: passport (to'liq)
            username = self.passport if self.passport else f"person_{self.id}"

            # PASSWORD: birth_date (DDMMYYYY)
            password = 'password123'  # Default
            if self.birth_date:
                try:
                    from datetime import date
                    if isinstance(self.birth_date, date):
                        password = str(self.birth_date.strftime('%d%m%Y'))
                    else:
                        password = 'password123'
                except Exception:
                    password = 'password123'

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
            print(f"Django User yaratishda xatolik (Inspector {self.id}): {e}")

    def __str__(self) -> str:
        return self.full_name


class LoginLog(models.Model):
    """
    Login loglarini saqlash - V1 login_logs jadvaliga ulangan
    """

    LOGIN_METHOD_CHOICES = [
        ('FACE', 'Yuz orqali'),
        ('PASSPORT', 'Passport orqali'),
    ]

    # === Primary Key (V1 dan) ===
    id = models.CharField(
        max_length=36,
        primary_key=True,
        verbose_name="ID",
        help_text="UUID format (v1 dan)"
    )

    # === Inspector relation ===
    inspector = models.ForeignKey(
        Person,
        on_delete=models.CASCADE,
        related_name='login_logs',
        db_column='inspector_id',
        verbose_name='Inspector'
    )

    login_method = models.CharField(
        max_length=20,
        choices=LOGIN_METHOD_CHOICES,
        db_column='login_method',
        verbose_name='Login usuli'
    )

    # === Login vaqti ===
    login_time = models.DateTimeField(
        auto_now_add=True,
        db_column='login_time',
        verbose_name='Kirish vaqti'
    )

    # === Rasm (login vaqtida olingan) ===
    login_photo = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        db_column='login_photo',
        verbose_name='Login vaqtidagi rasm path'
    )

    # === Qo'shimcha ma'lumotlar ===
    ip_address = models.CharField(
        max_length=45,
        db_column='ip_address',
        verbose_name='IP manzil'
    )

    confidence = models.FloatField(
        null=True,
        blank=True,
        db_column='confidence',
        verbose_name='Ishonch darajasi (%)',
        help_text='Face recognition uchun ishonch darajasi'
    )

    success = models.BooleanField(
        default=True,
        db_column='success',
        verbose_name='Muvaffaqiyatli'
    )

    class Meta:
        db_table = 'login_logs'  # V1 jadvaliga ulash
        managed = False  # Django migrations bilan boshqarilmaydi
        ordering = ['-login_time']
        verbose_name = 'Login Log'
        verbose_name_plural = 'Login Loglari'

    @property
    def person(self):
        """Backward compatibility: person -> inspector"""
        return self.inspector

    def save(self, *args, **kwargs):
        """ID yaratish"""
        if not self.id:
            import uuid
            self.id = str(uuid.uuid4())
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.inspector.full_name} - {self.login_time.strftime('%Y-%m-%d %H:%M:%S')}"
