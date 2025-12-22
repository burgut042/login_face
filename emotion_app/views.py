"""
emotion_app/views.py
Login System - Yuz tanish orqali login
"""
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.core.cache import cache
from django.contrib.auth import logout
from django.core.files.base import ContentFile
from .models import LoginLog, Person
from django.http import JsonResponse

import cv2
import numpy as np
import base64
import face_recognition
from datetime import timedelta, datetime
from django.db.models import Count
from django.utils import timezone
import json
import os


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

        # LoginLog yaratish (V1 login_logs jadvaliga)
        login_log = LoginLog(
            inspector=person,  # V1 da inspector field
            login_method=login_method.upper(),  # V1 da FACE/PASSPORT (uppercase)
            ip_address=ip_address or '0.0.0.0',
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
    SMART LOGIN API - Passport + Face Recognition

    Oqim:
    1. User passport kiritadi
    2. Person topiladi va rasm tekshiriladi:
       - Rasm yo'q → Rasmga tushirish kerak (requires_photo: true)
       - Rasm bor:
         - 1 oy ichida yangilangan → Face recognition (requires_face: true)
         - 1 oydan eski → Yangi rasm olish kerak (requires_photo: true)
    3. User rasm yoki face yuboradi
    4. Login
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST method allowed'}, status=405)

    try:
        from datetime import timedelta
        data = json.loads(request.body)

        # =============================
        # PASSPORT KIRITISH (1-qadam)
        # =============================
        username_input = data.get('username')  # AD2423695
        image_data = data.get('image')         # Camera'dan rasm

        if not username_input:
            return JsonResponse({
                'success': False,
                'error': 'Passport seriya va raqamni kiriting'
            }, status=400)

        # Passport format tekshirish
        username_input = username_input.strip().upper()
        match = re.fullmatch(r'([A-Z]{2})(\d{7})', username_input)
        if not match:
            return JsonResponse({
                'success': False,
                'error': "Passport formati noto'g'ri. Masalan: AD2423695"
            }, status=400)

        passport_full = username_input  # AB1234567 (already uppercased)

        # Person topish (V1 inspectors jadvalida)
        try:
            person = Person.objects.get(
                passport=passport_full
            )
        except Person.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': "Passport ma'lumotlari noto'g'ri"
            }, status=404)

        # =============================
        # RASM TEKSHIRISH (2-qadam)
        # =============================
        login_method = None
        photo_age_days = None

        if person.photo:
            # Rasmning yoshini hisoblash
            if hasattr(person.photo, 'name') and person.photo.name:
                try:
                    # Fayl yaratilgan vaqtini olish
                    photo_path = person.photo.path
                    if os.path.exists(photo_path):
                        photo_mtime = os.path.getmtime(photo_path)
                        photo_date = datetime.fromtimestamp(photo_mtime)
                        photo_age_days = (datetime.now() - photo_date).days
                except Exception as e:
                    print(f"Rasm yoshini hisoblab bo'lmadi: {e}")
                    photo_age_days = None

        # =============================
        # LOGIKA ANIQLASH
        # =============================
        if not person.photo or not person.photo.name:
            # VARIANT 1: Rasm yo'q
            if not image_data:
                return JsonResponse({
                    'success': False,
                    'requires_photo': True,
                    'message': 'Sizning rasmingiz bazada yo\'q. Iltimos rasmga tushing.',
                    'person_id': person.id,
                    'full_name': person.full_name
                })
            login_method = 'passport_new_photo'

        elif photo_age_days is not None and photo_age_days > 30:
            # VARIANT 2: Rasm 1 oydan eski
            if not image_data:
                return JsonResponse({
                    'success': False,
                    'requires_photo': True,
                    'message': f'Rasmingiz {photo_age_days} kun oldin yangilangan. Yangi rasm oling.',
                    'person_id': person.id,
                    'full_name': person.full_name,
                    'photo_age_days': photo_age_days
                })
            login_method = 'passport_update_photo'

        else:
            # VARIANT 3: Rasm bor va yangi (1 oy ichida)
            if not image_data:
                return JsonResponse({
                    'success': False,
                    'requires_face': True,
                    'message': 'Iltimos yuzingizni ko\'rsating',
                    'person_id': person.id,
                    'full_name': person.full_name,
                    'photo_age_days': photo_age_days or 0
                })
            login_method = 'face_recognition'

        # =============================
        # 3-QADAM: RASM BILAN LOGIN (yangi yoki eski rasm)
        # =============================
        if login_method in ['passport_new_photo', 'passport_update_photo']:
            # Rasmni decode qilish
            if "base64," in image_data:
                image_data_clean = image_data.split("base64,")[1]
            else:
                image_data_clean = image_data

            image_bytes = base64.b64decode(image_data_clean)

            # Eski rasmni o'chirish (agar mavjud bo'lsa)
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

            print(f"✅ Yangi rasm saqlandi (Person {person.id})")
            login_method = 'passport'

        # =============================
        # 4-QADAM: FACE RECOGNITION
        # =============================
        elif login_method == 'face_recognition':
            # Rasmni decode qilish
            if "base64," in image_data:
                image_data_clean = image_data.split("base64,")[1]
            else:
                image_data_clean = image_data

            image_bytes = base64.b64decode(image_data_clean)

            # Face recognition
            try:
                import numpy as np
                from PIL import Image as PILImage
                import io

                # Rasmni load qilish
                img = PILImage.open(io.BytesIO(image_bytes))
                img_array = np.array(img)

                # Face encoding topish
                face_encodings = face_recognition.face_encodings(img_array)

                if not face_encodings:
                    return JsonResponse({
                        'success': False,
                        'error': 'Rasmda yuz topilmadi. Qaytadan urinib ko\'ring.'
                    }, status=400)

                # Bazadagi face encoding bilan solishtirish
                if not person.face_encoding:
                    return JsonResponse({
                        'success': False,
                        'error': 'Bazada face encoding yo\'q. Yangi rasm oling.',
                        'requires_photo': True
                    }, status=400)

                known_encoding = np.array(person.face_encoding)
                current_encoding = face_encodings[0]

                # Face comparison
                face_distance = face_recognition.face_distance([known_encoding], current_encoding)[0]
                confidence = (1 - face_distance) * 100

                print(f"Face recognition confidence: {confidence:.2f}%")

                if confidence < 51.0:
                    return JsonResponse({
                        'success': False,
                        'error': f'Yuz mos kelmadi (aniqlik: {confidence:.1f}%). Qaytadan urinib ko\'ring.',
                        'confidence': round(confidence, 2)
                    }, status=400)

                print(f"✅ Face recognized: {person.full_name} ({confidence:.2f}%)")
                login_method = 'face'

            except Exception as e:
                print(f"❌ Face recognition xatosi: {e}")
                return JsonResponse({
                    'success': False,
                    'error': 'Face recognition jarayonida xatolik yuz berdi'
                }, status=500)

        # =============================
        # 5-QADAM: USER VA LOGIN
        # =============================
        # Django User yaratish/olish
        username_for_django = person.passport  # V1 da birlashgan passport
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
        # 6-QADAM: LOGIN QILISH
        # =============================
        user.backend = 'django.contrib.auth.backends.ModelBackend'
        login(request, user)

        # LoginLog yaratish
        confidence_value = None
        if login_method == 'face':
            try:
                confidence_value = confidence
            except:
                confidence_value = None

        create_login_log(
            person=person,
            login_method=login_method,
            request=request,
            image_data=image_data,
            confidence=confidence_value
        )

        # =============================
        # 7-QADAM: RESPONSE
        # =============================
        response_data = {
            'success': True,
            'message': f'{person.full_name} tizimga kirdi',
            'redirect_url': '/dashboard/',
            'login_method': login_method,
            'user': {
                'id': user.id,
                'username': user.username,
                'full_name': person.full_name,
                'is_staff': user.is_staff,
                'is_superuser': user.is_superuser,
            }
        }

        if login_method == 'face' and confidence_value:
            response_data['confidence'] = round(confidence_value, 2)

        if photo_age_days is not None:
            response_data['photo_age_days'] = photo_age_days

        return JsonResponse(response_data)

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

        passport_full = passport_input  # AD2423695

        # =============================
        # PERSON TOPISH (faqat passport bo'yicha)
        # =============================
        try:
            person = Person.objects.get(
                passport=passport_full
            )
        except Person.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': "Passport ma'lumotlari noto'g'ri"
            }, status=404)

        # =============================
        # DJANGO USER (USERNAME = AD2423695)
        # =============================
        username = person.passport  # V1 birlashgan passport

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
        # RASM YUKLASH (agar yuborilgan bo'lsa)
        # =============================
        if image_data:
            try:
                # Rasmni decode qilish
                if "base64," in image_data:
                    image_data_clean = image_data.split("base64,")[1]
                else:
                    image_data_clean = image_data

                image_bytes = base64.b64decode(image_data_clean)

                # MUHIM: Eski rasmni o'chirish (agar mavjud bo'lsa)
                if person.photo:
                    try:
                        import os
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
                    import face_recognition
                    image = face_recognition.load_image_file(person.photo.path)
                    encodings = face_recognition.face_encodings(image)
                    if encodings:
                        person.face_encoding = encodings[0].tolist()
                        person.save()
                        print(f"✅ Face encoding yaratildi (Person {person.id})")
                except Exception as e:
                    print(f"⚠️  Face encoding xatolik: {e}")

                # LoginLog yaratish
                create_login_log(
                    person=person,
                    login_method='passport',
                    request=request,
                    image_data=image_data,
                    confidence=None
                )

                print(f"✅ Rasm va LoginLog saqlandi (Person {person.id})")

            except Exception as e:
                print(f"❌ Rasmni saqlashda xatolik: {e}")

        # =============================
        # LOGIN
        # =============================
        user.backend = 'django.contrib.auth.backends.ModelBackend'
        login(request, user)

        return JsonResponse({
            'success': True,
            'message': f'{person.full_name} tizimga kirdi',
            'redirect_url': '/dashboard/',
            'user': {
                'id': user.id,
                'username': user.username,  # AD2423695
                'full_name': person.full_name,
            }
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

                # Person topish passport bo'yicha (V1 birlashgan format)
                person = Person.objects.filter(
                    passport=username
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
    Excel fayldan shaxslarni import qilish - rasmlar bilan
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Only POST allowed'}, status=405)

    try:
        import pandas as pd
        from datetime import datetime
        import openpyxl
        from PIL import Image
        import io
        import requests
        from urllib.parse import urlparse

        if 'file' not in request.FILES:
            return JsonResponse({
                'success': False,
                'message': 'Fayl topilmadi'
            }, status=400)

        excel_file = request.FILES['file']

        # Excel faylni saqlash (rasmlarni olish uchun)
        temp_path = f'/tmp/temp_excel_{datetime.now().timestamp()}.xlsx'
        with open(temp_path, 'wb+') as temp_file:
            for chunk in excel_file.chunks():
                temp_file.write(chunk)

        try:
            # Pandas bilan ma'lumotlarni o'qish
            df = pd.read_excel(temp_path)

            # Openpyxl bilan rasmlarni o'qish
            wb = openpyxl.load_workbook(temp_path)
            ws = wb.active

            # Rasmlarni topish va to'g'ri mapping qilish
            images_dict = {}  # {DataFrame index: rasm_bytes}

            print(f"📸 Excel'da {len(ws._images)} ta rasm topildi")

            for image in ws._images:
                try:
                    # Excel qator raqami (1-indexed)
                    excel_row = image.anchor._from.row + 1
                    print(excel_row)

                    df_index = excel_row - 2

                    # Rasmni olish
                    img_bytes = image._data()

                    if df_index >= 0:
                        images_dict[df_index] = img_bytes
                        print(f"  ✓ Rasm: Excel qator {excel_row} → DataFrame index {df_index}")

                except Exception as e:
                    print(f"  ✗ Rasmni o'qishda xatolik: {e}")
                    pass

            print(f"📊 Jami ma'lumotlar: {len(df)} qator")
            print(f"🖼️  Rasmlar mapping: {list(images_dict.keys())}")

        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Excel faylni o\'qib bo\'lmadi: {str(e)}'
            }, status=400)

        # Ustun nomlarini normalizatsiya qilish (keng variant)
        column_mapping = {}
        for col in df.columns:
            print(col)
            col_upper = str(col).upper().strip()

            # Ism variantlari (Ismi)
            if col_upper in ['ISM', 'ISMI', 'FIRST_NAME', 'FIRSTNAME', 'NAME']:
                column_mapping[col] = 'first_name'
            # Familiya variantlari (Familiyasi)
            elif col_upper in ['FAMILIYA', 'FAMILIYASI', 'LAST_NAME', 'LASTNAME', 'SURNAME']:
                column_mapping[col] = 'last_name'
            # Sharif variantlari (Otasining ismi)
            elif col_upper in ['SHARIF', 'MIDDLE_NAME', 'MIDDLENAME', 'OTASINING ISMI']:
                column_mapping[col] = 'middle_name'
            # Passport seriyasi
            elif col_upper in ['PASSPORT SERIYASI', 'PASSPORT_SERIES', 'PASPORT SERIYASI', 'HUJJAT SERIYA', 'Pasport seryasi']:
                column_mapping[col] = 'passport_series'
            # Passport raqami
            elif col_upper in ['PASSPORT RAQAMI', 'PASSPORT_NUMBER', 'PASPORT RAQAMI', 'HUJJAT RAQAM']:
                column_mapping[col] = 'passport_number'
            # Tug'ilgan kun oy yili
            elif 'TUGILGAN' in col_upper or 'TUG\'ILGAN' in col_upper or 'BIRTH' in col_upper or 'SANA' in col_upper:
                column_mapping[col] = 'birth_date'
            # JShIR / PINFL
            elif 'JSHIR' in col_upper or 'PINFL' in col_upper or 'JSHSHR' in col_upper:
                column_mapping[col] = 'pinfl'
            # Maxsus unvon / Lavozim
            elif col_upper in ['MAXSUS UNVON', 'LAVOZIM', 'POSITION', 'VAZIFA', 'ISH']:
                column_mapping[col] = 'position'
            # Tuman
            elif col_upper in ['TUMAN', 'DISTRICT', 'HUDUD']:
                column_mapping[col] = 'district'
            # IIB / Bo'lim
            elif col_upper in ['IIB', 'BOLIM', 'BO\'LIM', 'DEPARTMENT', 'BULIM']:
                column_mapping[col] = 'department'
            # Mahalla
            elif col_upper in ['MAHALLA', 'MAHALLA NOMI']:
                column_mapping[col] = 'mahalla'
            # Jeton seriyasi
            elif col_upper in ['JETON SERIYASI', 'JETON', 'XIZMAT JETONI']:
                column_mapping[col] = 'jeton_series'
            # Telefon raqami
            elif 'TELEFON' in col_upper or 'PHONE' in col_upper or 'TEL' in col_upper:
                column_mapping[col] = 'phone_number'
            # Rasm (3x4 RASM)
            elif 'RASM' in col_upper or 'PHOTO' in col_upper or 'IMAGE' in col_upper or 'URL' in col_upper or '3X4' in col_upper:
                column_mapping[col] = 'photo_url'

        # MUHIM: Mapping natijalarini ko'rsatish
        print(f"\n" + "="*70)
        print(f"📊 COLUMN MAPPING NATIJALARI:")
        print(f"="*70)
        print(f"\n📝 Asl Excel ustunlari:")
        for col in df.columns:
            print(f"   - {col}")

        print(f"\n🔄 Mapping qilingan ustunlar:")
        if column_mapping:
            for old_col, new_col in column_mapping.items():
                print(f"   '{old_col}' -> '{new_col}'")
        else:
            print(f"   ❌ HECH QANDAY USTUN MAPPING QILINMADI!")

        # Unmapped columns
        unmapped = [col for col in df.columns if col not in column_mapping]
        if unmapped:
            print(f"\n⚠️  Mapping qilinmagan ustunlar (e'tiborga olinmaydi):")
            for col in unmapped:
                print(f"   - {col}")

        df.rename(columns=column_mapping, inplace=True)

        # KRITIK TEKSHIRUV: first_name va last_name mavjudmi?
        print(f"\n" + "="*70)
        print(f"🔍 KRITIK USTUNLAR TEKSHIRUVI:")
        print(f"="*70)
        has_first_name = 'first_name' in df.columns
        has_last_name = 'last_name' in df.columns

        fn_status = "✅ HA" if has_first_name else "❌ YO'Q - BARCHA MA'LUMOTLAR FAIL BO'LADI!"
        ln_status = "✅ HA" if has_last_name else "❌ YO'Q - BARCHA MA'LUMOTLAR FAIL BO'LADI!"
        print(f"   first_name mavjudmi? {fn_status}")
        print(f"   last_name mavjudmi?  {ln_status}")

        if not has_first_name or not has_last_name:
            print(f"\n❌ XATOLIK: Excel faylda 'Ism' va 'Familiya' ustunlari topilmadi!")
            print(f"\n💡 Quyidagi ustun nomlaridan birini ishlating:")
            print(f"   Ism uchun: ISM, ISMI, FIRST_NAME, FIRSTNAME, NAME")
            print(f"   Familiya uchun: FAMILIYA, FAMILIYASI, LAST_NAME, LASTNAME, SURNAME")
            return JsonResponse({
                'success': False,
                'message': 'Excel faylda Ism va Familiya ustunlari topilmadi. Ustun nomlarini tekshiring!',
                'available_columns': list(df.columns),
                'required_columns': ['ISM yoki ISMI', 'FAMILIYA yoki FAMILIYASI']
            }, status=400)

        # Ustunlarni ko'rsatish
        print(f"\n📋 Excel ustunlari (mapping'dan keyin):")
        print(f"   {list(df.columns)}")
        print(f"\n🔍 Birinchi qator ma'lumotlari:")
        if len(df) > 0:
            first_row = df.iloc[0]
            for col in df.columns:
                val = first_row[col]
                print(f"   {col}: {val} (type: {type(val).__name__})")
        print(f"\n" + "="*70)

        success_count = 0
        error_count = 0
        errors = []
        warnings = []

        print(f"\n🚀 Ma'lumotlarni import qilish boshlandi...\n")

        for index, row in df.iterrows():
            try:
                print(f"⚙️  Qator {index + 2} ishlanmoqda...")

                # Faqat ism va familiya majburiy
                first_name = str(row.get('first_name', '')).strip() if pd.notna(row.get('first_name')) else ''
                last_name = str(row.get('last_name', '')).strip() if pd.notna(row.get('last_name')) else ''

                print(f"   ISM: '{first_name}', FAMILIYA: '{last_name}'")

                # Ism yoki familiya bo'sh bo'lsa, o'tkazib yuborish
                if not first_name or not last_name or first_name == 'nan' or last_name == 'nan':
                    error_msg = f"Qator {index + 2}: Ism yoki Familiya yo'q (ISM='{first_name}', FAMILIYA='{last_name}')"
                    errors.append(error_msg)
                    print(f"   ❌ {error_msg}")
                    error_count += 1
                    continue

                # Boshqa barcha maydonlar ixtiyoriy - mavjud bo'lsa olinadi
                def safe_get(field_name):
                    """Maydonni xavfsiz olish - bo'sh bo'lsa None qaytaradi"""
                    val = row.get(field_name)
                    if pd.isna(val) or val is None:
                        return None
                    val_str = str(val).strip()
                    if val_str == '' or val_str == 'nan' or val_str.lower() == 'none':
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
                photo_url = safe_get('photo_url')

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

                # Person yaratish yoki yangilash - BARCHA field'lar (V1 format)
                # Passport birlashtirilgan format: AB1234567
                passport_full = None
                if passport_series and passport_number:
                    passport_full = f"{passport_series.strip().upper()}{str(int(passport_number)).strip()}"

                person_data = {
                    'first_name': first_name,
                    'last_name': last_name,
                    'middle_name': middle_name,
                    'passport': passport_full,  # V1 birlashgan format
                    'birth_date': birth_date,
                    'pinfl': pinfl,
                    'position': position,
                    'tuman': district,  # V1 da tuman
                    'department': department,
                    'phone': phone_number,  # V1 da phone
                    'mahalla': mahalla,
                    'badge_number': jeton_series,  # V1 da badge_number
                }

                # BIRINCHI: Person yaratish yoki yangilash (RASMISIZ)
                # MUHIM: Passport bo'yicha tekshirish (V1 da unique)
                if passport_full:
                    # Passport bo'yicha topish
                    person, created = Person.objects.update_or_create(
                        passport=passport_full,
                        defaults=person_data
                    )
                elif pinfl:
                    # PINFL bo'yicha topish (PINFL unique)
                    person, created = Person.objects.update_or_create(
                        pinfl=pinfl,
                        defaults=person_data
                    )
                else:
                    # Passport ham, PINFL ham bo'lmasa - yangi person yaratish
                    # Lekin bu holat kam uchraydi
                    person = Person.objects.create(**person_data)
                    created = True

                # IKKINCHI: Rasmni yuklash (Person ID kerak bo'lgani uchun keyin)
                photo_saved = False

                # 1. Excel ichida embed qilingan rasm
                if index in images_dict:
                    try:
                        print(f"  📸 Qator {index + 2}: Rasm topildi, yuklanmoqda...")
                        img_bytes = images_dict[index]
                        img = Image.open(io.BytesIO(img_bytes))

                        # Rasm formatini aniqlash
                        original_format = img.format if img.format else 'JPEG'

                        # Ruxsat etilgan formatlar
                        allowed_formats = ['JPEG', 'JPG', 'PNG', 'WEBP', 'GIF']

                        if original_format.upper() not in allowed_formats:
                            print(f"  ⚠️  Noma'lum format ({original_format}), JPEG'ga aylantirilmoqda...")
                            original_format = 'JPEG'

                        # Format bo'yicha sozlash
                        output = io.BytesIO()
                        save_format = original_format.upper()

                        if save_format in ('JPEG', 'JPG'):
                            # JPEG uchun RGB kerak
                            if img.mode in ('RGBA', 'LA', 'P'):
                                img = img.convert('RGB')
                            img.save(output, format='JPEG', quality=85, optimize=True)
                            file_ext = 'jpg'
                        elif save_format == 'PNG':
                            # PNG RGBA'ni qo'llab-quvvatlaydi
                            if img.mode == 'P':
                                img = img.convert('RGBA')
                            img.save(output, format='PNG', optimize=True)
                            file_ext = 'png'
                        elif save_format == 'WEBP':
                            # WEBP RGBA'ni qo'llab-quvvatlaydi
                            img.save(output, format='WEBP', quality=85, method=6)
                            file_ext = 'webp'
                        elif save_format == 'GIF':
                            # GIF P yoki RGB bo'lishi kerak
                            if img.mode not in ('P', 'RGB', 'RGBA'):
                                img = img.convert('RGB')
                            img.save(output, format='GIF', optimize=True)
                            file_ext = 'gif'
                        else:
                            # Default JPEG
                            if img.mode in ('RGBA', 'LA', 'P'):
                                img = img.convert('RGB')
                            img.save(output, format='JPEG', quality=85)
                            file_ext = 'jpg'

                        output.seek(0)

                        # Person ID bilan fayl nomi yaratish
                        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                        filename = f"person_{person.id}_{timestamp}.{file_ext}"
                        person.photo.save(filename, ContentFile(output.read()), save=True)
                        photo_saved = True
                        print(f"  ✅ Rasm saqlandi: {filename} (Format: {save_format}, Person ID: {person.id})")
                    except Exception as e:
                        error_msg = f"Qator {index + 2}: Rasmni saqlab bo'lmadi: {str(e)}"
                        warnings.append(error_msg)
                        print(f"  ❌ {error_msg}")
                else:
                    print(f"  ℹ️  Qator {index + 2}: Rasm yo'q (Person ID: {person.id})")

                # 2. URL orqali rasm yuklash (agar Excel'da rasm bo'lmasa)
                if not photo_saved and photo_url:
                    try:
                        print(f"  🌐 Qator {index + 2}: URL dan rasm yuklanmoqda...")
                        parsed = urlparse(photo_url)
                        if parsed.scheme in ['http', 'https']:
                            response = requests.get(photo_url, timeout=10)
                            if response.status_code == 200:
                                img = Image.open(io.BytesIO(response.content))

                                # Rasm formatini aniqlash
                                original_format = img.format if img.format else 'JPEG'

                                # Ruxsat etilgan formatlar
                                allowed_formats = ['JPEG', 'JPG', 'PNG', 'WEBP', 'GIF']

                                if original_format.upper() not in allowed_formats:
                                    print(f"  ⚠️  Noma'lum format ({original_format}), JPEG'ga aylantirilmoqda...")
                                    original_format = 'JPEG'

                                # Format bo'yicha sozlash
                                output = io.BytesIO()
                                save_format = original_format.upper()

                                if save_format in ('JPEG', 'JPG'):
                                    if img.mode in ('RGBA', 'LA', 'P'):
                                        img = img.convert('RGB')
                                    img.save(output, format='JPEG', quality=85, optimize=True)
                                    file_ext = 'jpg'
                                elif save_format == 'PNG':
                                    if img.mode == 'P':
                                        img = img.convert('RGBA')
                                    img.save(output, format='PNG', optimize=True)
                                    file_ext = 'png'
                                elif save_format == 'WEBP':
                                    img.save(output, format='WEBP', quality=85, method=6)
                                    file_ext = 'webp'
                                elif save_format == 'GIF':
                                    if img.mode not in ('P', 'RGB', 'RGBA'):
                                        img = img.convert('RGB')
                                    img.save(output, format='GIF', optimize=True)
                                    file_ext = 'gif'
                                else:
                                    if img.mode in ('RGBA', 'LA', 'P'):
                                        img = img.convert('RGB')
                                    img.save(output, format='JPEG', quality=85)
                                    file_ext = 'jpg'

                                output.seek(0)

                                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                                filename = f"person_{person.id}_{timestamp}_url.{file_ext}"
                                person.photo.save(filename, ContentFile(output.read()), save=True)
                                photo_saved = True
                                print(f"  ✅ URL rasm saqlandi: {filename} (Format: {save_format})")
                    except Exception as e:
                        warnings.append(f"Qator {index + 2}: URL dan rasm yuklanmadi: {str(e)[:100]}")
                        print(f"  ❌ URL xato: {str(e)[:100]}")

                # 3. Face encoding yaratish (agar rasm saqlangan bo'lsa)
                if photo_saved and person.photo:
                    try:
                        print(f"  🔍 Qator {index + 2}: Face encoding yaratilmoqda...")
                        import face_recognition
                        image = face_recognition.load_image_file(person.photo.path)
                        encodings = face_recognition.face_encodings(image)

                        if encodings:
                            person.face_encoding = encodings[0].tolist()
                            person.save()
                            print(f"  ✅ Face encoding yaratildi (Person ID: {person.id})")
                        else:
                            warnings.append(f"Qator {index + 2}: Rasmda yuz topilmadi")
                            print(f"  ⚠️  Rasmda yuz topilmadi")
                    except Exception as e:
                        warnings.append(f"Qator {index + 2}: Face encoding yaratib bo'lmadi: {str(e)[:100]}")
                        print(f"  ❌ Face encoding xato: {str(e)[:100]}")

                # 4. Admin User yaratish
                try:
                    print(f"  👤 Qator {index + 2}: Admin User yaratilmoqda...")
                    from django.contrib.auth.models import User

                    # USERNAME: passport (V1 birlashgan format, masalan: AD3145734)
                    if passport_full:
                        username = passport_full
                    else:
                        # Fallback - agar passport bo'lmasa, person ID ishlatamiz
                        username = f"person_{person.id}"

                    # PASSWORD: Tug'ilgan kun (DDMMYYYY formatda, masalan: 29021988)
                    if birth_date:
                        # birth_date - date obyekti (masalan: 1988-02-29)
                        password = str(birth_date.strftime('%d%m%Y'))  # String'ga aylantirish
                    else:
                        # Fallback - agar tug'ilgan kun bo'lmasa, default password
                        password = 'password123'

                    # XAVFSIZLIK: Password string ekanligini ta'minlash
                    password = str(password) if password else 'password123'

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
                        print(f"  ✅ Admin User yaratildi: {username} / password: {password}")
                    else:
                        # Agar user allaqachon mavjud bo'lsa, password'ni yangilash
                        user.set_password(password)
                        user.is_staff = True
                        user.is_superuser = True
                        user.is_active = True
                        user.save()
                        print(f"  🔄 Admin User yangilandi: {username} / password: {password}")
                except Exception as e:
                    warnings.append(f"Qator {index + 2}: Admin User yaratib bo'lmadi: {str(e)[:100]}")
                    print(f"  ❌ Admin User xato: {str(e)[:100]}")

                success_count += 1
                print(f"   ✅ Muvaffaqiyatli saqlandi!\n")

            except Exception as e:
                error_msg = f"Qator {index + 2}: {str(e)}"
                errors.append(error_msg)
                error_count += 1
                print(f"   ❌ XATOLIK: {error_msg}")
                print(f"   📋 Qator ma'lumotlari: {dict(row)}\n")

                # Agar juda ko'p xatolik bo'lsa, to'xtatish (cheksiz loop oldini olish)
                if error_count > 50:
                    print(f"\n⚠️  50 tadan ortiq xatolik! Import to'xtatildi.")
                    break
                continue

        # Temp faylni o'chirish
        try:
            import os
            os.remove(temp_path)
        except:
            pass

        print(f"\n✅ Import yakunlandi:")
        print(f"   Jami: {len(df)}")
        print(f"   Muvaffaqiyatli: {success_count}")
        print(f"   Xatoliklar: {error_count}")
        print(f"   Ogohlantirishlar: {len(warnings)}")

        return JsonResponse({
            'success': True,
            'message': 'Import yakunlandi',
            'total_count': len(df),
            'success_count': success_count,
            'error_count': error_count,
            'errors': errors[:20],
            'warnings': warnings[:20],
            'images_found': len(images_dict)
        })

    except Exception as e:
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


# =====================================================
# UNIVERSAL CRUD API
# =====================================================

@csrf_exempt
def person_crud_api(request):
    """
    UNIVERSAL CRUD API - Bitta endpoint barcha CRUD operatsiyalari uchun

    Endpoint: POST /api/person/

    Operatsiya "action" field orqali aniqlanadi:
    - action: "list"   → Barcha personlarni olish
    - action: "get"    → Bitta personni olish (id kerak)
    - action: "create" → Yangi person yaratish
    - action: "update" → Person yangilash (id kerak)
    - action: "delete" → Person o'chirish (id kerak)

    Request Body:
    {
        "action": "list|get|create|update|delete",
        "id": 127,  // get, update, delete uchun kerak
        "data": {}, // create, update uchun
        "limit": 50,    // list uchun
        "offset": 0,    // list uchun
        "search": ""    // list uchun
    }
    """
    from .models import Person

    try:
        # Parse request
        if request.method == 'POST':
            try:
                body = json.loads(request.body)
            except Exception as e:
                return JsonResponse({
                    'success': False,
                    'error': f'JSON parse xatosi: {str(e)}',
                    'received_body': request.body.decode('utf-8')[:200]
                }, status=400)
        elif request.method == 'GET':
            # GET method uchun query params
            action = request.GET.get('action', '').lower()
            if not action:
                return JsonResponse({
                    'success': False,
                    'error': 'action parametri kerak (list, get, create, update, delete)',
                    'method': request.method
                }, status=400)
            body = {
                'action': action,
                'id': request.GET.get('id'),
                'limit': request.GET.get('limit', 50),
                'offset': request.GET.get('offset', 0),
                'search': request.GET.get('search', '')
            }
        else:
            return JsonResponse({
                'success': False,
                'error': f'Faqat POST yoki GET metodlari qo\'llab-quvvatlanadi. Sizniki: {request.method}'
            }, status=405)

        action = body.get('action', '').lower()
        if not action:
            return JsonResponse({
                'success': False,
                'error': 'action maydoni bo\'sh. Foydalanish mumkin: list, get, create, update, delete',
                'received_body': body
            }, status=400)
        
        person_id = body.get('id')
        print(f"\n🔔 Person CRUD API chaqirildi - action: {action}, id: {person_id}")
        data = body.get('data', {})

        # ==================== LIST - Barcha personlar ====================
        if action == 'list':
            limit = int(body.get('limit', 50))
            offset = int(body.get('offset', 0))
            search = body.get('search', '').strip()

            # Base query
            persons = Person.objects.all()

            # Search filter
            if search:
                from django.db.models import Q
                persons = persons.filter(
                    Q(first_name__icontains=search) |
                    Q(last_name__icontains=search) |
                    Q(middle_name__icontains=search) |
                    Q(passport__icontains=search) |  # V1 birlashgan passport
                    Q(pinfl__icontains=search)
                )

            total_count = persons.count()
            persons = persons.order_by('-id')[offset:offset + limit]

            # Serialize
            persons_data = []
            for person in persons:
                persons_data.append({
                    'id': person.id,
                    'first_name': person.first_name,
                    'last_name': person.last_name,
                    'middle_name': person.middle_name,
                    'full_name': person.full_name,
                    'passport_series': person.passport_series,
                    'passport_number': person.passport_number,
                    'birth_date': person.birth_date.strftime('%Y-%m-%d') if person.birth_date else None,
                    'pinfl': person.pinfl,
                    'position': person.position,
                    'district': person.district,
                    'department': person.department,
                    'phone_number': person.phone_number,
                    'mahalla': person.mahalla,
                    'jeton_series': person.jeton_series,
                    'has_photo': bool(person.photo),
                    'photo_url': request.build_absolute_uri(person.photo.url) if person.photo else None,
                    'has_face_encoding': bool(person.face_encoding),
                    'registered_at': person.registered_at.strftime('%Y-%m-%d %H:%M:%S'),
                })

            return JsonResponse({
                'success': True,
                'action': 'list',
                'total_count': total_count,
                'limit': limit,
                'offset': offset,
                'data': persons_data
            })

        # ==================== GET - Bitta person ====================
        elif action == 'get':
            if not person_id:
                return JsonResponse({
                    'success': False,
                    'error': 'id maydoni kerak'
                }, status=400)

            try:
                person = Person.objects.get(id=person_id)
            except Person.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'error': f'Person ID {person_id} topilmadi'
                }, status=404)

            return JsonResponse({
                'success': True,
                'action': 'get',
                'data': {
                    'id': person.id,
                    'first_name': person.first_name,
                    'last_name': person.last_name,
                    'middle_name': person.middle_name,
                    'full_name': person.full_name,
                    'passport_series': person.passport_series,
                    'passport_number': person.passport_number,
                    'birth_date': person.birth_date.strftime('%Y-%m-%d') if person.birth_date else None,
                    'pinfl': person.pinfl,
                    'position': person.position,
                    'district': person.district,
                    'department': person.department,
                    'phone_number': person.phone_number,
                    'mahalla': person.mahalla,
                    'jeton_series': person.jeton_series,
                    'has_photo': bool(person.photo),
                    'photo_url': request.build_absolute_uri(person.photo.url) if person.photo else None,
                    'has_face_encoding': bool(person.face_encoding),
                    'registered_at': person.registered_at.strftime('%Y-%m-%d %H:%M:%S'),
                }
            })

        # ==================== CREATE - Yangi person ====================
        elif action == 'create':
            print("📥 CREATE action chaqirildi")
            print(f"📥 Qabul qilingan data: {data}")
            
            try:
                # Validation
                if not data.get('first_name') or not data.get('last_name'):
                    return JsonResponse({
                        'success': False,
                        'error': 'first_name va last_name majburiy'
                    }, status=400)

                # PINFL unique tekshirish
                pinfl_value = data.get('pinfl', '').strip()
                if pinfl_value:
                    existing_person = Person.objects.filter(pinfl=pinfl_value).first()
                    if existing_person:
                        return JsonResponse({
                            'success': False,
                            'error': f'Bu PINFL ({pinfl_value}) allaqachon "{existing_person.full_name}" foydalanuvchisiga tegishli'
                        }, status=400)
                
                # PASSPORT unique tekshirish (V1 birlashgan format)
                passport_series = data.get('passport_series', '').strip()
                passport_number = data.get('passport_number', '').strip()
                passport_full = None
                if passport_series and passport_number:
                    passport_full = f"{passport_series.upper()}{passport_number}"
                    existing_person = Person.objects.filter(
                        passport=passport_full
                    ).first()
                    if existing_person:
                        return JsonResponse({
                            'success': False,
                            'error': f'Bu passport ({passport_full}) allaqachon "{existing_person.full_name}" foydalanuvchisiga tegishli'
                        }, status=400)

                # Create person object (V1 format)
                person = Person()
                person.first_name = data.get('first_name', '').strip()
                person.last_name = data.get('last_name', '').strip()
                person.middle_name = data.get('middle_name', '').strip() or None
                person.passport = passport_full  # V1 birlashgan format
                person.pinfl = pinfl_value or None
                person.position = data.get('position', '').strip() or None
                person.tuman = data.get('district', '').strip() or None  # V1 da tuman
                person.department = data.get('department', '').strip() or None
                person.phone = data.get('phone_number', '').strip() or None  # V1 da phone
                person.mahalla = data.get('mahalla', '').strip() or None
                person.badge_number = data.get('jeton_series', '').strip() or None  # V1 da badge_number

                # Birth date
                if data.get('birth_date'):
                    try:
                        person.birth_date = datetime.strptime(data['birth_date'], '%Y-%m-%d').date()
                    except:
                        return JsonResponse({
                            'success': False,
                            'error': 'birth_date formati noto\'g\'ri. Masalan: 1990-01-15'
                        }, status=400)

                # Photo upload
                # if data.get('photo'):
                #     try:
                #         print("📸 Rasm yuklanmoqda...")
                #         if ',' in data['photo']:
                #             header, encoded = data['photo'].split(',', 1)
                #             # Check if it's base64
                #             if 'base64' not in header:
                #                 return JsonResponse({
                #                     'success': False,
                #                     'error': 'Rasm base64 formatida emas'
                #                 }, status=400)
                #         else:
                #             encoded = data['photo']

                #         image_bytes = base64.b64decode(encoded)
                #         # Rasm hajmini tekshirish (max 5MB)
                #         if len(image_bytes) > 5 * 1024 * 1024:
                #             return JsonResponse({
                #                 'success': False,
                #                 'error': 'Rasm hajmi 5MB dan oshmasligi kerak'
                #             }, status=400)
                        
                #         timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                #         filename = f"person_{timestamp}.jpg"
                #         person.photo.save(filename, ContentFile(image_bytes))
                #         print(f"✅ Rasm saqlandi: {filename}")

                #         # Face encoding
                #         try:
                #             import face_recognition
                #             image = face_recognition.load_image_file(person.photo.path)
                #             encodings = face_recognition.face_encodings(image)
                #             if encodings:
                #                 person.face_encoding = encodings[0].tolist()
                #                 print("✅ Yuz encoding qilindi")
                #             else:
                #                 print("⚠️ Rasmda yuz aniqlanmadi")
                #         except Exception as face_error:
                #             print(f"⚠️ Yuz encoding xatosi: {face_error}")
                #             # Face encoding xatosi person yaratishga to'sqinlik qilmasin
                            
                #     except Exception as e:
                #         print(f"❌ Rasm yuklash xatosi: {str(e)}")
                #         return JsonResponse({
                #             'success': False,
                #             'error': f'Rasmni yuklashda xatolik: {str(e)}'
                #         }, status=400)

                try:
                    person.save()
                    print(f"✅ Person saqlandi: ID={person.id}, Ism={person.full_name}")
                except Exception as save_error:
                    print(f"❌ Saqlash xatosi: {save_error}")
                    # Rasmni o'chirish agar saqlanmagan bo'lsa
                    if person.photo and hasattr(person.photo, 'path'):
                        try:
                            os.remove(person.photo.path)
                        except:
                            pass
                    raise save_error

                return JsonResponse({
                    'success': True,
                    'action': 'create',
                    'message': f'{person.full_name} muvaffaqiyatli yaratildi',
                    'data': {
                        'id': person.id,
                        'full_name': person.full_name,
                        'pinfl': person.pinfl,
                        'passport': f'{person.passport_series} {person.passport_number}'.strip() if person.passport_series else None
                    }
                }, status=201)
                
            except Exception as e:
                print(f"❌ Umumiy xato: {str(e)}")
                return JsonResponse({
                    'success': False,
                    'error': f'Server xatosi: {str(e)}'
                }, status=500)
            

        # ==================== UPDATE - Person yangilash ====================
        elif action == 'update':
            if not person_id:
                return JsonResponse({
                    'success': False,
                    'error': 'id maydoni kerak'
                }, status=400)

            try:
                person = Person.objects.get(id=person_id)
            except Person.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'error': f'Person ID {person_id} topilmadi'
                }, status=404)

            # Update fields
            if 'first_name' in data:
                person.first_name = data['first_name'].strip()
            if 'last_name' in data:
                person.last_name = data['last_name'].strip()
            if 'middle_name' in data:
                person.middle_name = data['middle_name'].strip() or None
            # Passport yangilash (V1 birlashgan format)
            if 'passport_series' in data or 'passport_number' in data:
                passport_series = data.get('passport_series', '').strip()
                passport_number = data.get('passport_number', '').strip()
                if passport_series and passport_number:
                    person.passport = f"{passport_series.upper()}{passport_number}"
            if 'pinfl' in data:
                person.pinfl = data['pinfl'].strip() or None
            if 'position' in data:
                person.position = data['position'].strip() or None
            if 'district' in data:
                person.tuman = data['district'].strip() or None  # V1 da tuman
            if 'department' in data:
                person.department = data['department'].strip() or None
            if 'phone_number' in data:
                person.phone = data['phone_number'].strip() or None  # V1 da phone
            if 'mahalla' in data:
                person.mahalla = data['mahalla'].strip() or None
            if 'jeton_series' in data:
                person.badge_number = data['jeton_series'].strip() or None  # V1 da badge_number

            # Birth date
            if 'birth_date' in data:
                try:
                    person.birth_date = datetime.strptime(data['birth_date'], '%Y-%m-%d').date()
                except:
                    return JsonResponse({
                        'success': False,
                        'error': 'birth_date formati noto\'g\'ri'
                    }, status=400)

            # Photo update
            if 'photo' in data and data['photo']:
                try:
                    # Delete old
                    if person.photo:
                        if os.path.exists(person.photo.path):
                            os.remove(person.photo.path)
                        person.photo.delete(save=False)

                    # Upload new
                    if ',' in data['photo']:
                        header, encoded = data['photo'].split(',', 1)
                    else:
                        encoded = data['photo']

                    image_bytes = base64.b64decode(encoded)
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    filename = f"person_{person.id}_{timestamp}.jpg"
                    person.photo.save(filename, ContentFile(image_bytes))

                    # Regenerate encoding
                    import face_recognition
                    image = face_recognition.load_image_file(person.photo.path)
                    encodings = face_recognition.face_encodings(image)
                    if encodings:
                        person.face_encoding = encodings[0].tolist()
                    else:
                        person.face_encoding = None

                except Exception as e:
                    return JsonResponse({
                        'success': False,
                        'error': f'Rasmni yangilashda xatolik: {str(e)}'
                    }, status=400)

            person.save()

            return JsonResponse({
                'success': True,
                'action': 'update',
                'message': f'{person.full_name} muvaffaqiyatli yangilandi',
                'data': {
                    'id': person.id,
                    'full_name': person.full_name
                }
            })

        # ==================== DELETE - Person o'chirish ====================
        elif action == 'delete':
            if not person_id:
                return JsonResponse({
                    'success': False,
                    'error': 'id maydoni kerak'
                }, status=400)

            try:
                person = Person.objects.get(id=person_id)
            except Person.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'error': f'Person ID {person_id} topilmadi'
                }, status=404)

            full_name = person.full_name

            # Delete photo
            if person.photo:
                if os.path.exists(person.photo.path):
                    os.remove(person.photo.path)

            person.delete()

            return JsonResponse({
                'success': True,
                'action': 'delete',
                'message': f'{full_name} muvaffaqiyatli o\'chirildi'
            })

        # ==================== INVALID ACTION ====================
        else:
            return JsonResponse({
                'success': False,
                'error': 'Noto\'g\'ri action. Foydalanish mumkin: list, get, create, update, delete',
                'received_action': action,
                'received_action_type': str(type(action)),
                'received_body': body
            }, status=400)

    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Noto\'g\'ri JSON format'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)