from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from .serializers import (
    PhoneNumberSerializer, 
    SMSVerificationSerializer, 
    UserSerializer, 
    TokenResponseSerializer,
    SMSResponseSerializer
)
from .services import SMSService


class LoginView(APIView):
    """
    Вход по номеру телефона (отправка SMS кода)
    """
    permission_classes = [AllowAny]
    
    @swagger_auto_schema(
        operation_description="Отправка 4-значного SMS кода на номер телефона",
        request_body=PhoneNumberSerializer,
        responses={
            200: openapi.Response(
                description="SMS код успешно отправлен",
                schema=SMSResponseSerializer
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
        """Вход - отправка SMS кода"""
        serializer = PhoneNumberSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response({
                'success': False,
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        phone_number = serializer.validated_data['phone_number']
        
        # Отправка кода через SMS сервис
        result = SMSService.send_sms_code(phone_number)
        
        if result['success']:
            # Добавление информации о существовании пользователя
            response_data = {
                'success': True,
                'message': result['message'],
                'phone': result['phone'],
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
        operation_description="Проверка SMS кода и получение JWT токена",
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
        
        phone_number = serializer.validated_data['phone_number']
        sms_code = serializer.validated_data['sms_code']
        
        # Проверка кода через SMS сервис
        result = SMSService.verify_sms_code(phone_number, sms_code)
        
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
