from django.urls import path
from .api.views import (
    LoginView, CheckSMSCodeView, SMSServiceStatusView,
    UserDetailsView, UserDetailsByIdView, FAQListView, UpdateTelegramChatIdView,
    HealthCheckView,
    SbpBalanceQrView,
    SbpIntentStatusView,
    SbpWebhookView,
    SbpConfirmByTrxView,
    AlfaGetOrderStatusExtendedView,
    OwnerTopUpMasterBalanceView,
    MasterAvailableBalanceView,
    MasterWithdrawalCreateView,
    MasterWithdrawalListView,
    UserDeviceListCreateView,
    UserDeviceDetailView,
)

urlpatterns = [
    
    # Login (SMS kod yuborish)
    path('login/', LoginView.as_view(), name='login'),
    
    # SMS kod tekshirish va token berish
    path('check-sms-code/', CheckSMSCodeView.as_view(), name='check_sms_code'),
    
    # SMS servis statusini tekshirish
    path('sms-status/', SMSServiceStatusView.as_view(), name='sms_status'),
    
    # User details endpoints
    path('user/', UserDetailsView.as_view(), name='user_details'),
    path('user/<int:user_id>/', UserDetailsByIdView.as_view(), name='user_details_by_id'),
    
    # Telegram Chat ID update endpoint
    path('update-telegram-chat-id/', UpdateTelegramChatIdView.as_view(), name='update_telegram_chat_id'),
    
    # FAQ endpoints
    path('faq/', FAQListView.as_view(), name='faq_list'),

    # Пополнение: QR СБП (статическая ссылка НСПК)
    path('balance/sbp-qr/', SbpBalanceQrView.as_view(), name='balance_sbp_qr'),
    path('balance/sbp-intent/<uuid:intent_id>/', SbpIntentStatusView.as_view(), name='balance_sbp_intent'),
    path('balance/sbp-webhook/', SbpWebhookView.as_view(), name='balance_sbp_webhook'),
    path('balance/sbp-confirm-by-trx/', SbpConfirmByTrxView.as_view(), name='balance_sbp_confirm_by_trx'),
    path('balance/alfa-order-status/', AlfaGetOrderStatusExtendedView.as_view(), name='balance_alfa_order_status'),
    path('balance/master-topup/', OwnerTopUpMasterBalanceView.as_view(), name='balance_master_topup'),
    path('balance/master-available/', MasterAvailableBalanceView.as_view(), name='balance_master_available'),
    path('balance/master-withdraw/', MasterWithdrawalCreateView.as_view(), name='balance_master_withdraw'),
    path('balance/master-withdrawals/', MasterWithdrawalListView.as_view(), name='balance_master_withdrawals'),

    # Push devices
    path('devices/', UserDeviceListCreateView.as_view(), name='user_devices'),
    path('devices/<int:device_id>/', UserDeviceDetailView.as_view(), name='user_device_detail'),
]