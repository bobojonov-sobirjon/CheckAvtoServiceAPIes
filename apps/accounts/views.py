from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from drf_yasg.utils import swagger_auto_schema, no_body
from drf_yasg import openapi
from .serializers import (
    PhoneNumberSerializer, 
    IdentifierSerializer,
    SMSVerificationSerializer, 
    UserSerializer, 
    TokenResponseSerializer,
    SMSResponseSerializer,
    UserDetailsSerializer,
    UserUpdateSerializer,
    FAQSerializer
)
from .services import SMSService
from .models import CustomUser, FAQ


class LoginView(APIView):
    """
    Вход по email или номеру телефона (отправка SMS кода)
    """
    permission_classes = [AllowAny]
    
    @swagger_auto_schema(
        operation_description="Отправка 4-значного кода подтверждения на номер телефона (SMS) или email. Если пользователь не найден, создается новый пользователь автоматически. Параметр 'role' (Driver или Master) обязателен.",
        request_body=IdentifierSerializer,
        responses={
            200: openapi.Response(
                description="Код подтверждения успешно отправлен",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'success': openapi.Schema(type=openapi.TYPE_BOOLEAN, example=True),
                        'message': openapi.Schema(type=openapi.TYPE_STRING, example="Код подтверждения отправлен на email"),
                        'identifier': openapi.Schema(type=openapi.TYPE_STRING, example="user@example.com"),
                        'identifier_type': openapi.Schema(type=openapi.TYPE_STRING, example="email"),
                        'phone': openapi.Schema(type=openapi.TYPE_STRING, example="998901234567", description="Номер телефона (только для phone)"),
                        'email': openapi.Schema(type=openapi.TYPE_STRING, example="user@example.com", description="Email адрес (только для email)"),
                        'user_exists': openapi.Schema(type=openapi.TYPE_BOOLEAN, example=True),
                        'role': openapi.Schema(type=openapi.TYPE_STRING, example="Driver", description="Роль пользователя (Driver или Master)")
                    }
                )
            ),
            400: openapi.Response(
                description="Неверные данные",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'success': openapi.Schema(type=openapi.TYPE_BOOLEAN, example=False),
                        'errors': openapi.Schema(type=openapi.TYPE_OBJECT)
                    }
                )
            ),
            500: openapi.Response(
                description="Ошибка сервера",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'success': openapi.Schema(type=openapi.TYPE_BOOLEAN, example=False),
                        'error': openapi.Schema(type=openapi.TYPE_STRING)
                    }
                )
            )
        },
        tags=['Authentication']
    )
    def post(self, request):
        """Вход - отправка кода подтверждения на телефон или email"""
        serializer = IdentifierSerializer(data=request.data)
        
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
                'user_exists': result.get('user_exists', False)
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
    
    @swagger_auto_schema(
        operation_description="Проверка SMS кода и получение JWT токена. Параметр 'role' (Driver или Master) обязателен.",
        request_body=SMSVerificationSerializer,
        responses={
            200: openapi.Response(
                description="SMS код правильный, токен выдан",
                schema=TokenResponseSerializer
            ),
            400: openapi.Response(
                description="Неверные данные или SMS код",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'success': openapi.Schema(type=openapi.TYPE_BOOLEAN, example=False),
                        'errors': openapi.Schema(type=openapi.TYPE_OBJECT),
                        'error': openapi.Schema(type=openapi.TYPE_STRING)
                    }
                )
            ),
            500: openapi.Response(
                description="Ошибка сервера",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'success': openapi.Schema(type=openapi.TYPE_BOOLEAN, example=False),
                        'error': openapi.Schema(type=openapi.TYPE_STRING)
                    }
                )
            )
        },
        tags=['Authentication']
    )
    def post(self, request):
        """Проверка SMS кода"""
        serializer = SMSVerificationSerializer(data=request.data)
        
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
            user_serializer = UserSerializer(result['user'])
            
            response_data = {
                'success': True,
                'message': result['message'],
                'user': user_serializer.data,
                'user_created': result.get('user_created', False),
                'tokens': result['tokens']
            }
            
            response_serializer = TokenResponseSerializer(response_data)
            return Response(response_serializer.data, status=result['status_code'])
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
    
    @swagger_auto_schema(
        operation_description="Проверка статуса SMS сервиса SMSC.ru и баланса",
        responses={
            200: openapi.Response(
                description="Статус SMS сервиса",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'success': openapi.Schema(type=openapi.TYPE_BOOLEAN, example=True),
                        'service': openapi.Schema(type=openapi.TYPE_STRING, example='SMSC.ru'),
                        'balance': openapi.Schema(type=openapi.TYPE_NUMBER, example=150.50),
                        'currency': openapi.Schema(type=openapi.TYPE_STRING, example='RUB'),
                        'status': openapi.Schema(type=openapi.TYPE_STRING, example='active')
                    }
                )
            ),
            400: openapi.Response(
                description="Ошибка проверки статуса",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'success': openapi.Schema(type=openapi.TYPE_BOOLEAN, example=False),
                        'error': openapi.Schema(type=openapi.TYPE_STRING)
                    }
                )
            )
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
    
    @swagger_auto_schema(
        operation_description="Получение детальной информации о текущем авторизованном пользователе",
        responses={
            200: openapi.Response(
                description="Информация о пользователе",
                schema=UserDetailsSerializer
            ),
            401: openapi.Response(
                description="Пользователь не авторизован",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'detail': openapi.Schema(type=openapi.TYPE_STRING, example="Authentication credentials were not provided.")
                    }
                )
            )
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
    
    @swagger_auto_schema(
        operation_description="Обновление информации о текущем пользователе. Поддерживает обновление всех полей, включая avatar (файл) и роль (группу).",
        request_body=UserUpdateSerializer,
        operation_id='user_update_full',
        consumes=['multipart/form-data'],
        responses={
            200: openapi.Response(
                description="Информация о пользователе успешно обновлена",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'success': openapi.Schema(type=openapi.TYPE_BOOLEAN, example=True),
                        'message': openapi.Schema(type=openapi.TYPE_STRING, example="Информация о пользователе успешно обновлена"),
                        'user': openapi.Schema(type=openapi.TYPE_OBJECT)
                    }
                )
            ),
            400: openapi.Response(
                description="Ошибка валидации данных",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'success': openapi.Schema(type=openapi.TYPE_BOOLEAN, example=False),
                        'errors': openapi.Schema(type=openapi.TYPE_OBJECT)
                    }
                )
            ),
            401: openapi.Response(
                description="Пользователь не авторизован",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'detail': openapi.Schema(type=openapi.TYPE_STRING, example="Authentication credentials were not provided.")
                    }
                )
            )
        },
        tags=['User Profile']
    )
    def put(self, request):
        """Полное обновление информации о пользователе"""
        user = request.user
        serializer = UserUpdateSerializer(user, data=request.data, partial=False)
        
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
    
    @swagger_auto_schema(
        operation_description="Частичное обновление информации о текущем пользователе. Можно обновить только нужные поля. Поддерживает avatar (файл) и роль (группу).",
        request_body=UserUpdateSerializer,
        operation_id='user_update_partial',
        consumes=['multipart/form-data'],
        responses={
            200: openapi.Response(
                description="Информация о пользователе успешно обновлена",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'success': openapi.Schema(type=openapi.TYPE_BOOLEAN, example=True),
                        'message': openapi.Schema(type=openapi.TYPE_STRING, example="Информация о пользователе успешно обновлена"),
                        'user': openapi.Schema(type=openapi.TYPE_OBJECT)
                    }
                )
            ),
            400: openapi.Response(
                description="Ошибка валидации данных",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'success': openapi.Schema(type=openapi.TYPE_BOOLEAN, example=False),
                        'errors': openapi.Schema(type=openapi.TYPE_OBJECT)
                    }
                )
            ),
            401: openapi.Response(
                description="Пользователь не авторизован",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'detail': openapi.Schema(type=openapi.TYPE_STRING, example="Authentication credentials were not provided.")
                    }
                )
            )
        },
        tags=['User Profile']
    )
    def patch(self, request):
        """Частичное обновление информации о пользователе"""
        user = request.user
        serializer = UserUpdateSerializer(user, data=request.data, partial=True)
        
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
    
    @swagger_auto_schema(
        operation_description="Получение списка всех активных FAQ. Доступно без авторизации.",
        responses={
            200: openapi.Response(
                description="Список FAQ успешно получен",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'success': openapi.Schema(type=openapi.TYPE_BOOLEAN, example=True),
                        'count': openapi.Schema(type=openapi.TYPE_INTEGER, example=5),
                        'faqs': openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    'id': openapi.Schema(type=openapi.TYPE_INTEGER, example=1),
                                    'question': openapi.Schema(type=openapi.TYPE_STRING, example="Как зарегистрироваться в системе?"),
                                    'answer': openapi.Schema(type=openapi.TYPE_STRING, example="Для регистрации..."),
                                    'order': openapi.Schema(type=openapi.TYPE_INTEGER, example=1),
                                    'created_at': openapi.Schema(type=openapi.TYPE_STRING, format='date-time'),
                                    'updated_at': openapi.Schema(type=openapi.TYPE_STRING, format='date-time')
                                }
                            )
                        )
                    }
                )
            )
        },
        tags=['FAQ']
    )
    def get(self, request):
        """Получение всех активных FAQ"""
        faqs = FAQ.objects.filter(is_active=True)
        serializer = FAQSerializer(faqs, many=True)
        
        return Response({
            'success': True,
            'count': faqs.count(),
            'faqs': serializer.data
        }, status=status.HTTP_200_OK)


