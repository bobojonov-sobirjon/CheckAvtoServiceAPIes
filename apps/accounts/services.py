"""
Бизнес-логика для SMS и пользовательских сервисов
"""
import requests
import random
import logging
from django.conf import settings
from django.core.cache import cache
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.mail import send_mail
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework import status
from rest_framework.response import Response

# Настройка логирования
logger = logging.getLogger(__name__)

User = get_user_model()


class SMSService:
    """Класс для SMS сервисов"""
    
    @staticmethod
    def format_phone_number(phone_number: str) -> str:
        """
        Форматирование номера телефона для SMSC.ru
        
        Args:
            phone_number (str): Номер телефона
            
        Returns:
            str: Отформатированный номер
        """
        # Удаляем все символы кроме цифр
        cleaned = ''.join(filter(str.isdigit, phone_number))
        
        # Если номер начинается с 8, заменяем на 7
        if cleaned.startswith('8') and len(cleaned) == 11:
            cleaned = '7' + cleaned[1:]
        
        # Если номер начинается с +7, убираем +
        if phone_number.startswith('+7'):
            cleaned = '7' + cleaned[1:]
        
        # Если номер начинается с 7 и имеет 11 цифр, оставляем как есть
        if cleaned.startswith('7') and len(cleaned) == 11:
            return cleaned
        
        # Если номер начинается с 998 (Узбекистан), оставляем как есть
        if cleaned.startswith('998') and len(cleaned) == 12:
            return cleaned
        
        # Если номер начинается с 9 и имеет 10 цифр, добавляем 7
        if cleaned.startswith('9') and len(cleaned) == 10:
            return '7' + cleaned
        
        return cleaned
    
    @staticmethod
    def send_email_code(email: str, sms_code: str) -> dict:
        """
        Отправка кода подтверждения на email
        
        Args:
            email (str): Email адрес
            sms_code (str): Код подтверждения
            
        Returns:
            dict: Результат отправки
        """
        try:
            subject = 'Код подтверждения CheckAvto'
            message = f'Ваш код подтверждения: {sms_code}'
            from_email = settings.DEFAULT_FROM_EMAIL
            recipient_list = [email]
            
            send_mail(
                subject=subject,
                message=message,
                from_email=from_email,
                recipient_list=recipient_list,
                fail_silently=False,
            )
            
            logger.info(f"Email code {sms_code} sent to {email}")
            return {
                'success': True,
                'message': 'Код подтверждения отправлен на email'
            }
            
        except Exception as e:
            logger.error(f"Failed to send email to {email}: {str(e)}")
            return {
                'success': False,
                'error': f'Ошибка отправки email: {str(e)}'
            }
    
    @staticmethod
    def check_smsc_balance() -> dict:
        """
        Проверка баланса SMSC.ru
        
        Returns:
            dict: Информация о балансе
        """
        try:
            data = {
                'login': settings.SMSC_LOGIN,
                'psw': settings.SMSC_PASSWORD,
                'fmt': 3  # JSON формат
            }
            
            response = requests.get('https://smsc.ru/sys/balance.php', params=data, timeout=10)
            result = response.json()
            
            if result.get('error'):
                return {
                    'success': False,
                    'error': f'Ошибка проверки баланса: {result.get("error")}',
                    'balance': 0
                }
            
            return {
                'success': True,
                'balance': float(result.get('balance', 0)),
                'currency': result.get('currency', 'RUB')
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Ошибка проверки баланса: {str(e)}',
                'balance': 0
            }
    
    @staticmethod
    def send_sms_code(identifier: str, identifier_type: str = 'phone', role: str = None) -> dict:
        """
        Отправка SMS кода на номер телефона или email
        
        Args:
            identifier (str): Номер телефона или email
            identifier_type (str): Тип идентификатора ('phone' или 'email')
            role (str): Роль пользователя ('Driver' или 'Master') - только для новых пользователей
            
        Returns:
            dict: Результат
        """
        try:
            # Валидация роли
            if role and role not in ['Driver', 'Master']:
                return {
                    'success': False,
                    'error': 'Роль должна быть "Driver" или "Master"',
                    'status_code': status.HTTP_400_BAD_REQUEST
                }
            
            # Проверка баланса SMSC.ru перед отправкой
            balance_info = SMSService.check_smsc_balance()
            if not balance_info['success']:
                logger.warning(f"Could not check balance: {balance_info['error']}")
            else:
                logger.info(f"SMSC.ru balance: {balance_info['balance']} {balance_info['currency']}")
                if balance_info['balance'] < 1.0:  # Минимальный баланс для отправки SMS
                    # В тестовом режиме продолжаем без отправки SMS
                    logger.warning("Insufficient balance, continuing in test mode")
            
            # Проверка существования пользователя
            user_exists = False
            phone_number = None
            
            if identifier_type == 'phone':
                phone_number = identifier
                try:
                    user = User.objects.get(phone_number=phone_number)
                    user_exists = True
                except User.DoesNotExist:
                    user_exists = False
            elif identifier_type == 'email':
                try:
                    user = User.objects.get(email=identifier)
                    user_exists = True
                    # Если пользователь найден по email, получаем его номер телефона
                    if user.phone_number:
                        phone_number = user.phone_number
                    else:
                        # Если у пользователя нет номера телефона, используем email для отправки SMS
                        phone_number = identifier
                except User.DoesNotExist:
                    user_exists = False
                    # Если пользователь не найден, создаем нового пользователя
                    # Для email используем сам email как "номер телефона" для отправки SMS
                    phone_number = identifier
            
            if not phone_number:
                return {
                    'success': False,
                    'error': 'Не удалось определить номер телефона для отправки SMS',
                    'status_code': status.HTTP_400_BAD_REQUEST
                }
            
            # Создание 4-значного кода
            sms_code = str(random.randint(1000, 9999))
            
            # Отправка кода в зависимости от типа идентификатора
            if identifier_type == 'email':
                # Отправка кода на email
                email_result = SMSService.send_email_code(identifier, sms_code)
                if not email_result['success']:
                    return {
                        'success': False,
                        'error': email_result['error'],
                        'status_code': status.HTTP_500_INTERNAL_SERVER_ERROR
                    }
            else:
                # Отправка SMS на номер телефона
                # Форматирование номера телефона
                formatted_phone = SMSService.format_phone_number(phone_number)
                logger.info(f"Original phone: {phone_number}, Formatted phone: {formatted_phone}")
                
                # Проверяем баланс перед отправкой SMS (временно отключено для тестирования)
                if False:  # balance_info.get('success') and balance_info.get('balance', 0) >= 1.0:
                    # Отправка SMS через SMSC.ru
                    data = {
                        'login': settings.SMSC_LOGIN,
                        'psw': settings.SMSC_PASSWORD,
                        'phones': formatted_phone,
                        'mes': f'Ваш код подтверждения: {sms_code}',
                        'sender': 'SMSC.RU',  # Tasdiqlangan sender ID
                        'fmt': 3  # JSON формат
                    }
                    
                    logger.info(f"Sending SMS to {formatted_phone} with data: {data}")
                    
                    response = requests.get(settings.SMSC_API_URL, params=data, timeout=10)
                    logger.info(f"SMSC.ru response status: {response.status_code}")
                    logger.info(f"SMSC.ru response text: {response.text}")
                    
                    result = response.json()
                    logger.info(f"SMSC.ru response JSON: {result}")
                    
                    if result.get('error'):
                        error_msg = result.get('error')
                        logger.error(f"SMSC.ru error: {error_msg}")
                        
                        # Специальная обработка для разных типов ошибок
                        if 'denied' in error_msg.lower():
                            return {
                                'success': False,
                                'error': f'Ошибка отправки SMS: Сообщение отклонено. Возможно, номер заблокирован или аккаунт не имеет прав для отправки на данный номер. Ошибка: {error_msg}',
                                'status_code': status.HTTP_400_BAD_REQUEST
                            }
                        elif 'balance' in error_msg.lower() or 'money' in error_msg.lower():
                            return {
                                'success': False,
                                'error': f'Ошибка отправки SMS: Недостаточно средств на балансе SMSC.ru. Ошибка: {error_msg}',
                                'status_code': status.HTTP_400_BAD_REQUEST
                            }
                        else:
                            return {
                                'success': False,
                                'error': f'Ошибка отправки SMS: {error_msg}',
                                'status_code': status.HTTP_400_BAD_REQUEST
                            }
                else:
                    # В тестовом режиме просто логируем
                    logger.info(f"Test mode: SMS code {sms_code} would be sent to {formatted_phone}")
            
            # Сохранение кода в кэше на 5 минут
            cache_key = f'sms_code_{identifier_type}_{identifier}'
            cache.set(cache_key, sms_code, timeout=300)
            
            # Сохранение информации о пользователе в кэше
            cache.set(f'user_exists_{identifier_type}_{identifier}', user_exists, timeout=300)
            
            # Сохранение роли в кэше (только для новых пользователей)
            if role and not user_exists:
                cache.set(f'user_role_{identifier_type}_{identifier}', role, timeout=300)
            
            # Определяем сообщение в зависимости от типа отправки
            if identifier_type == 'email':
                message = 'Код подтверждения отправлен на email'
            else:
                message = 'SMS код отправлен'
            
            return {
                'success': True,
                'message': message,
                'identifier': identifier,
                'identifier_type': identifier_type,
                'phone': phone_number if identifier_type == 'phone' else None,
                'email': identifier if identifier_type == 'email' else None,
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
    def verify_sms_code(identifier: str, sms_code: str, identifier_type: str = 'phone', role: str = None) -> dict:
        """
        Проверка SMS кода
        
        Args:
            identifier (str): Номер телефона или email
            sms_code (str): SMS код
            identifier_type (str): Тип идентификатора ('phone' или 'email')
            role (str): Роль пользователя ('Driver' или 'Master') - только для новых пользователей
            
        Returns:
            dict: Результат
        """
        try:
            # Валидация роли
            if role and role not in ['Driver', 'Master']:
                return {
                    'success': False,
                    'error': 'Роль должна быть "Driver" или "Master"',
                    'status_code': status.HTTP_400_BAD_REQUEST
                }
            
            # Получение кода из кэша
            cache_key = f'sms_code_{identifier_type}_{identifier}'
            stored_code = cache.get(cache_key)
            
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
            user_exists = cache.get(f'user_exists_{identifier_type}_{identifier}', False)
            
            # Получение роли из кэша (для новых пользователей)
            cached_role = cache.get(f'user_role_{identifier_type}_{identifier}')
            if not role and cached_role:
                role = cached_role
            
            if user_exists:
                # Пользователь существует, найти его
                try:
                    if identifier_type == 'phone':
                        user = User.objects.prefetch_related('groups').get(phone_number=identifier)
                    else:  # email
                        user = User.objects.prefetch_related('groups').get(email=identifier)
                    created = False
                except User.DoesNotExist:
                    # Если пользователь не найден, создать нового
                    if identifier_type == 'phone':
                        user, created = User.objects.prefetch_related('groups').get_or_create(
                            phone_number=identifier,
                            defaults={
                                'username': f'user_{identifier}',
                                'email': f'{identifier}@example.com',
                                'first_name': 'User',
                                'last_name': identifier,
                                'is_verified': True
                            }
                        )
                        
                        # Назначение роли для нового пользователя
                        if created and role:
                            try:
                                group = Group.objects.get(name=role)
                                user.groups.add(group)
                            except Group.DoesNotExist:
                                logger.warning(f"Group {role} not found, skipping role assignment")
                    else:  # email
                        user, created = User.objects.prefetch_related('groups').get_or_create(
                            email=identifier,
                            defaults={
                                'username': f'user_{identifier.split("@")[0]}',
                                'phone_number': None,
                                'first_name': 'User',
                                'last_name': identifier.split("@")[0],
                                'is_verified': True
                            }
                        )
                        
                        # Назначение роли для нового пользователя
                        if created and role:
                            try:
                                group = Group.objects.get(name=role)
                                user.groups.add(group)
                            except Group.DoesNotExist:
                                logger.warning(f"Group {role} not found, skipping role assignment")
            else:
                # Пользователь не существует, создать нового
                if identifier_type == 'phone':
                    # Определение страны номера
                    if identifier.startswith('998'):
                        country = 'UZ'
                        display_name = f'UZ_{identifier[3:]}'  # Удаление 998
                    else:
                        country = 'RU'
                        display_name = f'RU_{identifier[1:]}'  # Удаление 7
                    
                    user, created = User.objects.prefetch_related('groups').get_or_create(
                        phone_number=identifier,
                        defaults={
                            'username': f'user_{identifier}',
                            'email': f'{identifier}@example.com',
                            'first_name': f'User_{country}',
                            'last_name': display_name,
                            'is_verified': True
                        }
                    )
                    
                    # Назначение роли для нового пользователя
                    if created and role:
                        try:
                            group = Group.objects.get(name=role)
                            user.groups.add(group)
                        except Group.DoesNotExist:
                            logger.warning(f"Group {role} not found, skipping role assignment")
                else:  # email
                    user, created = User.objects.prefetch_related('groups').get_or_create(
                        email=identifier,
                        defaults={
                            'username': f'user_{identifier.split("@")[0]}',
                            'phone_number': None,
                            'first_name': 'User',
                            'last_name': identifier.split("@")[0],
                            'is_verified': True
                        }
                    )
                    
                    # Назначение роли для нового пользователя
                    if created and role:
                        try:
                            group = Group.objects.get(name=role)
                            user.groups.add(group)
                        except Group.DoesNotExist:
                            logger.warning(f"Group {role} not found, skipping role assignment")
            
            # Создание JWT токена
            refresh = RefreshToken.for_user(user)
            access_token = refresh.access_token
            
            # Удаление кода из кэша
            cache.delete(cache_key)
            
            # Очистка кэша
            cache.delete(f'user_exists_{identifier_type}_{identifier}')
            cache.delete(f'user_role_{identifier_type}_{identifier}')
            
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
