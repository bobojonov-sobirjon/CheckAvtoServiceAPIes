import uuid
from datetime import timedelta
from decimal import Decimal, ROUND_HALF_UP
from zoneinfo import ZoneInfo

from django.conf import settings
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample
from drf_spectacular.types import OpenApiTypes
from .serializers import (
    PhoneNumberSerializer,
    IdentifierSerializer,
    SMSVerificationSerializer,
    UserSerializer,
    TokenResponseSerializer,
    SMSResponseSerializer,
    UserDetailsSerializer,
    UserUpdateSerializer,
    FAQSerializer,
    TelegramChatIdSerializer,
    SbpBalanceQrSerializer,
    SbpWebhookSerializer,
    SbpConfirmByTrxSerializer,
    AlfaOrderStatusExtendedSerializer,
)
from .services import SMSService
from .models import CustomUser, FAQ, SbpPaymentIntent, UserBalance, AlfaSbpTemplateSnapshot
from .sbp_qr import pay_url_to_qr_png_base64
from .alfa_orders import post_order_status_extended, is_paid_status
from .alfa_sbp_templates import (
    post_template_json,
    alfa_sbp_templates_configured,
    alfa_sbp_gateway_ready,
    alfa_template_gateway_failed,
)


class HealthCheckView(APIView):
    """Test endpoint for checking CORS and server status"""
    permission_classes = [AllowAny]
    
    @extend_schema(
        summary="Health check endpoint",
        description="Simple endpoint to test CORS and server connectivity",
        tags=['System'],
        responses={
            200: {
                'type': 'object',
                'properties': {
                    'status': {'type': 'string'},
                    'message': {'type': 'string'},
                    'cors_enabled': {'type': 'boolean'}
                }
            }
        }
    )
    def get(self, request):
        """Health check"""
        return Response({
            'status': 'ok',
            'message': 'Server is running',
            'cors_enabled': True,
            'method': 'GET'
        }, status=status.HTTP_200_OK)
    
    def post(self, request):
        """Health check POST"""
        return Response({
            'status': 'ok',
            'message': 'Server is running',
            'cors_enabled': True,
            'method': 'POST',
            'data_received': request.data
        }, status=status.HTTP_200_OK)


class LoginView(APIView):
    """
    Вход по email или номеру телефона (отправка SMS кода)
    """
    permission_classes = [AllowAny]
    
    @extend_schema(
        summary="Отправка кода подтверждения",
        description="Отправка 4-значного кода подтверждения на номер телефона (SMS) или email. Если пользователь не найден, создается новый пользователь автоматически. Параметр 'role' (Driver, Master или Owner) обязателен.",
        request=IdentifierSerializer,
        responses={
            200: {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean', 'example': True},
                    'message': {'type': 'string', 'example': 'Код подтверждения отправлен на email'},
                    'identifier': {'type': 'string', 'example': 'user@example.com'},
                    'identifier_type': {'type': 'string', 'example': 'email'},
                    'phone': {'type': 'string', 'example': '998901234567', 'description': 'Номер телефона (только для phone)'},
                    'email': {'type': 'string', 'example': 'user@example.com', 'description': 'Email адрес (только для email)'},
                    'user_exists': {'type': 'boolean', 'example': True},
                    'sms_code': {'type': 'string', 'example': '1234', 'description': 'SMS код подтверждения'}
                }
            },
            400: {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean', 'example': False},
                    'errors': {'type': 'object'}
                }
            },
            500: {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean', 'example': False},
                    'error': {'type': 'string'}
                }
            }
        },
        tags=['Authentication']
    )
    def post(self, request):
        """Вход - отправка кода подтверждения на телефон или email"""
        serializer = IdentifierSerializer(data=request.data, context={'request': request})
        
        if not serializer.is_valid():
            return Response({
                'success': False,
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        identifier_data = serializer.validated_data['identifier']
        identifier = identifier_data['value']
        identifier_type = identifier_data['type']
        role = serializer.validated_data.get('role')
        
        # Отправка кода через SMS сервис
        result = SMSService.send_sms_code(identifier, identifier_type, role)
        
        if result['success']:
            # Добавление информации о существовании пользователя
            response_data = {
                'success': True,
                'message': result['message'],
                'identifier': result['identifier'],
                'identifier_type': result['identifier_type'],
                'phone': result.get('phone'),
                'email': result.get('email'),
                'user_exists': result.get('user_exists', False),
                'sms_code': result.get('sms_code')  # Добавляем SMS код в response
            }
            return Response(response_data, status=result['status_code'])
        else:
            return Response({
                'success': False,
                'error': result['error']
            }, status=result['status_code'])


class CheckSMSCodeView(APIView):
    """
    Проверка SMS кода и выдача токена
    """
    permission_classes = [AllowAny]
    
    @extend_schema(
        summary="Проверка SMS кода",
        description="Проверка SMS кода и получение JWT токена. Параметр 'role' (Driver, Master или Owner) обязателен.",
        request=SMSVerificationSerializer,
        responses={
            200: TokenResponseSerializer,
            400: {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean', 'example': False},
                    'errors': {'type': 'object'},
                    'error': {'type': 'string'}
                }
            },
            500: {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean', 'example': False},
                    'error': {'type': 'string'}
                }
            }
        },
        tags=['Authentication']
    )
    def post(self, request):
        """Проверка SMS кода"""
        serializer = SMSVerificationSerializer(data=request.data, context={'request': request})
        
        if not serializer.is_valid():
            return Response({
                'success': False,
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        identifier_data = serializer.validated_data['identifier']
        identifier = identifier_data['value']
        identifier_type = identifier_data['type']
        sms_code = serializer.validated_data['sms_code']
        role = serializer.validated_data.get('role')
        
        # Проверка кода через SMS сервис
        result = SMSService.verify_sms_code(identifier, sms_code, identifier_type, role)
        
        if result['success']:
            # Сериализация данных пользователя
            user_serializer = UserSerializer(result['user'], context={'request': request})
            
            response_data = {
                'success': True,
                'message': result['message'],
                'user': user_serializer.data,
                'user_created': result.get('user_created', False),
                'tokens': result['tokens']
            }
            
            return Response(response_data, status=result['status_code'])
        else:
            return Response({
                'success': False,
                'error': result['error']
            }, status=result['status_code'])


class SMSServiceStatusView(APIView):
    """
    Проверка статуса SMS сервиса и баланса
    """
    permission_classes = [AllowAny]
    
    @extend_schema(
        summary="Проверка статуса SMS сервиса",
        description="Проверка статуса SMS сервиса SMSC.ru и баланса",
        responses={
            200: {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean', 'example': True},
                    'service': {'type': 'string', 'example': 'SMSC.ru'},
                    'balance': {'type': 'number', 'example': 150.50},
                    'currency': {'type': 'string', 'example': 'RUB'},
                    'status': {'type': 'string', 'example': 'active'}
                }
            },
            400: {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean', 'example': False},
                    'error': {'type': 'string'}
                }
            }
        },
        tags=['SMS Service']
    )
    def get(self, request):
        """Проверка статуса SMS сервиса"""
        balance_info = SMSService.check_smsc_balance()
        
        if balance_info['success']:
            return Response({
                'success': True,
                'service': 'SMSC.ru',
                'balance': balance_info['balance'],
                'currency': balance_info['currency'],
                'status': 'active' if balance_info['balance'] > 0 else 'low_balance'
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                'success': False,
                'error': balance_info['error']
            }, status=status.HTTP_400_BAD_REQUEST)


class UserDetailsView(APIView):
    """
    Получение и обновление информации о текущем пользователе
    """
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    
    @extend_schema(
        summary="Получение информации о пользователе",
        description="Получение детальной информации о текущем авторизованном пользователе",
        responses={
            200: UserDetailsSerializer,
            401: {
                'type': 'object',
                'properties': {
                    'detail': {'type': 'string', 'example': 'Authentication credentials were not provided.'}
                }
            }
        },
        tags=['User Profile']
    )
    def get(self, request):
        """Получение информации о текущем пользователе"""
        user = request.user
        serializer = UserDetailsSerializer(user, context={'request': request})
        return Response({
            'success': True,
            'user': serializer.data
        }, status=status.HTTP_200_OK)
    
    @extend_schema(
        summary="Обновление информации о пользователе",
        description="Обновление информации о текущем пользователе. Поддерживает обновление всех полей, включая avatar (файл) и роль (группу).",
        request=UserUpdateSerializer,
        responses={
            200: {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean', 'example': True},
                    'message': {'type': 'string', 'example': 'Информация о пользователе успешно обновлена'},
                    'user': {'type': 'object'}
                }
            },
            400: {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean', 'example': False},
                    'errors': {'type': 'object'}
                }
            },
            401: {
                'type': 'object',
                'properties': {
                    'detail': {'type': 'string', 'example': 'Authentication credentials were not provided.'}
                }
            }
        },
        tags=['User Profile']
    )
    def put(self, request):
        """Полное обновление информации о пользователе"""
        user = request.user
        serializer = UserUpdateSerializer(user, data=request.data, partial=False, context={'request': request})
        
        if serializer.is_valid():
            serializer.save()
            # Возвращаем обновленные данные через UserDetailsSerializer
            detail_serializer = UserDetailsSerializer(user, context={'request': request})
            return Response({
                'success': True,
                'message': 'Информация о пользователе успешно обновлена',
                'user': detail_serializer.data
            }, status=status.HTTP_200_OK)
        
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)
    
    @extend_schema(
        summary="Частичное обновление информации о пользователе",
        description="Частичное обновление информации о текущем пользователе. Можно обновить только нужные поля. Поддерживает avatar (файл) и роль (группу).",
        request=UserUpdateSerializer,
        responses={
            200: {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean', 'example': True},
                    'message': {'type': 'string', 'example': 'Информация о пользователе успешно обновлена'},
                    'user': {'type': 'object'}
                }
            },
            400: {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean', 'example': False},
                    'errors': {'type': 'object'}
                }
            },
            401: {
                'type': 'object',
                'properties': {
                    'detail': {'type': 'string', 'example': 'Authentication credentials were not provided.'}
                }
            }
        },
        tags=['User Profile']
    )
    def patch(self, request):
        """Частичное обновление информации о пользователе"""
        user = request.user
        serializer = UserUpdateSerializer(user, data=request.data, partial=True, context={'request': request})
        
        if serializer.is_valid():
            serializer.save()
            # Возвращаем обновленные данные через UserDetailsSerializer
            detail_serializer = UserDetailsSerializer(user, context={'request': request})
            return Response({
                'success': True,
                'message': 'Информация о пользователе успешно обновлена',
                'user': detail_serializer.data
            }, status=status.HTTP_200_OK)
        
        return Response({
            'success': False,
            'errors': serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)


class FAQListView(APIView):
    """
    Получение списка всех FAQ (часто задаваемых вопросов)
    """
    permission_classes = [AllowAny]
    
    @extend_schema(
        summary="Получение списка FAQ",
        description="Получение списка всех активных FAQ. Доступно без авторизации.",
        responses={
            200: {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean', 'example': True},
                    'count': {'type': 'integer', 'example': 5},
                    'faqs': {
                        'type': 'array',
                        'items': {
                            'type': 'object',
                            'properties': {
                                'id': {'type': 'integer', 'example': 1},
                                'question': {'type': 'string', 'example': 'Как зарегистрироваться в системе?'},
                                'answer': {'type': 'string', 'example': 'Для регистрации...'},
                                'order': {'type': 'integer', 'example': 1},
                                'created_at': {'type': 'string', 'format': 'date-time'},
                                'updated_at': {'type': 'string', 'format': 'date-time'}
                            }
                        }
                    }
                }
            }
        },
        tags=['FAQ']
    )
    def get(self, request):
        """Получение всех активных FAQ"""
        faqs = FAQ.objects.filter(is_active=True)
        serializer = FAQSerializer(faqs, many=True, context={'request': request})
        
        return Response({
            'success': True,
            'count': faqs.count(),
            'faqs': serializer.data
        }, status=status.HTTP_200_OK)



class UpdateTelegramChatIdView(APIView):
    """
    API для обновления Telegram Chat ID пользователя
    """
    permission_classes = [IsAuthenticated]
    
    @extend_schema(
        summary="Обновить Telegram Chat ID",
        description="Обновляет Telegram Chat ID текущего пользователя для получения SMS",
        request=TelegramChatIdSerializer,
        responses={
            200: {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean', 'example': True},
                    'message': {'type': 'string', 'example': 'Telegram Chat ID успешно обновлен'}
                }
            },
            400: {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean', 'example': False},
                    'errors': {'type': 'object'}
                }
            },
            401: {'type': 'object', 'properties': {'detail': {'type': 'string'}}}
        },
        tags=['User Profile']
    )
    def post(self, request):
        """Обновление Telegram Chat ID"""
        serializer = TelegramChatIdSerializer(data=request.data, context={'request': request})
        
        if not serializer.is_valid():
            return Response({
                'success': False,
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        chat_id = serializer.validated_data['chat_id']
        
        # Обновляем Chat ID пользователя
        request.user.telegram_chat_id = chat_id
        request.user.save()
        
        return Response({
            'success': True,
            'message': 'Telegram Chat ID успешно обновлен'
        }, status=status.HTTP_200_OK)


class UserDetailsByIdView(APIView):
    """
    Получение информации о пользователе по ID
    """
    permission_classes = [AllowAny]
    
    @extend_schema(
        summary="Получить информацию о пользователе по ID",
        description="""
## Получить детальную информацию о пользователе

Возвращает полную информацию о пользователе по его ID.
Этот endpoint может использоваться для:
- Просмотра профиля мастера
- Получения информации о водителе
- Просмотра рейтинга и отзывов пользователя

## Response включает:
- Основную информацию (имя, email, телефон)
- Роли пользователя (Driver, Master)
- Баланс (если есть)
- Рейтинг и отзывы (для мастеров)
- Статистику (количество заказов, рекомендации)

## Примеры использования:

**Просмотр мастера:**
```
GET /api/auth/user/5/
```

**Просмотр водителя:**
```
GET /api/auth/user/10/
```
        """,
        parameters=[
            OpenApiParameter(
                name='user_id',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.PATH,
                description='ID пользователя',
                required=True
            )
        ],
        responses={
            200: UserDetailsSerializer,
            404: {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean', 'example': False},
                    'error': {'type': 'string', 'example': 'Пользователь не найден'}
                }
            }
        },
        tags=['User Profile']
    )
    def get(self, request, user_id):
        """Получение информации о пользователе по ID"""
        try:
            user = CustomUser.objects.get(id=user_id)
        except CustomUser.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Пользователь не найден'
            }, status=status.HTTP_404_NOT_FOUND)
        
        serializer = UserDetailsSerializer(user, context={'request': request})
        return Response({
            'success': True,
            'user': serializer.data
        }, status=status.HTTP_200_OK)


class SbpBalanceQrView(APIView):
    """
    POST: тело `{ "price": "1000.00" }` — ответ с ссылкой СБП и PNG QR (base64).
    Ссылка статическая («любая сумма»); сумму пользователь вводит в банке = price.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary='QR СБП для пополнения баланса',
        description=(
            'Минимум 1000 ₽. Создаётся `intent_id` — по нему смотрите статус (GET .../sbp-intent/{id}/) '
            'и подтверждайте оплату webhook POST .../sbp-webhook/ (секрет в .env) или в админке.'
        ),
        request=SbpBalanceQrSerializer,
        tags=['Payments'],
        responses={
            200: {
                'type': 'object',
                'properties': {
                    'success': {'type': 'boolean'},
                    'price': {'type': 'string'},
                    'pay_url': {'type': 'string'},
                    'qr_image_base64': {'type': 'string'},
                    'intent_id': {'type': 'string', 'format': 'uuid'},
                    'note': {'type': 'string'},
                },
            },
            400: {'type': 'object'},
            503: {'type': 'object'},
        },
    )
    def post(self, request):
        pay_url = getattr(settings, 'SBP_QR_PAY_URL', '').strip()
        if not pay_url:
            return Response(
                {'success': False, 'error': 'SBP_QR_PAY_URL не задан (settings / .env).'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        ser = SbpBalanceQrSerializer(data=request.data)
        if not ser.is_valid():
            return Response({'success': False, 'errors': ser.errors}, status=status.HTTP_400_BAD_REQUEST)

        price = ser.validated_data['price']
        intent = SbpPaymentIntent.objects.create(
            user=request.user,
            amount=price,
            status=SbpPaymentIntent.STATUS_PENDING,
        )
        qr_b64 = pay_url_to_qr_png_base64(pay_url)

        return Response(
            {
                'success': True,
                'intent_id': str(intent.id),
                'price': str(price),
                'pay_url': pay_url,
                'qr_image_base64': qr_b64,
                'note': (
                    'QR — постоянная ссылка СБП («любая сумма»): в банке укажите сумму = price. '
                    'Оплату подтверждает банк (webhook) или админ; статус: GET .../sbp-intent/{intent_id}/.'
                ),
            },
            status=status.HTTP_200_OK,
        )


def _sync_order_payment_paid(intent) -> None:
    """Если intent привязан к заказу — помечаем оплату заказа как paid."""
    if not intent:
        return
    from django.apps import apps

    Order = apps.get_model('order', 'Order')
    Order.objects.filter(sbp_payment_intent_id=intent.pk).update(payment_status='paid')


def _sbp_webhook_secret(request) -> str:
    h = request.headers.get('X-Sbp-Webhook-Secret') or request.headers.get('X-Webhook-Secret')
    if h:
        return h.strip()
    auth = request.headers.get('Authorization') or ''
    if auth.startswith('Bearer '):
        return auth[7:].strip()
    return ''


class SbpIntentStatusView(APIView):
    """Статус намерения СБП (pending / completed) и баланс после оплаты."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary='Статус СБП-пополнения',
        tags=['Payments'],
        responses={
            200: {'type': 'object'},
            404: {'type': 'object'},
        },
    )
    def get(self, request, intent_id):
        intent = SbpPaymentIntent.objects.filter(pk=intent_id).first()
        if not intent:
            return Response(
                {'success': False, 'error': 'Намерение не найдено.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Доступ:
        # - владелец intent
        # - или любой пользователь, связанный с заказом, к которому привязан intent:
        #   driver (order.user), главный мастер (order.master.user), или мастер из списка order.masters
        allowed = intent.user_id == request.user.id
        order_id = None
        if not allowed:
            from django.apps import apps

            Order = apps.get_model('order', 'Order')
            order = (
                Order.objects.filter(sbp_payment_intent_id=intent.pk)
                .select_related('master', 'master__user')
                .first()
            )
            if order:
                order_id = order.id
                if order.user_id == request.user.id:
                    allowed = True
                elif order.master_id and getattr(order.master, 'user_id', None) == request.user.id:
                    allowed = True
                elif order.masters.filter(id=request.user.id).exists():
                    allowed = True

        if not allowed:
            return Response(
                {'success': False, 'error': 'Намерение не найдено.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        data = {
            'success': True,
            'intent_id': str(intent.id),
            'status': intent.status,
            'price': str(intent.amount),
            'created_at': intent.created_at.isoformat(),
        }
        if order_id is not None:
            data['order_id'] = order_id
        if intent.completed_at:
            data['completed_at'] = intent.completed_at.isoformat()
        # Баланс показываем только владельцу intent (Driver),
        # чтобы мастер не видел баланс пользователя.
        if intent.status == SbpPaymentIntent.STATUS_COMPLETED and intent.user_id == request.user.id:
            data['balance'] = str(UserBalance.get_or_create_balance(request.user).amount)
        return Response(data, status=status.HTTP_200_OK)


class SbpWebhookView(APIView):
    """
    Сервер-сервер: после фактической оплаты (или интеграции банка) зачислить баланс.
    Заголовок: X-Sbp-Webhook-Secret: <SBP_WEBHOOK_SECRET из .env>
    Тело JSON: { \"intent_id\": \"uuid\", \"amount\": \"1000.00\" (опционально), \"bank_reference\": \"\" }
    """

    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(
        summary='Webhook: подтвердить СБП-оплату',
        description='Не для Swagger: передавайте секрет в заголовке X-Sbp-Webhook-Secret.',
        request=SbpWebhookSerializer,
        tags=['Payments'],
        responses={200: {'type': 'object'}, 400: {'type': 'object'}, 403: {'type': 'object'}, 503: {'type': 'object'}},
    )
    def post(self, request):
        expected = getattr(settings, 'SBP_WEBHOOK_SECRET', '').strip()
        if not expected:
            return Response(
                {'success': False, 'error': 'SBP_WEBHOOK_SECRET не задан в настройках.'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        if _sbp_webhook_secret(request) != expected:
            return Response({'success': False, 'error': 'Неверный секрет.'}, status=status.HTTP_403_FORBIDDEN)

        ser = SbpWebhookSerializer(data=request.data)
        if not ser.is_valid():
            return Response({'success': False, 'errors': ser.errors}, status=status.HTTP_400_BAD_REQUEST)

        vid = ser.validated_data['intent_id']
        amt = ser.validated_data.get('amount')
        ref = ser.validated_data.get('bank_reference') or ''

        code, obj = SbpPaymentIntent.complete_pending(
            vid,
            bank_reference=ref,
            expected_amount=amt,
        )

        if code == 'not_found':
            return Response({'success': False, 'error': 'intent_id не найден'}, status=status.HTTP_404_NOT_FOUND)
        if code == 'amount_mismatch':
            return Response({'success': False, 'error': 'Сумма не совпадает с намерением'}, status=status.HTTP_400_BAD_REQUEST)
        if code == 'not_pending':
            return Response(
                {'success': False, 'error': 'Намерение не в статусе pending', 'status': obj.status if obj else None},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if code == 'already_completed':
            bal = UserBalance.get_or_create_balance(obj.user) if obj else None
            _sync_order_payment_paid(obj)
            return Response(
                {
                    'success': True,
                    'result': 'already_completed',
                    'intent_id': str(obj.id),
                    'balance': str(bal.amount) if bal else None,
                },
                status=status.HTTP_200_OK,
            )

        bal = UserBalance.get_or_create_balance(obj.user)
        _sync_order_payment_paid(obj)
        return Response(
            {
                'success': True,
                'result': 'completed',
                'intent_id': str(obj.id),
                'balance': str(bal.amount),
            },
            status=status.HTTP_200_OK,
        )


class SbpConfirmByTrxView(APIView):
    """
    Резервный API: подтвердить оплату по trx_id (из админки банка),
    когда банк не присылает наш intent_id.

    Это ручная привязка (через API):
    - ищем самый свежий pending intent по сумме (если amount передан)
    - иначе самый свежий pending intent вообще
    и помечаем completed с bank_reference=trx_id.
    """

    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(
        summary='Confirm: СБП по TRX_ID (manual)',
        description='Ручное подтверждение по trx_id. Требует X-Sbp-Webhook-Secret как у webhook.',
        request=SbpConfirmByTrxSerializer,
        tags=['Payments'],
        responses={200: {'type': 'object'}, 400: {'type': 'object'}, 403: {'type': 'object'}, 404: {'type': 'object'}, 503: {'type': 'object'}},
    )
    def post(self, request):
        expected = getattr(settings, 'SBP_WEBHOOK_SECRET', '').strip()
        if not expected:
            return Response(
                {'success': False, 'error': 'SBP_WEBHOOK_SECRET не задан в настройках.'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        if _sbp_webhook_secret(request) != expected:
            return Response({'success': False, 'error': 'Неверный секрет.'}, status=status.HTTP_403_FORBIDDEN)

        ser = SbpConfirmByTrxSerializer(data=request.data)
        if not ser.is_valid():
            return Response({'success': False, 'errors': ser.errors}, status=status.HTTP_400_BAD_REQUEST)

        trx_id = (ser.validated_data['trx_id'] or '').strip()
        amt = ser.validated_data.get('amount')

        qs = SbpPaymentIntent.objects.filter(status=SbpPaymentIntent.STATUS_PENDING).order_by('-created_at')
        if amt is not None:
            qs = qs.filter(amount=amt)

        intent = qs.first()
        if not intent:
            return Response(
                {'success': False, 'error': 'Подходящий pending intent не найден.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        code, obj = SbpPaymentIntent.complete_pending(
            intent.id,
            bank_reference=trx_id,
            expected_amount=amt,
        )
        if code == 'amount_mismatch':
            return Response({'success': False, 'error': 'Сумма не совпадает с намерением'}, status=status.HTTP_400_BAD_REQUEST)
        if code == 'not_pending':
            return Response({'success': False, 'error': 'Намерение не в статусе pending'}, status=status.HTTP_400_BAD_REQUEST)
        if code == 'not_found':
            return Response({'success': False, 'error': 'intent не найден'}, status=status.HTTP_404_NOT_FOUND)

        bal = UserBalance.get_or_create_balance(obj.user) if obj else None
        _sync_order_payment_paid(obj)
        return Response(
            {
                'success': True,
                'result': 'completed',
                'intent_id': str(obj.id),
                'trx_id': trx_id,
                'balance': str(bal.amount) if bal else None,
            },
            status=status.HTTP_200_OK,
        )


class AlfaGetOrderStatusExtendedView(APIView):
    """
    API: проверить оплату через Alfa acquiring метод getOrderStatusExtended.

    Если в запросе передан `intent_id`, и шлюз говорит что заказ оплачен,
    мы помечаем intent как completed (и order.payment_status=paid через _sync_order_payment_paid).
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary='Alfa: getOrderStatusExtended (check paid)',
        tags=['Payments'],
        request=AlfaOrderStatusExtendedSerializer,
        responses={200: {'type': 'object'}, 400: {'type': 'object'}, 502: {'type': 'object'}, 503: {'type': 'object'}},
    )
    def post(self, request):
        ser = AlfaOrderStatusExtendedSerializer(data=request.data)
        if not ser.is_valid():
            return Response({'success': False, 'errors': ser.errors}, status=status.HTTP_400_BAD_REQUEST)

        alfa_order_id = ser.validated_data.get('alfa_order_id') or None
        alfa_order_number = ser.validated_data.get('alfa_order_number') or None
        intent_id = ser.validated_data.get('intent_id')
        amt = ser.validated_data.get('amount')

        gw = post_order_status_extended(order_id=alfa_order_id, order_number=alfa_order_number)
        if gw.get('error'):
            return Response({'success': False, 'gateway': gw}, status=status.HTTP_502_BAD_GATEWAY)

        paid = is_paid_status(gw)
        result: dict = {'success': True, 'paid': paid, 'gateway': gw}

        if paid and intent_id:
            code, obj = SbpPaymentIntent.complete_pending(
                intent_id,
                bank_reference=alfa_order_id or alfa_order_number or '',
                expected_amount=amt,
            )
            result['intent_update'] = {'code': code}
            if obj:
                result['intent_update']['intent_id'] = str(obj.id)
                result['intent_update']['status'] = obj.status
            if code in ('ok', 'already_completed'):
                _sync_order_payment_paid(obj)

        return Response(result, status=status.HTTP_200_OK)


def _save_alfa_sbp_template_snapshot(user, gw: dict, generated: dict | None = None) -> None:
    tid = gw.get('templateId')
    if not tid:
        return
    AlfaSbpTemplateSnapshot.objects.update_or_create(
        user=user,
        template_id=str(tid)[:40],
        defaults={'gateway_response': gw, 'generated_meta': generated},
    )


def _alfa_sbp_quick_create_body(price: Decimal) -> dict:
    """Поля createTemplate.do без кредов: имя, даты, сумма, PNG QR — статично/авто."""
    tz_name = getattr(settings, 'TIME_ZONE', 'Europe/Moscow')
    try:
        tz = ZoneInfo(tz_name)
    except Exception:
        tz = ZoneInfo('Europe/Moscow')
    now = timezone.now().astimezone(tz).replace(microsecond=0)
    years = max(1, min(30, getattr(settings, 'SBP_GATEWAY_TEMPLATE_VALID_YEARS', 10)))
    end = now + timedelta(days=365 * years)

    def _fmt(dt):
        return dt.strftime('%Y-%m-%dT%H:%M:%S')

    kopecks = int((price * Decimal('100')).quantize(Decimal('1'), rounding=ROUND_HALF_UP))
    prefix = (getattr(settings, 'SBP_GATEWAY_TEMPLATE_NAME_PREFIX', 'CheckAvto') or 'CheckAvto')[:80]
    name = f'{prefix}-{uuid.uuid4().hex[:10]}'[:140]
    channel = (getattr(settings, 'SBP_GATEWAY_TEMPLATE_DIST_CHANNEL', 'CheckAvto') or 'CheckAvto')[:256]
    purpose = f'CheckAvto {price} RUB'[:140]
    w = max(10, min(1000, getattr(settings, 'SBP_GATEWAY_TEMPLATE_QR_WIDTH', 300)))
    h = max(10, min(1000, getattr(settings, 'SBP_GATEWAY_TEMPLATE_QR_HEIGHT', 300)))

    return {
        'name': name,
        'type': 'SBP_QR',
        'startDate': _fmt(now),
        'endDate': _fmt(end),
        'amount': kopecks,
        'currency': '810',
        'distributionChannel': channel,
        'qrTemplate': {
            'qrWidth': int(w),
            'qrHeight': int(h),
            'paymentPurpose': purpose,
        },
    }


def _alfa_sbp_create_body(vd: dict) -> dict:
    body: dict = {
        'name': vd['name'],
        'type': vd.get('template_type') or 'SBP_QR',
    }
    sd = (vd.get('start_date') or '').strip()
    if sd:
        body['startDate'] = sd
    ed = (vd.get('end_date') or '').strip()
    if ed:
        body['endDate'] = ed
    if vd.get('amount_kopecks') is not None:
        body['amount'] = vd['amount_kopecks']
    cur = (vd.get('currency') or '810').strip()
    if cur:
        body['currency'] = cur
    dc = (vd.get('distribution_channel') or '').strip()
    if dc:
        body['distributionChannel'] = dc
    qt: dict = {}
    if vd.get('qr_height') is not None and vd.get('qr_width') is not None:
        qt['qrHeight'] = int(vd['qr_height'])
        qt['qrWidth'] = int(vd['qr_width'])
    pp = (vd.get('payment_purpose') or '').strip()
    if pp:
        qt['paymentPurpose'] = pp[:140]
    qid = (vd.get('qrc_id') or '').strip()
    if qid:
        qt['qrcId'] = qid[:32]
    if qt:
        body['qrTemplate'] = qt
    return body


def _alfa_sbp_update_body(vd: dict) -> dict:
    body: dict = {'templateId': vd['template_id']}
    if vd.get('status'):
        body['status'] = vd['status']
    n = (vd.get('name') or '').strip()
    if n:
        body['name'] = n
    sd = (vd.get('start_date') or '').strip()
    if sd:
        body['startDate'] = sd
    ed = (vd.get('end_date') or '').strip()
    if ed:
        body['endDate'] = ed
    return body


#
# Alfa SBP gateway views were removed from public API for this project.
#
