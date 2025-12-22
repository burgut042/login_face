"""
Admin Panel - Login System with Import/Export
"""
from django.contrib import admin
from django.utils.html import format_html
from import_export import resources, fields
from import_export.admin import ImportExportModelAdmin
from import_export.widgets import ForeignKeyWidget
from .models import Person, LoginLog
import base64
from django.core.files.base import ContentFile


class LoginLogInline(admin.TabularInline):
    """Person sahifasida login loglarini ko'rsatish"""
    model = LoginLog
    extra = 0
    readonly_fields = ['login_time', 'login_method', 'login_photo_preview', 'ip_address', 'confidence']
    fields = ['login_time', 'login_method', 'login_photo_preview', 'confidence', 'ip_address'] 
    can_delete = False
    max_num = 10  # Oxirgi 10 ta logni ko'rsatish

    def login_photo_preview(self, obj):
        if obj.login_photo:
            return format_html('<img src="{}" width="100" height="100" style="object-fit: cover; border-radius: 5px;" />', obj.login_photo.url)
        return "Rasm yo'q"
    login_photo_preview.short_description = 'Rasm'

    def has_add_permission(self, request, obj=None):
        return False


# =====================================================
# Person Resource - Import/Export uchun
# =====================================================
class PersonResource(resources.ModelResource):
    """Person modelini import/export qilish uchun"""

    # Rasm maydonini qo'shimcha qilish (Base64 format)
    photo_base64 = fields.Field(column_name='photo_base64')

    class Meta:
        model = Person
        fields = (
            'id',
            'first_name',
            'last_name',
            'middle_name',
            'passport_series',
            'passport_number',
            'birth_date',
            'pinfl',
            'position',
            'district',
            'department',
            'phone_number',
            'mahalla',
            'jeton_series',
            'photo_base64',
            'registered_at',
        )
        export_order = fields
        # MUHIM: Passport seriya VA raqam bo'yicha yangilash
        import_id_fields = ['passport_series', 'passport_number']
        skip_unchanged = True
        report_skipped = True
        use_bulk = False  # Har bir Person uchun save() chaqiriladi (User yaratish uchun)

    def dehydrate_photo_base64(self, person):
        """Export: Rasmni base64 formatga o'tkazish"""
        if person.photo:
            try:
                with person.photo.open('rb') as f:
                    return base64.b64encode(f.read()).decode('utf-8')
            except:
                return ''
        return ''

    def before_import_row(self, row, **kwargs):
        """Import: Rasmni base64 dan qayta tiklash"""
        photo_b64 = row.get('photo_base64', '')
        if photo_b64:
            try:
                # Base64 ni decode qilish
                image_data = base64.b64decode(photo_b64)
                row['_photo_data'] = image_data
            except:
                pass

    def after_import_instance(self, instance, new, **kwargs):
        """Import: Rasmni saqlash"""
        if hasattr(kwargs.get('row', {}), '__getitem__'):
            row = kwargs['row']
            if '_photo_data' in row:
                try:
                    from PIL import Image
                    import io

                    # Rasm formatini aniqlash
                    img_bytes = row['_photo_data']
                    img = Image.open(io.BytesIO(img_bytes))
                    original_format = img.format if img.format else 'JPEG'

                    # Ruxsat etilgan formatlar
                    allowed_formats = ['JPEG', 'JPG', 'PNG', 'WEBP', 'GIF']

                    if original_format.upper() not in allowed_formats:
                        original_format = 'JPEG'

                    # File extension aniqlash
                    format_ext_map = {
                        'JPEG': 'jpg',
                        'JPG': 'jpg',
                        'PNG': 'png',
                        'WEBP': 'webp',
                        'GIF': 'gif'
                    }
                    file_ext = format_ext_map.get(original_format.upper(), 'jpg')

                    filename = f"{instance.passport_series or instance.id}.{file_ext}"
                    instance.photo.save(filename, ContentFile(img_bytes), save=False)
                except Exception as e:
                    print(f"Rasm saqlashda xatolik: {e}")
                    pass

    def skip_row(self, instance, original, row, import_validation_errors=None):
        """
        Qatorni o'tkazib yuborish kerakmi?
        Agar ism yoki familiya bo'lmasa - skip
        """
        if not instance.first_name or not instance.last_name:
            return True
        return super().skip_row(instance, original, row, import_validation_errors)

    def before_save_instance(self, instance, row, **kwargs):
        """
        Saqlashdan oldin ma'lumotlarni tekshirish
        """
        # Ism va familiyani trim qilish
        if instance.first_name:
            instance.first_name = instance.first_name.strip()
        if instance.last_name:
            instance.last_name = instance.last_name.strip()
        if instance.passport_series:
            instance.passport_series = instance.passport_series.upper().strip()
        if instance.passport_number:
            instance.passport_number = instance.passport_number.strip()


@admin.register(Person)
class PersonAdmin(ImportExportModelAdmin):
    """Person Admin with Import/Export"""
    resource_class = PersonResource

    # MUHIM: Bir sahifada ko'rsatiladigan ma'lumotlar soni
    list_per_page = 500  # 500 tagacha ma'lumot bir sahifada ko'rsatiladi
    list_max_show_all = 1000  # "Barchasini ko'rsatish" tugmasi uchun maksimal limit

    list_display = [
        'id',
        'photo_thumbnail',
        'full_name',
        'passport_series',
        'passport_number',
        'birth_date',
        'position',
        'district',
        'department',
        'phone_number',
        'has_photo',
        'login_count',
        'last_login_time',
        'registered_at',
    ]

    # Qaysi ustunlar bo'yicha saralash mumkin
    sortable_by = [
        'id',
        'first_name',
        'last_name',
        'passport_series',
        'passport_number',
        'birth_date',
        'position',
        'district',
        'department',
        'registered_at',
    ]

    # Default saralash - ID bo'yicha
    ordering = ['id']

    list_filter = [
        'registered_at',
        'position',
        'district',
        'department',
        'passport_series',  # Passport seriya bo'yicha filter
    ]

    search_fields = [
        'first_name',
        'last_name',
        'middle_name',
        'passport_series',
        'pinfl',
        'position',
        'district',
        'phone_number',
    ]

    readonly_fields = [
        'registered_at',
        'face_encoding',
        'photo_preview',
        'login_statistics',
    ]

    fieldsets = (
        ('Asosiy Ma\'lumotlar', {
            'fields': ('first_name', 'last_name', 'middle_name')
        }),
        ('Login Ma\'lumotlari', {
            'fields': ('passport_series', 'passport_number', 'birth_date', 'pinfl')
        }),
        ('Ish Ma\'lumotlari', {
            'fields': ('position', 'district', 'department', 'phone_number', 'mahalla', 'jeton_series')
        }),
        ('Yuz Tanish', {
            'fields': ('photo', 'photo_preview', 'face_encoding')
        }),
        ('Vaqt', {
            'fields': ('registered_at',)
        }),
        ('Statistika', {
            'fields': ('login_statistics',),
            'classes': ('collapse',)
        }),
    )

    inlines = [LoginLogInline]

    def full_name(self, obj):
        return obj.full_name
    full_name.short_description = 'To\'liq ism'

    def photo_thumbnail(self, obj):
        """Ro'yxatda kichik rasm ko'rsatish"""
        if obj.photo:
            return format_html(
                '<img src="{}" width="50" height="50" style="object-fit: cover; border-radius: 5px; border: 1px solid #ddd;" />',
                obj.photo.url
            )
        return format_html('<span style="color: gray; font-size: 12px;">❌</span>')
    photo_thumbnail.short_description = '📷'

    def has_photo(self, obj):
        if obj.photo:
            return format_html('<span style="color: green; font-size: 18px;">✅</span>')
        return format_html('<span style="color: gray; font-size: 18px;">❌</span>')
    has_photo.short_description = 'Rasm'

    def photo_preview(self, obj):
        if obj.photo:
            return format_html(
                '<img src="{}" width="150" height="150" style="object-fit: cover; border-radius: 10px; border: 2px solid #ddd;" />',
                obj.photo.url
            )
        return "Rasm yuklanmagan"
    photo_preview.short_description = 'Rasm ko\'rinishi'

    def login_count(self, obj):
        count = obj.login_logs.count()
        if count > 0:
            return format_html('<strong style="color: green;">{}</strong>', count)
        return format_html('<span style="color: gray;">0</span>')
    login_count.short_description = 'Login soni'

    def last_login_time(self, obj):
        last_log = obj.login_logs.first()
        if last_log:
            return last_log.login_time.strftime('%Y-%m-%d %H:%M')
        return '-'
    last_login_time.short_description = 'Oxirgi kirish'

    def login_statistics(self, obj):
        """Login statistikasini ko'rsatish"""
        total = obj.login_logs.count()
        face_count = obj.login_logs.filter(login_method='face').count()
        passport_count = obj.login_logs.filter(login_method='passport').count()

        last_10 = obj.login_logs.all()[:10]

        html = f"""
        <div style="background: #f8f9fa; padding: 20px; border-radius: 10px;">
            <h3 style="margin-top: 0;">📊 Login Statistikasi</h3>
            <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 15px; margin-bottom: 20px;">
                <div style="background: white; padding: 15px; border-radius: 8px; text-align: center; border: 2px solid #007bff;">
                    <div style="font-size: 32px; font-weight: bold; color: #007bff;">{total}</div>
                    <div style="color: #666; margin-top: 5px;">Jami login</div>
                </div>
                <div style="background: white; padding: 15px; border-radius: 8px; text-align: center; border: 2px solid #28a745;">
                    <div style="font-size: 32px; font-weight: bold; color: #28a745;">{face_count}</div>
                    <div style="color: #666; margin-top: 5px;">Yuz orqali</div>
                </div>
                <div style="background: white; padding: 15px; border-radius: 8px; text-align: center; border: 2px solid #ffc107;">
                    <div style="font-size: 32px; font-weight: bold; color: #ffc107;">{passport_count}</div>
                    <div style="color: #666; margin-top: 5px;">Passport orqali</div>
                </div>
            </div>
        """

        if last_10:
            html += "<h4>Oxirgi loginlar:</h4><table style='width: 100%; border-collapse: collapse;'>"
            html += "<tr style='background: #e9ecef;'><th style='padding: 10px; text-align: left;'>Vaqt</th><th style='padding: 10px; text-align: left;'>Usul</th><th style='padding: 10px; text-align: left;'>IP</th></tr>"
            for log in last_10:
                method_color = '#28a745' if log.login_method == 'face' else '#ffc107'
                method_text = 'Yuz' if log.login_method == 'face' else 'Passport'
                html += f"<tr style='border-bottom: 1px solid #dee2e6;'>"
                html += f"<td style='padding: 10px;'>{log.login_time.strftime('%Y-%m-%d %H:%M:%S')}</td>"
                html += f"<td style='padding: 10px;'><span style='background: {method_color}; color: white; padding: 3px 10px; border-radius: 5px; font-size: 12px;'>{method_text}</span></td>"
                html += f"<td style='padding: 10px;'>{log.ip_address or '-'}</td>"
                html += "</tr>"
            html += "</table>"

        html += "</div>"
        return format_html(html)
    login_statistics.short_description = 'Login Statistikasi'

    # Permissions - to'liq ruxsat berish
    def has_add_permission(self, request):
        """Qo'shish ruxsati"""
        return True

    def has_change_permission(self, request, obj=None):
        """O'zgartirish ruxsati"""
        return True

    def has_delete_permission(self, request, obj=None):
        """O'chirish ruxsati - faqat staff uchun"""
        return request.user.is_staff

    def has_view_permission(self, request, obj=None):
        """Ko'rish ruxsati"""
        return True

    # Actions - bulk operatsiyalar
    actions = ['delete_selected']  # O'chirish action'ni yoqish


@admin.register(LoginLog)
class LoginLogAdmin(admin.ModelAdmin):
    """LoginLog Admin"""

    # MUHIM: Bir sahifada ko'rsatiladigan ma'lumotlar soni
    list_per_page = 500  # 500 tagacha ma'lumot bir sahifada ko'rsatiladi
    list_max_show_all = 1000  # "Barchasini ko'rsatish" tugmasi uchun maksimal limit

    list_display = [
        'id',
        'person',
        'login_method',
        'login_time',
        'ip_address',
        'confidence',
        'success',
        'has_photo',
    ]

    list_filter = [
        'login_method',
        'success',
        'login_time',
    ]

    search_fields = [
        'person__first_name',
        'person__last_name',
        'person__passport_series',
        'ip_address',
    ]

    readonly_fields = [
        'person',
        'login_method',
        'login_time',
        'login_photo_preview',
        'ip_address',
        'confidence',
        'success',
    ]

    fieldsets = (
        ('Asosiy Ma\'lumotlar', {
            'fields': ('person', 'login_method', 'login_time', 'success')
        }),
        ('Login Rasmi', {
            'fields': ('login_photo', 'login_photo_preview')
        }),
        ('Qo\'shimcha', {
            'fields': ('ip_address', 'confidence')
        }),
    )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

    def login_photo_preview(self, obj):
        if obj.login_photo:
            return format_html(
                '<img src="{}" width="300" style="border-radius: 10px; border: 2px solid #ddd;" />',
                obj.login_photo.url
            )
        return "Rasm yo'q"
    login_photo_preview.short_description = 'Login rasmi'

    def has_photo(self, obj):
        return '✅' if obj.login_photo else '❌'
    has_photo.short_description = 'Rasm'
