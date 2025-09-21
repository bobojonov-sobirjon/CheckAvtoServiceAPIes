from django.urls import path
from .views import LoginView, CheckSMSCodeView

urlpatterns = [
    # Login (SMS kod yuborish)
    path('login/', LoginView.as_view(), name='login'),
    
    # SMS kod tekshirish va token berish
    path('check-sms-code/', CheckSMSCodeView.as_view(), name='check_sms_code'),
]