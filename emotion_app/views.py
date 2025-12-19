"""
emotion_app/views.py
Login System - Yuz tanish orqali login
"""
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.core.cache import cache
from django.contrib.auth import logout
from django.core.files.base import ContentFile
from .models import LoginLog

import cv2
import numpy as np
import base64
import face_recognition
from datetime import timedelta
from django.db.models import Count
from django.utils import timezone
import os
import json


# =====================================================
# Helper Classes
# =====================================================

class PersonRecognitionResult:
    """Yuzni tanish natijasini saqlash uchun klass"""

    def __init__(self, person=None, confidence=0.0):
        self.person = person
        self.confidence = confidence

    @property
    def is_registered(self) -> bool:
        return self.person is not None


# =====================================================
# Helper Functions
# =====================================================

def create_login_log(person, login_method, request, image_data=None, confidence=None):
    """
    Login log yaratish va rasm saqlash
    """
    try:
        # IP addressni olish
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip_address = x_forwarded_for.split(',')[0]
        else:
            ip_address = request.META.get('REMOTE_ADDR')

        # LoginLog yaratish
        login_log = LoginLog(
            person=person,
            login_method=login_method,
            ip_address=ip_address,
            confidence=confidence,
            success=True
        )

        # Agar rasm bo'lsa, saqlash
        if image_data:
            try:
                # Base64'dan rasmni decode qilish
                if "base64," in image_data:
                    image_data = image_data.split("base64,")[1]

                image_bytes = base64.b64decode(image_data)

                # Fayl nomi yaratish
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"{person.id}_{timestamp}.jpg"

                # Rasmni saqlash
                login_log.login_photo.save(
                    filename,
                    ContentFile(image_bytes),
                    save=False
                )
            except Exception as e:
                print(f"Rasm saqlashda xatolik: {e}")

        login_log.save()
        return login_log

    except Exception as e:
        print(f"LoginLog yaratishda xatolik: {e}")
        return None


# =====================================================
# Face Recognition Functions
# =====================================================

def load_known_faces_cached():
    """
    Cache'dan face encodinglarni yuklash
    """
    cache_key = "known_faces_data"
    cached_data = cache.get(cache_key)

    if cached_data:
        return cached_data["encodings"], cached_data["persons"]

    persons = Person.objects.all()
    known_encodings = []
    known_persons = []

    for person in persons:
        try:
            if person.face_encoding:
                enc = np.array(person.face_encoding, dtype=np.float64)
                known_encodings.append(enc)
                known_persons.append(person)
                continue

            if person.photo:
                image = face_recognition.load_image_file(person.photo.path)
                encodings = face_recognition.face_encodings(image)

                if encodings:
                    encoding_vec = encodings[0]
                    known_encodings.append(encoding_vec)
                    known_persons.append(person)
                    person.face_encoding = encoding_vec.tolist()
                    person.save(update_fields=["face_encoding"])

        except Exception:
            continue

    cache.set(
        cache_key,
        {"encodings": known_encodings, "persons": known_persons},
        timeout=3600,
    )

    return known_encodings, known_persons


def recognize_face_fast(frame):
    """
    Yuzni tanish (optimized)
    """
    small_frame = None
    rgb_frame = None

    try:
        known_encodings, known_persons = load_known_faces_cached()

        if not known_encodings:
            return PersonRecognitionResult()

        small_frame = cv2.resize(frame, (0, 0), fx=0.75, fy=0.75)
        rgb_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)

        face_locations = face_recognition.face_locations(
            rgb_frame,
            model="hog",
            number_of_times_to_upsample=1
        )

        if not face_locations:
            return PersonRecognitionResult()

        face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)

        if not face_encodings:
            return PersonRecognitionResult()

        face_encoding = face_encodings[0]

        matches = face_recognition.compare_faces(
            known_encodings, face_encoding, tolerance=0.5
        )
        face_distances = face_recognition.face_distance(known_encodings, face_encoding)

        if not any(matches):
            return PersonRecognitionResult()

        best_match_idx = int(np.argmin(face_distances))

        if matches[best_match_idx]:
            distance = float(face_distances[best_match_idx])
            confidence = (1.0 - distance) * 100.0

            if confidence < 51.0:
                return PersonRecognitionResult()

            person = known_persons[best_match_idx]

            result = PersonRecognitionResult(
                person=person,
                confidence=confidence,
            )

            del face_encodings, face_encoding, matches, face_distances
            return result

        return PersonRecognitionResult()

    except Exception as e:
        print(f"Face recognition error: {str(e)}")
        return PersonRecognitionResult()
    finally:
        if small_frame is not None:
            del small_frame
        if rgb_frame is not None:
            del rgb_frame


# =====================================================
# Views - HTML Pages
# =====================================================

def face_login(request):
    """Login sahifasi"""
    return render(request, "face.html")


def dashboard(request):
    """Dashboard sahifasi"""
    if not request.user.is_authenticated:
        return render(request, "face.html")
    return render(request, "dashboard_simple.html")


# =====================================================
# API - Face Recognition
# =====================================================

@csrf_exempt
def detect_face(request):
    """
    Yuzni tanish API
    """
    if request.method != "POST":
        return JsonResponse({"error": "Only POST method allowed"}, status=405)

    try:
        body = json.loads(request.body)
        image_data = body.get("image", "")

        if not image_data:
            return JsonResponse({"error": "No image provided"}, status=400)

        if "base64," in image_data:
            image_data = image_data.split("base64,")[1]

        try:
            image_bytes = base64.b64decode(image_data)
            nparr = np.frombuffer(image_bytes, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        except Exception:
            return JsonResponse({"error": "Failed to decode image"}, status=400)

        if frame is None or frame.size == 0:
            return JsonResponse({"error": "Invalid image data"}, status=400)

        recognition_result = recognize_face_fast(frame)

        if not recognition_result.is_registered:
            return JsonResponse(
                {
                    "person": {
                        "is_registered": False,
                        "status": "not_registered",
                        "message": "Shaxs tanilmadi",
                    },
                    "saved": False,
                    "message": "Iltimos ro'yxatdan o'tgan shaxsni ko'rsating",
                }
            )

        person = recognition_result.person
        confidence = recognition_result.confidence

        response_data = {
            "success": True,
            "person": {
                "id": person.id,
                "full_name": person.full_name,
                "first_name": person.first_name,
                "last_name": person.last_name,
                "photo_url": person.photo.url if person.photo else None,
                "confidence": round(confidence, 2),
                "is_registered": True,
                "status": "active",
                "registered_at": person.registered_at.strftime("%d.%m.%Y") if person.registered_at else "",
            },
            "message": f"{person.full_name} tanildi",
        }

        try:
            del frame, nparr, image_bytes
        except:
            pass

        return JsonResponse(response_data)

    except Exception as e:
        return JsonResponse(
            {
                "error": str(e),
                "message": "Xatolik yuz berdi",
            },
            status=500,
        )


# =====================================================
# API - Authentication
# =====================================================
@csrf_exempt
def face_login_auth(request):
    """
    UNIVERSAL LOGIN API - Face recognition yoki Passport login

    Ikki xil login qo'llab-quvvatlaydi:
    1. Face Recognition Login: person_id va image yuboriladi
    2. Passport Login: username (AD2423695) va optional image yuboriladi
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST method allowed'}, status=405)

    try:
        data = json.loads(request.body)
        # print(f"Login request data: {data}")

        # =============================
        # LOGIN METHOD ANIQLASH
        # =============================
        username_input = data.get('passport')  # Passport login uchun
        image_data = data.get('image')          # Rasm (ikkalasi uchun ham)
        print(f"Received login request - passport: {username_input is not None}")
        login_method = None
        person = None

        # =============================
        # 1. PASSPORT LOGIN
        # =============================
        if username_input:
            login_method = 'passport'
            username_input = username_input.strip().upper()

            # Passport format tekshirish (AD2423695)
            match = re.fullmatch(r'([A-Z]{2})(\d{7})', username_input)
            if not match:
                return JsonResponse({
                    'success': False,
                    'error': "Passport formati noto'g'ri. Masalan: AD2423695"
                }, status=400)

            passport_series = match.group(1)   # AD
            passport_number = match.group(2)   # 2423695

            # Person topish
            try:
                person = Person.objects.get(
                    passport_series=passport_series,
                    passport_number=passport_number
                )
            except Person.DoesNotExist:
                print(f"Passport ma'lumotlari noto'g'ri: {passport_series} {passport_number}")
                return JsonResponse({
                    'success': False,
                    'error': "Passport ma'lumotlari noto'g'ri"
                }, status=404)

            # Agar rasm yuborilgan bo'lsa - rasmni yangilash
            if image_data:
                try:
                    # Rasmni decode qilish
                    if "base64," in image_data:
                        image_data_clean = image_data.split("base64,")[1]
                    else:
                        image_data_clean = image_data

                    image_bytes = base64.b64decode(image_data_clean)

                    # MUHIM: Eski rasmni o'chirish
                    if person.photo:
                        try:
                            if os.path.isfile(person.photo.path):
                                os.remove(person.photo.path)
                            print(f"✅ Eski rasm o'chirildi: {person.photo.path}")
                        except Exception as e:
                            print(f"⚠️  Eski rasmni o'chirishda xatolik: {e}")

                        person.photo.delete(save=False)

                    # Eski face encoding'ni o'chirish
                    person.face_encoding = None

                    # Yangi rasmni saqlash
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    filename = f"person_{person.id}_{timestamp}.jpg"
                    person.photo.save(filename, ContentFile(image_bytes), save=True)

                    # Face encoding yaratish
                    try:
                        image = face_recognition.load_image_file(person.photo.path)
                        encodings = face_recognition.face_encodings(image)
                        if encodings:
                            person.face_encoding = encodings[0].tolist()
                            person.save()
                            print(f"✅ Face encoding yaratildi (Person {person.id})")
                    except Exception as e:
                        print(f"⚠️  Face encoding xatolik: {e}")

                    print(f"✅ Rasm yangilandi (Person {person.id})")
                except Exception as e:
                    print(f"❌ Rasmni saqlashda xatolik: {e}")


            # Django User yaratish/olish
            username_for_django = f"{passport_series}{passport_number}"
            user, created = User.objects.get_or_create(
                username=username_for_django,
                defaults={
                    'first_name': person.first_name,
                    'last_name': person.last_name,
                    'is_staff': True,
                    'is_superuser': True,
                    'is_active': True,
                }
            )

            if not created:
                updated = False
                if not user.is_staff:
                    user.is_staff = True
                    updated = True
                if not user.is_superuser:
                    user.is_superuser = True
                    updated = True
                if not user.is_active:
                    user.is_active = True
                    updated = True
                if updated:
                    user.save()

        # =============================
        # 2. FACE RECOGNITION LOGIN
        # =============================
        # elif person_id:
        #     login_method = 'face'

        #     # Person topish
        #     try:
        #         person = Person.objects.get(id=person_id)
        #     except Person.DoesNotExist:
        #         return JsonResponse({
        #             'success': False,
        #             'error': 'Shaxs topilmadi'
        #         }, status=404)

        #     # Django User yaratish/olish
        #     username_for_django = f"person_{person.id}"
        #     user, created = User.objects.get_or_create(
        #         username=username_for_django,
        #         defaults={
        #             'first_name': person.first_name,
        #             'last_name': person.last_name,
        #             'is_staff': True,
        #             'is_superuser': True,
        #         }
        #     )

        #     if not created:
        #         if not user.is_staff or not user.is_superuser:
        #             user.is_staff = True
        #             user.is_superuser = True
        #             user.save()

        # =============================
        # XATO: Hech qanday ma'lumot yo'q
        # =============================
        else:
            return JsonResponse({
                'success': False,
                'error': 'username (passport) yoki person_id yuborish kerak'
            }, status=400)

        # =============================
        # LOGIN QILISH
        # =============================
        user.backend = 'django.contrib.auth.backends.ModelBackend'
        login(request, user)

        # LoginLog yaratish
        create_login_log(
            person=person,
            login_method=login_method,
            request=request,
            image_data=image_data,
            # confidence=confidence if login_method == 'face' else None
        )

        # =============================
        # RESPONSE
        # =============================
        return JsonResponse({
            'success': True,
            'message': f'{person.full_name} tizimga kirdi',
            'redirect_url': '/dashboard/',
            'login_method': login_method,
            'user': {
                'id': user.id,
                'username': user.username,
                'birth_date': person.birth_date.strftime('%Y-%m-%d') if person.birth_date else None,
                'full_name': person.full_name,
                'is_staff': user.is_staff,
                'is_superuser': user.is_superuser,
            }
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e),
            'message': 'Login jarayonida xatolik'
        }, status=500)



import json
import re
from datetime import datetime
from django.http import JsonResponse
from django.contrib.auth import login
from django.contrib.auth.models import User

from emotion_app.models import Person

@csrf_exempt
def passport_login_auth(request):
    """
    Username (AD2423695) orqali login
    Username -> PASSPORT_SERIES + PASSPORT_NUMBER
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST method allowed'}, status=405)

    try:
        data = json.loads(request.body)

        username_input = (data.get('username') or '').strip().upper()
        image_data = data.get('image')  # optional

        if not username_input:
            return JsonResponse({
                'success': False,
                'error': "Passport seriya va raqam kerak"
            }, status=400)

        # =============================
        # USERNAME PARSE (AD2423695)
        # =============================
        match = re.fullmatch(r'([A-Z]{2})(\d{7})', username_input)
        if not match:
            return JsonResponse({
                'success': False,
                'error': "Passport formati noto'g'ri. Masalan: AD2423695"
            }, status=400)

        passport_series = match.group(1)   # AD
        passport_number = match.group(2)   # 2423695

        # =============================
        # PERSON TOPISH (faqat passport bo'yicha)
        # =============================
        try:
            person = Person.objects.get(
                passport_series=passport_series,
                passport_number=passport_number
            )
        except Person.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': "Passport ma'lumotlari noto'g'ri"
            }, status=404)

        # =============================
        # DJANGO USER (USERNAME = AD2423695)
        # =============================
        username = f"{passport_series}{passport_number}"

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

        if not created:
            updated = False
            if not user.is_staff:
                user.is_staff = True
                updated = True
            if not user.is_superuser:
                user.is_superuser = True
                updated = True
            if not user.is_active:
                user.is_active = True
                updated = True
            if updated:
                user.save()

        # =============================
        # LOGIN
        # =============================
        user.backend = 'django.contrib.auth.backends.ModelBackend'
        login(request, user)

        return JsonResponse({
            'success': True,
            'message': f'{person.full_name} tizimga kirdi',
            'person_id': person.id,  # Rasm yuklash uchun
            'user': {
                'id': user.id,
                'username': user.username,  # AD2423695
                'full_name': person.full_name,
            },
            'requires_photo': True  # Frontend'ga rasm olish kerakligini bildirish
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@csrf_exempt
def upload_login_photo(request):
    """
    Login vaqtida olingan rasmni saqlash (Person va LoginLog)
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST method allowed'}, status=405)

    try:
        data = json.loads(request.body)
        person_id = data.get('person_id')
        image_data = data.get('image')

        if not person_id or not image_data:
            return JsonResponse({
                'success': False,
                'error': 'person_id va image kerak'
            }, status=400)

        # Person topish
        try:
            person = Person.objects.get(id=person_id)
        except Person.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Shaxs topilmadi'
            }, status=404)

        # Rasmni decode qilish
        try:
            if "base64," in image_data:
                image_data = image_data.split("base64,")[1]

            image_bytes = base64.b64decode(image_data)

            # MUHIM: Eski rasmni o'chirish (agar mavjud bo'lsa)
            if person.photo:
                try:
                    import os
                    # Eski rasmni diskdan o'chirish
                    if os.path.isfile(person.photo.path):
                        os.remove(person.photo.path)
                    print(f"✅ Eski rasm o'chirildi: {person.photo.path}")
                except Exception as e:
                    print(f"⚠️  Eski rasmni o'chirishda xatolik: {e}")

                # Database'dan eski rasmni o'chirish
                person.photo.delete(save=False)

            # Eski face encoding'ni o'chirish
            person.face_encoding = None

            # Yangi rasmni Person'ga saqlash
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"person_{person.id}_{timestamp}.jpg"

            person.photo.save(filename, ContentFile(image_bytes), save=True)

            # Face encoding yaratish
            try:
                import face_recognition
                image = face_recognition.load_image_file(person.photo.path)
                encodings = face_recognition.face_encodings(image)

                if encodings:
                    person.face_encoding = encodings[0].tolist()
                    person.save()
            except Exception as e:
                print(f"Face encoding xatolik: {e}")

            # LoginLog yaratish
            create_login_log(
                person=person,
                login_method='passport',
                request=request,
                image_data=image_data,
                confidence=None
            )

            return JsonResponse({
                'success': True,
                'message': 'Rasm muvaffaqiyatli saqlandi',
                'photo_url': person.photo.url if person.photo else None
            })

        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': f'Rasmni saqlashda xatolik: {str(e)}'
            }, status=500)

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@csrf_exempt
def get_current_user(request):
    """
    Joriy foydalanuvchi ma'lumotlarini olish
    """
    try:
        if not request.user.is_authenticated:
            return JsonResponse({
                'success': False,
                'error': 'Not authenticated'
            }, status=401)

        person = None
        photo_url = None

        # Person'ni topish - username formatiga qarab
        try:
            if request.user.username.startswith('person_'):
                # Eski format: person_123
                person_id = int(request.user.username.replace('person_', ''))
                person = Person.objects.get(id=person_id)
            else:
                # Yangi format: AD3145734 (passport_series + passport_number)
                # Username'dan passport seriya va raqamni ajratish
                username = request.user.username

                # Passport seriya (birinchi 2 ta harf) va raqam (qolgan raqamlar)
                import re
                match = re.match(r'^([A-Z]{2})(.+)$', username)
                if match:
                    passport_series = match.group(1)
                    passport_number = match.group(2)

                    # Person topish
                    person = Person.objects.filter(
                        passport_series=passport_series,
                        passport_number=passport_number
                    ).first()

            # Rasm URL'ni olish
            if person and person.photo:
                photo_url = person.photo.url

        except Exception as e:
            print(f"Person topishda xatolik: {e}")
            pass

        return JsonResponse({
            'success': True,
            'user': {
                'id': request.user.id,
                'username': request.user.username,
                'full_name': person.full_name if person else f"{request.user.first_name} {request.user.last_name}".strip(),
                'is_staff': request.user.is_staff,
                'is_superuser': request.user.is_superuser,
                'photo_url': photo_url,
            }
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@csrf_exempt
def logout_view(request):
    """
    Tizimdan chiqish
    """
    try:
        logout(request)
        return JsonResponse({
            'success': True,
            'message': 'Tizimdan chiqildi'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


# =====================================================
# Excel Import
# =====================================================

def upload_excel_page(request):
    """Excel yuklash sahifasini ko'rsatish"""
    return render(request, 'upload_excel.html')

@csrf_exempt
def upload_excel(request):
    """
    Excel fayldan shaxslarni import qilish - TEZKOR VERSIYA
    Faqat Person yaratadi, Admin User'lar keyinroq yaratiladi
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST allowed'}, status=405)

    try:
        import pandas as pd
        from datetime import datetime

        if 'file' not in request.FILES:
            return JsonResponse({
                'success': False,
                'message': 'Fayl topilmadi'
            }, status=400)

        excel_file = request.FILES['file']

        # Excel faylni saqlash
        temp_path = f'/tmp/temp_excel_{datetime.now().timestamp()}.xlsx'
        with open(temp_path, 'wb+') as temp_file:
            for chunk in excel_file.chunks():
                temp_file.write(chunk)

        try:
            # Pandas bilan ma'lumotlarni o'qish
            df = pd.read_excel(temp_path)
            print(f"📊 Jami ma'lumotlar: {len(df)} qator")

        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Excel faylni o\'qib bo\'lmadi: {str(e)}'
            }, status=400)

        # Ustun nomlarini normalizatsiya qilish
        column_mapping = {}
        for col in df.columns:
            col_upper = str(col).upper().strip()

            if col_upper in ['ISM', 'ISMI', 'FIRST_NAME', 'FIRSTNAME', 'NAME']:
                column_mapping[col] = 'first_name'
            elif col_upper in ['FAMILIYA', 'FAMILIYASI', 'LAST_NAME', 'LASTNAME', 'SURNAME']:
                column_mapping[col] = 'last_name'
            elif col_upper in ['SHARIF', 'MIDDLE_NAME', 'MIDDLENAME', 'OTASINING ISMI']:
                column_mapping[col] = 'middle_name'
            elif col_upper in ['PASSPORT SERIYASI', 'PASSPORT_SERIES', 'PASPORT SERIYASI', 'HUJJAT SERIYA', 'Pasport seryasi']:
                column_mapping[col] = 'passport_series'
            elif col_upper in ['PASSPORT RAQAMI', 'PASSPORT_NUMBER', 'PASPORT RAQAMI', 'HUJJAT RAQAM']:
                column_mapping[col] = 'passport_number'
            elif 'TUGILGAN' in col_upper or 'TUG\'ILGAN' in col_upper or 'BIRTH' in col_upper or 'SANA' in col_upper:
                column_mapping[col] = 'birth_date'
            elif 'JSHIR' in col_upper or 'PINFL' in col_upper or 'JSHSHR' in col_upper:
                column_mapping[col] = 'pinfl'
            elif col_upper in ['MAXSUS UNVON', 'LAVOZIM', 'POSITION', 'VAZIFA', 'ISH']:
                column_mapping[col] = 'position'
            elif col_upper in ['TUMAN', 'DISTRICT', 'HUDUD']:
                column_mapping[col] = 'district'
            elif col_upper in ['IIB', 'BOLIM', 'BO\'LIM', 'DEPARTMENT', 'BULIM']:
                column_mapping[col] = 'department'
            elif col_upper in ['MAHALLA', 'MAHALLA NOMI']:
                column_mapping[col] = 'mahalla'
            elif col_upper in ['JETON SERIYASI', 'JETON', 'XIZMAT JETONI']:
                column_mapping[col] = 'jeton_series'
            elif 'TELEFON' in col_upper or 'PHONE' in col_upper or 'TEL' in col_upper:
                column_mapping[col] = 'phone_number'

        df.rename(columns=column_mapping, inplace=True)

        # KRITIK TEKSHIRUV
        has_first_name = 'first_name' in df.columns
        has_last_name = 'last_name' in df.columns

        if not has_first_name or not has_last_name:
            return JsonResponse({
                'success': False,
                'message': 'Excel faylda Ism va Familiya ustunlari topilmadi!',
                'available_columns': list(df.columns),
                'required_columns': ['ISM yoki ISMI', 'FAMILIYA yoki FAMILIYASI']
            }, status=400)

        success_count = 0
        error_count = 0
        errors = []
        warnings = []
        
        # Admin User'lar yaratish uchun ma'lumotlarni saqlash
        users_to_create = []

        print(f"\n🚀 Person ma'lumotlarini import qilish boshlandi...\n")

        for index, row in df.iterrows():
            try:
                # Ism va familiyani olish
                first_name = str(row.get('first_name', '')).strip() if pd.notna(row.get('first_name')) else ''
                last_name = str(row.get('last_name', '')).strip() if pd.notna(row.get('last_name')) else ''

                # Ism yoki familiya bo'sh bo'lsa
                if not first_name or not last_name or first_name == 'nan' or last_name == 'nan':
                    error_count += 1
                    continue

                # Boshqa maydonlarni olish
                def safe_get(field_name):
                    val = row.get(field_name)
                    if pd.isna(val) or val is None:
                        return None
                    val_str = str(val).strip()
                    if val_str == '' or val_str == 'nan' or val_str.lower() in ['none', 'vakant']:
                        return None
                    return val_str

                middle_name = safe_get('middle_name')
                passport_series = safe_get('passport_series')
                if passport_series:
                    passport_series = passport_series.upper()

                passport_number = safe_get('passport_number')
                pinfl = safe_get('pinfl')
                position = safe_get('position')
                district = safe_get('district')
                department = safe_get('department')
                phone_number = safe_get('phone_number')
                mahalla = safe_get('mahalla')
                jeton_series = safe_get('jeton_series')

                # Tug'ilgan kunni parse qilish
                birth_date = None
                if pd.notna(row.get('birth_date')):
                    try:
                        bd = row.get('birth_date')
                        if isinstance(bd, pd.Timestamp):
                            birth_date = bd.date()
                        else:
                            bd_str = str(bd).strip()
                            for fmt in ['%Y-%m-%d', '%d.%m.%Y', '%d/%m/%Y', '%Y/%m/%d', '%d-%m-%Y']:
                                try:
                                    birth_date = datetime.strptime(bd_str, fmt).date()
                                    break
                                except:
                                    continue
                    except:
                        pass

                # Person yaratish yoki yangilash
                person_data = {
                    'first_name': first_name,
                    'last_name': last_name,
                    'middle_name': middle_name,
                    'birth_date': birth_date,
                    'pinfl': pinfl,
                    'position': position,
                    'district': district,
                    'department': department,
                    'phone_number': phone_number,
                    'mahalla': mahalla,
                    'jeton_series': jeton_series,
                }
                
                # Passport seriyasini qo'shish
                if passport_series and passport_series.strip():
                    person_data['passport_series'] = passport_series.strip()
                    
                # Passport raqamini qo'shish
                if passport_number and str(passport_number).strip():
                    try:
                        passport_number_str = str(passport_number).strip()
                        if passport_number_str and passport_number_str != 'nan':
                            person_data['passport_number'] = int(passport_number_str)
                    except (ValueError, TypeError):
                        pass

                try:
                    # Passport seriya + raqam bo'yicha qidirish
                    if 'passport_series' in person_data and 'passport_number' in person_data:
                        person, created = Person.objects.update_or_create(
                            passport_series=person_data['passport_series'],
                            passport_number=person_data['passport_number'],
                            defaults=person_data
                        )
                    # PINFL bo'yicha qidirish
                    elif pinfl:
                        person, created = Person.objects.update_or_create(
                            pinfl=pinfl,
                            defaults=person_data
                        )
                    # Yangi person yaratish
                    else:
                        person = Person.objects.create(**person_data)
                        created = True
                        
                    # User yaratish uchun ma'lumotlarni saqlash
                    users_to_create.append({
                        'person': person,
                        'passport_series': passport_series,
                        'passport_number': passport_number,
                        'pinfl': pinfl,
                        'birth_date': birth_date
                    })
                    
                    success_count += 1
                    
                    # Har 20 ta qatordan keyin progress ko'rsatish
                    if success_count % 20 == 0:
                        print(f"   ✅ {success_count} ta person saqlandi...")

                except Exception as e:
                    error_msg = f"Qator {index + 2}: Person yaratishda xatolik: {str(e)[:100]}"
                    errors.append(error_msg)
                    error_count += 1

            except Exception as e:
                error_msg = f"Qator {index + 2}: {str(e)[:100]}"
                errors.append(error_msg)
                error_count += 1

        # Admin User'larni yaratish (keyinroq alohida)
        print(f"\n👤 Admin User'lar yaratilishi kerak: {len(users_to_create)} ta")
        
        # Faqat dastlabki 5 tasini yaratish (sinov uchun)
        created_users_count = 0
        for i, user_data in enumerate(users_to_create[:5]):  # Faqat 5 tasi
            try:
                person = user_data['person']
                passport_series = user_data['passport_series']
                passport_number = user_data['passport_number']
                pinfl = user_data['pinfl']
                birth_date = user_data['birth_date']
                
                # USERNAME yaratish
                username = None
                if passport_series and passport_number:
                    username = f"{passport_series}{passport_number}"
                elif pinfl:
                    username = f"pinfl_{pinfl}"
                else:
                    username = f"person_{person.id}"

                # PASSWORD yaratish
                if birth_date:
                    password = str(birth_date.strftime('%d%m%Y'))
                else:
                    password = 'password123'

                # User yaratish/yangilash
                from django.contrib.auth.models import User
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
                    created_users_count += 1
                    print(f"  ✅ Admin User yaratildi: {username}")
                else:
                    user.set_password(password)
                    user.first_name = person.first_name
                    user.last_name = person.last_name
                    user.is_staff = True
                    user.is_superuser = True
                    user.is_active = True
                    user.save()
                    print(f"  🔄 Admin User yangilandi: {username}")
                    
            except Exception as e:
                warnings.append(f"User {person.first_name} yaratishda xatolik: {str(e)[:100]}")

        # Temp faylni o'chirish
        try:
            import os
            os.remove(temp_path)
        except:
            pass

        print(f"\n✅ Person import yakunlandi:")
        print(f"   Jami qator: {len(df)}")
        print(f"   Muvaffaqiyatli: {success_count}")
        print(f"   Xatoliklar: {error_count}")
        print(f"   User yaratildi: {created_users_count} ta (faqat dastlabki 5 tasi)")
        
        return JsonResponse({
            'success': True,
            'message': f'Person import yakunlandi. {success_count} ta person saqlandi. Admin User\'lar keyinroq yaratiladi.',
            'total_count': len(df),
            'success_count': success_count,
            'error_count': error_count,
            'users_created': created_users_count,
            'errors': errors[:10],
            'warnings': warnings[:10],
            'note': 'Admin User\'larning qolgan qismini keyinroq yaratish mumkin'
        })

    except Exception as e:
        # Temp faylni o'chirish
        try:
            import os
            if 'temp_path' in locals():
                os.remove(temp_path)
        except:
            pass
            
        return JsonResponse({
            'success': False,
            'message': f'Import xatolik: {str(e)}'
        }, status=500)
    
# =====================================================
# Statistics API
# =====================================================

@csrf_exempt
def get_statistics(request):
    """
    Umumiy statistika - barcha loginlar
    """
    try:
        # Bugungi kunni olish
        today = timezone.now().date()
        yesterday = today - timedelta(days=1)
        week_ago = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)

        # Umumiy statistika
        total_logins = LoginLog.objects.count()
        total_persons = Person.objects.count()

        # Bugun
        today_logins = LoginLog.objects.filter(
            login_time__date=today
        ).count()

        # Kecha
        yesterday_logins = LoginLog.objects.filter(
            login_time__date=yesterday
        ).count()

        # Bu hafta
        week_logins = LoginLog.objects.filter(
            login_time__gte=week_ago
        ).count()

        # Bu oy
        month_logins = LoginLog.objects.filter(
            login_time__gte=month_ago
        ).count()

        # Login usullari bo'yicha
        face_logins = LoginLog.objects.filter(login_method='face').count()
        passport_logins = LoginLog.objects.filter(login_method='passport').count()

        # Eng ko'p login qilgan shaxslar (TOP 10)
        top_users = Person.objects.annotate(
            login_count=Count('login_logs')
        ).filter(login_count__gt=0).order_by('-login_count')[:10]

        top_users_data = [{
            'id': person.id,
            'full_name': person.full_name,
            'passport_series': person.passport_series,
            'position': person.position,
            'login_count': person.login_count,
        } for person in top_users]

        # Oxirgi 20 ta login
        recent_logins = LoginLog.objects.select_related('person').all()[:20]
        recent_logins_data = [{
            'id': log.id,
            'person_id': log.person.id,
            'person_name': log.person.full_name,
            'login_method': log.login_method,
            'login_time': log.login_time.strftime('%Y-%m-%d %H:%M:%S'),
            'ip_address': log.ip_address,
            'confidence': log.confidence,
        } for log in recent_logins]

        return JsonResponse({
            'success': True,
            'statistics': {
                'total_logins': total_logins,
                'total_persons': total_persons,
                'today_logins': today_logins,
                'yesterday_logins': yesterday_logins,
                'week_logins': week_logins,
                'month_logins': month_logins,
                'face_logins': face_logins,
                'passport_logins': passport_logins,
                'top_users': top_users_data,
                'recent_logins': recent_logins_data,
            }
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@csrf_exempt
def get_person_statistics(request, person_id):
    """
    Bitta shaxs uchun statistika
    """
    try:
        person = Person.objects.get(id=person_id)

        # Umumiy login soni
        total_logins = person.login_logs.count()

        # Login usullari bo'yicha
        face_logins = person.login_logs.filter(login_method='face').count()
        passport_logins = person.login_logs.filter(login_method='passport').count()

        # Oxirgi login
        last_login = person.login_logs.first()
        last_login_time = last_login.login_time.strftime('%Y-%m-%d %H:%M:%S') if last_login else None

        # Bugungi loginlar
        today = timezone.now().date()
        today_logins = person.login_logs.filter(login_time__date=today).count()

        # Oxirgi 30 kun statistikasi (kunlik)
        thirty_days_ago = today - timedelta(days=30)
        daily_stats = []

        for i in range(30):
            date = today - timedelta(days=i)
            count = person.login_logs.filter(login_time__date=date).count()
            daily_stats.append({
                'date': date.strftime('%Y-%m-%d'),
                'count': count
            })

        daily_stats.reverse()

        # Barcha loginlar (oxirgi 50 ta)
        all_logins = person.login_logs.all()[:50]
        logins_data = [{
            'id': log.id,
            'login_method': log.login_method,
            'login_time': log.login_time.strftime('%Y-%m-%d %H:%M:%S'),
            'ip_address': log.ip_address,
            'confidence': log.confidence,
            'has_photo': bool(log.login_photo),
            'photo_url': log.login_photo.url if log.login_photo else None,
        } for log in all_logins]

        return JsonResponse({
            'success': True,
            'person': {
                'id': person.id,
                'full_name': person.full_name,
                'passport_series': person.passport_series,
                'position': person.position,
                'district': person.district,
                'phone_number': person.phone_number,
            },
            'statistics': {
                'total_logins': total_logins,
                'face_logins': face_logins,
                'passport_logins': passport_logins,
                'last_login_time': last_login_time,
                'today_logins': today_logins,
                'daily_stats': daily_stats,
                'recent_logins': logins_data,
            }
        })

    except Person.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Shaxs topilmadi'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@csrf_exempt
def get_login_logs(request):
    """
    Barcha login loglarini olish - filtrlash imkoniyati bilan

    Query parametrlari:
    - person_id: Shaxs ID
    - method: face yoki passport
    - start_date: Boshlanish sanasi (YYYY-MM-DD)
    - end_date: Tugash sanasi (YYYY-MM-DD)
    - limit: Maksimal natijalar soni (default: 100)
    - offset: O'tkazib yuborish (pagination uchun)
    """
    try:
        # Barcha loginlardan boshlash
        logs = LoginLog.objects.all().select_related('person')

        # Filtrlash
        person_id = request.GET.get('person_id')
        if person_id:
            logs = logs.filter(person_id=person_id)

        method = request.GET.get('method')
        if method and method in ['face', 'passport']:
            logs = logs.filter(login_method=method)

        start_date = request.GET.get('start_date')
        if start_date:
            try:
                from datetime import datetime
                start = datetime.strptime(start_date, '%Y-%m-%d').date()
                logs = logs.filter(login_time__date__gte=start)
            except ValueError:
                pass

        end_date = request.GET.get('end_date')
        if end_date:
            try:
                from datetime import datetime
                end = datetime.strptime(end_date, '%Y-%m-%d').date()
                logs = logs.filter(login_time__date__lte=end)
            except ValueError:
                pass

        # Pagination
        limit = int(request.GET.get('limit', 100))
        offset = int(request.GET.get('offset', 0))

        total_count = logs.count()
        logs = logs[offset:offset + limit]

        # Ma'lumotlarni tayyorlash
        logs_data = []
        for log in logs:
            logs_data.append({
                'id': log.id,
                'person': {
                    'id': log.person.id,
                    'full_name': log.person.full_name,
                    'passport_series': log.person.passport_series,
                    'position': log.person.position,
                    'district': log.person.district,
                },
                'login_method': log.login_method,
                'login_time': log.login_time.strftime('%Y-%m-%d %H:%M:%S'),
                'ip_address': log.ip_address,
                'confidence': log.confidence,
                'success': log.success,
                'has_photo': bool(log.login_photo),
                'photo_url': request.build_absolute_uri(log.login_photo.url) if log.login_photo else None,
            })

        return JsonResponse({
            'success': True,
            'total_count': total_count,
            'limit': limit,
            'offset': offset,
            'logs': logs_data
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)
