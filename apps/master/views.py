from rest_framework.views import APIView
from rest_framework import status
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from .models import Master, ServiceType
from .serializers import MasterSerializer, MasterCreateSerializer, ServiceTypeSerializer
from .permissions import IsMasterGroup


class MasterProfileView(APIView):
    """Профиль мастера - только для группы Master"""
    permission_classes = [IsMasterGroup]
    
    def get_object(self):
        """Получение профиля мастера текущего пользователя"""
        try:
            return Master.objects.get(user=self.request.user)
        except Master.DoesNotExist:
            return None
    
    @swagger_auto_schema(
        operation_description="Получить профиль мастера",
        security=[{'Bearer': []}],
        responses={
            200: openapi.Response(
                description="Профиль мастера",
                schema=MasterSerializer
            
    ),
            404: openapi.Response(description="Профиль мастера не найден"),
            403: openapi.Response(description="Нет прав доступа")
        },
        tags=['Masters']
    )
    def get(self, request):
        """Получение профиля мастера"""
        master = self.get_object()
        if not master:
            return Response(
                {'error': 'Профиль мастера не найден'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = MasterSerializer(master, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    @swagger_auto_schema(
        operation_description="Создать профиль мастера",
        security=[{'Bearer': []}],
        request_body=MasterCreateSerializer,
        responses={
            201: openapi.Response(
                description="Профиль мастера создан",
                schema=MasterSerializer
            
    ),
            400: openapi.Response(description="Неверные данные"),
            403: openapi.Response(description="Нет прав доступа")
        },
        tags=['Masters']
    )
    def post(self, request):
        """Создание профиля мастера"""
        # Проверка, что у пользователя еще нет профиля мастера
        if Master.objects.filter(user=request.user).exists():
            return Response(
                {'error': 'Профиль мастера уже существует'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = MasterCreateSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            master = serializer.save()
            response_serializer = MasterSerializer(master, context={'request': request})
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @swagger_auto_schema(
        operation_description="Обновить профиль мастера",
        security=[{'Bearer': []}],
        request_body=MasterSerializer,
        responses={
            200: openapi.Response(
                description="Профиль мастера обновлен",
                schema=MasterSerializer
            
    ),
            400: openapi.Response(description="Неверные данные"),
            404: openapi.Response(description="Профиль мастера не найден"),
            403: openapi.Response(description="Нет прав доступа")
        },
        tags=['Masters']
    )
    def put(self, request):
        """Полное обновление профиля мастера"""
        master = self.get_object()
        if not master:
            return Response(
                {'error': 'Профиль мастера не найден'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = MasterSerializer(master, data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @swagger_auto_schema(
        operation_description="Частичное обновление профиля мастера",
        security=[{'Bearer': []}],
        request_body=MasterSerializer,
        responses={
            200: openapi.Response(
                description="Профиль мастера обновлен",
                schema=MasterSerializer
            
    ),
            400: openapi.Response(description="Неверные данные"),
            404: openapi.Response(description="Профиль мастера не найден"),
            403: openapi.Response(description="Нет прав доступа")
        },
        tags=['Masters']
    )
    def patch(self, request):
        """Частичное обновление профиля мастера"""
        master = self.get_object()
        if not master:
            return Response(
                {'error': 'Профиль мастера не найден'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = MasterSerializer(master, data=request.data, partial=True, context={'request': request} )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @swagger_auto_schema(
        operation_description="Удалить профиль мастера",
        security=[{'Bearer': []}],
        responses={
            204: openapi.Response(description="Профиль мастера удален"
    ),
            404: openapi.Response(description="Профиль мастера не найден"),
            403: openapi.Response(description="Нет прав доступа")
        },
        tags=['Masters']
    )
    def delete(self, request):
        """Удаление профиля мастера"""
        master = self.get_object()
        if not master:
            return Response(
                {'error': 'Профиль мастера не найден'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        master.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    

class MasterServiceTypesView(APIView):
    """Типы услуг - только для группы Master"""
    permission_classes = [IsMasterGroup]
    
    @swagger_auto_schema(
        operation_description="Получить доступные типы услуг",
        security=[{'Bearer': []}],
        responses={
            200: openapi.Response(
                description="Список типов услуг",
                schema=ServiceTypeSerializer(many=True
    )
            ),
            403: openapi.Response(description="Нет прав доступа")
        },
        tags=['Masters']
    )
    def get(self, request):
        """Получение доступных типов услуг"""
        services = ServiceTypeSerializer.get_all_services()
        return Response(services, status=status.HTTP_200_OK)


class MasterAddServiceView(APIView):
    """Добавление услуги - только для группы Master"""
    permission_classes = [IsMasterGroup]
    
    @swagger_auto_schema(
        operation_description="Добавить услугу к профилю мастера",
        security=[{'Bearer': []}],
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'service_code': openapi.Schema(type=openapi.TYPE_STRING, description='Код услуги'
    )
            },
            required=['service_code']
        ),
        responses={
            200: openapi.Response(description="Услуга добавлена"),
            400: openapi.Response(description="Неверные данные"),
            403: openapi.Response(description="Нет прав доступа"),
            404: openapi.Response(description="Профиль мастера не найден")
        },
        tags=['Masters']
    )
    def post(self, request):
        """Добавление услуги к профилю мастера"""
        try:
            master = Master.objects.get(user=request.user)
            service_code = request.data.get('service_code')
            
            if not service_code:
                return Response(
                    {'error': 'Код услуги не указан'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Проверка валидности кода услуги
            valid_services = [choice[0] for choice in ServiceType.choices]
            if service_code not in valid_services:
                return Response(
                    {'error': 'Неверный код услуги'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            master.add_service(service_code)
            return Response({'message': 'Услуга добавлена'}, status=status.HTTP_200_OK)
            
        except Master.DoesNotExist:
            return Response(
                {'error': 'Профиль мастера не найден'}, 
                status=status.HTTP_404_NOT_FOUND
            )


class MasterRemoveServiceView(APIView):
    """Удаление услуги - только для группы Master"""
    permission_classes = [IsMasterGroup]
    
    @swagger_auto_schema(
        operation_description="Удалить услугу из профиля мастера",
        security=[{'Bearer': []}],
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'service_code': openapi.Schema(type=openapi.TYPE_STRING, description='Код услуги'
    )
            },
            required=['service_code']
        ),
        responses={
            200: openapi.Response(description="Услуга удалена"),
            400: openapi.Response(description="Неверные данные"),
            403: openapi.Response(description="Нет прав доступа"),
            404: openapi.Response(description="Профиль мастера не найден")
        },
        tags=['Masters']
    )
    def post(self, request):
        """Удаление услуги из профиля мастера"""
        try:
            master = Master.objects.get(user=request.user)
            service_code = request.data.get('service_code')
            
            if not service_code:
                return Response(
                    {'error': 'Код услуги не указан'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            master.remove_service(service_code)
            return Response({'message': 'Услуга удалена'}, status=status.HTTP_200_OK)
            
        except Master.DoesNotExist:
            return Response(
                {'error': 'Профиль мастера не найден'}, 
                status=status.HTTP_404_NOT_FOUND
            )


class MasterStatsView(APIView):
    """Статистика мастера - только для группы Master"""
    permission_classes = [IsMasterGroup]
    
    @swagger_auto_schema(
        operation_description="Получить статистику мастера",
        security=[{'Bearer': []}],
        responses={
            200: openapi.Response(
                description="Статистика мастера",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'completion_rate': openapi.Schema(type=openapi.TYPE_NUMBER
    ),
                        'reserved_amount': openapi.Schema(type=openapi.TYPE_NUMBER),
                        'services_count': openapi.Schema(type=openapi.TYPE_INTEGER),
                        'can_take_order': openapi.Schema(type=openapi.TYPE_BOOLEAN)
                    }
                )
            ),
            403: openapi.Response(description="Нет прав доступа"),
            404: openapi.Response(description="Профиль мастера не найден")
        },
        tags=['Masters']
    )
    def get(self, request):
        """Статистика мастера"""
        try:
            master = Master.objects.get(user=request.user)
            
            return Response({
                'completion_rate': master.completion_rate,
                'reserved_amount': float(master.reserved_amount),
                'services_count': len(master.services),
                'can_take_order': master.can_take_order(),
                'services': master.get_services_display()
            }, status=status.HTTP_200_OK)
            
        except Master.DoesNotExist:
            return Response(
                {'error': 'Профиль мастера не найден'}, 
                status=status.HTTP_404_NOT_FOUND
            )