# emotion_app/urls.py - Faqat login uchun kerakli URLlar

from django.urls import path
from .views import (
    face_login,
    dashboard,
    detect_face,
    face_login_auth,
    passport_login_auth,
    upload_login_photo,
    get_current_user,
    logout_view,
    upload_excel,
    upload_excel_page,
    get_statistics,
    get_person_statistics,
    get_login_logs
)

urlpatterns = [
    # === SAHIFALAR ===
    path('', face_login, name='face-login'),
    path('dashboard/', dashboard, name='dashboard'),
    path('upload-excel/', upload_excel_page, name='upload-excel-page'),

    # === LOGIN API ===
    path('api/face-detect/', detect_face, name='face-detect'),
    path('api/face-login/', face_login_auth, name='face-login-auth'),
    path('api/passport-login/', passport_login_auth, name='passport-login-auth'),
    path('api/upload-login-photo/', upload_login_photo, name='upload-login-photo'),

    # === USER API ===
    path('api/current-user/', get_current_user, name='current-user'),
    path('api/logout/', logout_view, name='logout'),

    # === EXCEL IMPORT API ===
    path('api/upload-excel/', upload_excel, name='upload-excel'),

    # === STATISTICS API ===
    path('api/statistics/', get_statistics, name='statistics'),
    path('api/statistics/<int:person_id>/', get_person_statistics, name='person-statistics'),

    # === LOGIN LOGS API ===
    path('api/login-logs/', get_login_logs, name='login-logs'),
]
