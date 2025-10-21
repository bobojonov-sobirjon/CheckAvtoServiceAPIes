from django.urls import path
from .views import LoginView, CheckSMSCodeView, SMSServiceStatusView, UserDetailsView

urlpatterns = [
    # Login (SMS kod yuborish)
    path('login/', LoginView.as_view(), name='login'),
    
    # SMS kod tekshirish va token berish
    path('check-sms-code/', CheckSMSCodeView.as_view(), name='check_sms_code'),
    
    # SMS servis statusini tekshirish
    path('sms-status/', SMSServiceStatusView.as_view(), name='sms_status'),
    
    # User details endpoints
    path('user/', UserDetailsView.as_view(), name='user_details'),
]