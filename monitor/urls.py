from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    # Auth
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    
    # Custom OTP Auth Flow
    path('password-reset/', views.password_reset_view, name='password_reset'),
    path('verify-otp/', views.verify_otp, name='verify_otp'),
    path('password-reset-confirm-otp/', views.password_reset_confirm_otp, name='password_reset_confirm_otp'),
    path('password-reset-complete/', auth_views.PasswordResetCompleteView.as_view(
        template_name='auth/password_reset_complete.html'
    ), name='password_reset_complete'),
    
    # Extra Menus
    path('hydro-ai/', views.hydro_ai_chat, name='hydro_ai'),
    path('beli-kit/', views.beli_kit, name='beli_kit'),


    # Utama (Level 1: Kebun)
    path('', views.daftar_kebun, name='daftar_kebun'),
    
    # Level 2: Tanaman (Berdasarkan ID Kebun)
    path('kebun/<int:kebun_id>/', views.daftar_tanaman, name='daftar_tanaman'),
    
    # Level 3: Rak (Berdasarkan ID Tanaman)
    path('tanaman/<int:tanaman_id>/', views.daftar_rak, name='daftar_rak'),
    
    # Level 4: Monitoring (Berdasarkan ID Rak)
    path('rak/<int:rak_id>/', views.monitoring_rak, name='monitoring_rak'),
    
    # AJAX Endpoints
    path('rak/<int:rak_id>/deepsleep/', views.update_deepsleep_ajax, name='update_deepsleep_ajax'),
    path('rak/<int:rak_id>/interval/', views.update_interval, name='update_interval'),
    path('rak/<int:rak_id>/edit/', views.edit_rak, name='edit_rak'),
    
    # Fungsi Hapus
    path('hapus/<str:tipe>/<int:item_id>/', views.hapus_item, name='hapus'),
]