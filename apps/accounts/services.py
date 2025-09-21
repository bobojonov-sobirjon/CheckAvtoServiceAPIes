"""
Бизнес-логика для SMS и пользовательских сервисов
"""
import requests
import random
from django.conf import settings
from django.core.cache import cache
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework import status
from rest_framework.response import Response

User = get_user_model()


class SMSService:
    """Класс для SMS сервисов"""
    
    @staticmethod
    def send_sms_code(phone_number: str) -> dict:
        """
        Отправка SMS кода на номер телефона
        
        Args:
            phone_number (str): Номер телефона
            
        Returns:
            dict: Результат
        """
        try:
            # Проверка существования пользователя
            try:
                user = User.objects.get(phone_number=phone_number)
                user_exists = True
            except User.DoesNotExist:
                user_exists = False
            
            # Создание 4-значного кода
            sms_code = str(random.randint(1000, 9999))
            
            # Отправка SMS через SMSC.ru
            data = {
                'login': settings.SMSC_LOGIN,
                'psw': settings.SMSC_PASSWORD,
                'phones': phone_number,
                'mes': f'Ваш код подтверждения: {sms_code}',
                'fmt': 3  # JSON формат
            }
            
            response = requests.get(settings.SMSC_API_URL, params=data, timeout=10)
            result = response.json()
            
            if result.get('error'):
                return {
                    'success': False,
                    'error': f'Ошибка отправки SMS: {result.get("error")}',
                    'status_code': status.HTTP_400_BAD_REQUEST
                }
            
            # Сохранение кода в кэше на 5 минут
            cache.set(f'sms_code_{phone_number}', sms_code, timeout=300)
            
            # Сохранение информации о пользователе в кэше
            cache.set(f'user_exists_{phone_number}', user_exists, timeout=300)
            
            return {
                'success': True,
                'message': 'SMS код отправлен',
                'phone': phone_number,
                'user_exists': user_exists,
                'status_code': status.HTTP_200_OK
            }
            
        except requests.exceptions.Timeout:
            return {
                'success': False,
                'error': 'Время ожидания SMS сервиса истекло',
                'status_code': status.HTTP_408_REQUEST_TIMEOUT
            }
        except requests.exceptions.RequestException as e:
            return {
                'success': False,
                'error': f'Ошибка SMS сервиса: {str(e)}',
                'status_code': status.HTTP_500_INTERNAL_SERVER_ERROR
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'Неожиданная ошибка: {str(e)}',
                'status_code': status.HTTP_500_INTERNAL_SERVER_ERROR
            }
    
    @staticmethod
    def verify_sms_code(phone_number: str, sms_code: str) -> dict:
        """
        Проверка SMS кода
        
        Args:
            phone_number (str): Номер телефона
            sms_code (str): SMS код
            
        Returns:
            dict: Результат
        """
        try:
            # Получение кода из кэша
            stored_code = cache.get(f'sms_code_{phone_number}')
            
            if not stored_code:
                return {
                    'success': False,
                    'error': 'Срок действия SMS кода истек или код не найден',
                    'status_code': status.HTTP_400_BAD_REQUEST
                }
            
            # Проверка кода
            if stored_code != sms_code:
                return {
                    'success': False,
                    'error': 'Неверный SMS код',
                    'status_code': status.HTTP_400_BAD_REQUEST
                }
            
            # Если код правильный, найти или создать пользователя
            # Проверка существования пользователя из кэша
            user_exists = cache.get(f'user_exists_{phone_number}', False)
            
            if user_exists:
                # Пользователь существует, найти его
                try:
                    user = User.objects.get(phone_number=phone_number)
                    created = False
                except User.DoesNotExist:
                    # Если пользователь не найден, создать нового
                    user, created = User.objects.get_or_create(
                        phone_number=phone_number,
                        defaults={
                            'username': f'user_{phone_number}',
                            'email': f'{phone_number}@example.com',
                            'first_name': 'User',
                            'last_name': phone_number,
                            'is_verified': True
                        }
                    )
            else:
                # Пользователь не существует, создать нового
                # Определение страны номера
                if phone_number.startswith('998'):
                    country = 'UZ'
                    display_name = f'UZ_{phone_number[3:]}'  # Удаление 998
                else:
                    country = 'RU'
                    display_name = f'RU_{phone_number[1:]}'  # Удаление 7
                
                user, created = User.objects.get_or_create(
                    phone_number=phone_number,
                    defaults={
                        'username': f'user_{phone_number}',
                        'email': f'{phone_number}@example.com',
                        'first_name': f'User_{country}',
                        'last_name': display_name,
                        'is_verified': True
                    }
                )
            
            # Создание JWT токена
            refresh = RefreshToken.for_user(user)
            access_token = refresh.access_token
            
            # Удаление кода из кэша
            cache.delete(f'sms_code_{phone_number}')
            
            # Очистка кэша
            cache.delete(f'user_exists_{phone_number}')
            
            return {
                'success': True,
                'message': 'Успешный вход',
                'user': user,
                'user_created': created,
                'tokens': {
                    'access': str(access_token),
                    'refresh': str(refresh)
                },
                'status_code': status.HTTP_200_OK
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Ошибка создания пользователя: {str(e)}',
                'status_code': status.HTTP_500_INTERNAL_SERVER_ERROR
            }
