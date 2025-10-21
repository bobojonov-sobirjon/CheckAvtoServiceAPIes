from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.generics import RetrieveUpdateDestroyAPIView
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from .serializers import (
    PhoneNumberSerializer, 
    IdentifierSerializer,
    SMSVerificationSerializer, 
    UserSerializer, 
    TokenResponseSerializer,
    SMSResponseSerializer,
    UserDetailsSerializer,
    UserUpdateSerializer
)
from .services import SMSService
from .models import CustomUser


class LoginView(APIView):
    """
    Вход по email или номеру телефона (отправка SMS кода)
    """
    permission_classes = [AllowAny]
    
    @swagger_auto_schema(
        operation_description="Отправка 4-значного кода подтверждения на номер телефона (SMS) или email. Если пользователь не найден, создается новый пользователь автоматически. Параметр 'role' (Driver или Master) обязателен только для новых пользователей.",
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
        operation_description="Проверка SMS кода и получение JWT токена. Параметр 'role' (Driver или Master) обязателен только для новых пользователей.",
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


class UserDetailsView(RetrieveUpdateDestroyAPIView):
    """
    Получение, обновление и удаление информации о пользователе
    """
    serializer_class = UserDetailsSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    
    def get_object(self):
        """Возвращает текущего пользователя"""
        return self.request.user
    
    def get_serializer_class(self):
        """Возвращает соответствующий сериализатор в зависимости от метода"""
        if self.request.method in ['PUT', 'PATCH']:
            return UserUpdateSerializer
        return UserDetailsSerializer
    
    @swagger_auto_schema(
        operation_description="Получение детальной информации о текущем пользователе",
        responses={
            200: openapi.Response(
                description="Информация о пользователе",
                schema=UserDetailsSerializer
            ),
            401: openapi.Response(
                description="Не авторизован",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'detail': openapi.Schema(type=openapi.TYPE_STRING, example="Authentication credentials were not provided.")
                    }
                )
            )
        },
        tags=['User Details']
    )
    def get(self, request, *args, **kwargs):
        """Получение информации о пользователе"""
        return super().get(request, *args, **kwargs)
    
    @swagger_auto_schema(
        operation_description="Обновление информации о пользователе. Можно добавить email если есть только phone_number, или добавить phone_number если есть только email. Поддерживает загрузку изображений через form-data.",
        request_body=UserUpdateSerializer,
        responses={
            200: openapi.Response(
                description="Информация о пользователе обновлена",
                schema=UserDetailsSerializer
            ),
            400: openapi.Response(
                description="Неверные данные",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'field_name': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Schema(type=openapi.TYPE_STRING))
                    }
                )
            ),
            401: openapi.Response(
                description="Не авторизован",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'detail': openapi.Schema(type=openapi.TYPE_STRING, example="Authentication credentials were not provided.")
                    }
                )
            )
        },
        tags=['User Details'],
        consumes=['application/json', 'multipart/form-data']
    )
    def put(self, request, *args, **kwargs):
        """Полное обновление информации о пользователе"""
        return super().put(request, *args, **kwargs)
    
    @swagger_auto_schema(
        operation_description="Частичное обновление информации о пользователе. Можно добавить email если есть только phone_number, или добавить phone_number если есть только email. Поддерживает загрузку изображений через form-data.",
        request_body=UserUpdateSerializer,
        responses={
            200: openapi.Response(
                description="Информация о пользователе обновлена",
                schema=UserDetailsSerializer
            ),
            400: openapi.Response(
                description="Неверные данные",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'field_name': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Schema(type=openapi.TYPE_STRING))
                    }
                )
            ),
            401: openapi.Response(
                description="Не авторизован",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'detail': openapi.Schema(type=openapi.TYPE_STRING, example="Authentication credentials were not provided.")
                    }
                )
            )
        },
        tags=['User Details'],
        consumes=['application/json', 'multipart/form-data']
    )
    def patch(self, request, *args, **kwargs):
        """Частичное обновление информации о пользователе"""
        return super().patch(request, *args, **kwargs)
    
    @swagger_auto_schema(
        operation_description="Удаление аккаунта пользователя",
        responses={
            204: openapi.Response(
                description="Аккаунт успешно удален"
            ),
            401: openapi.Response(
                description="Не авторизован",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'detail': openapi.Schema(type=openapi.TYPE_STRING, example="Authentication credentials were not provided.")
                    }
                )
            )
        },
        tags=['User Details']
    )
    def delete(self, request, *args, **kwargs):
        """Удаление аккаунта пользователя"""
        user = self.get_object()
        user.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)