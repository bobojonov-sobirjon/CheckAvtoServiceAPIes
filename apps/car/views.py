from rest_framework.views import APIView
from rest_framework import status
from rest_framework.response import Response
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from .models import Car
from .serializers import CarSerializer, CarCreateSerializer
from .permissions import IsDriverGroup


class CarListCreateView(APIView):
    """Список и создание машин - только для группы Driver"""
    permission_classes = [IsDriverGroup]
    
    def get_queryset(self):
        """Получение только машин текущего пользователя"""
        return Car.objects.filter(user=self.request.user)
    
    @swagger_auto_schema(
        operation_description="Получить список машин пользователя",
        security=[{'Bearer': []}],
        responses={
            200: openapi.Response(
                description="Список машин",
                schema=CarSerializer(many=True)
            ),
            403: openapi.Response(description="Нет прав доступа")
        },
        tags=['Cars']
    )
    def get(self, request):
        """Список машин пользователя"""
        cars = self.get_queryset()
        serializer = CarSerializer(cars, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    @swagger_auto_schema(
        operation_description="Создать новую машину",
        request_body=CarCreateSerializer,
        security=[{'Bearer': []}],
        responses={
            201: openapi.Response(
                description="Машина создана",
                schema=CarSerializer
            ),
            400: openapi.Response(description="Неверные данные"),
            403: openapi.Response(description="Нет прав доступа")
        },
        tags=['Cars']
    )
    def post(self, request):
        """Создание новой машины"""
        serializer = CarCreateSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            car = serializer.save()
            response_serializer = CarSerializer(car, context={'request': request})
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    

class CarDetailView(APIView):
    """Детали, обновление и удаление машины - только для группы Driver"""
    permission_classes = [IsDriverGroup]
    
    def get_object(self, pk):
        """Получение машины пользователя по ID"""
        try:
            return Car.objects.get(pk=pk, user=self.request.user)
        except Car.DoesNotExist:
            return None
    
    @swagger_auto_schema(
        operation_description="Получить детали машины",
        security=[{'Bearer': []}],
        responses={
            200: openapi.Response(
                description="Детали машины",
                schema=CarSerializer
            ),
            404: openapi.Response(description="Машина не найдена"),
            403: openapi.Response(description="Нет прав доступа")
        },
        tags=['Cars']
    )
    def get(self, request, pk):
        """Детали машины"""
        car = self.get_object(pk)
        if not car:
            return Response(
                {'error': 'Машина не найдена'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = CarSerializer(car, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    @swagger_auto_schema(
        operation_description="Обновить машину",
        security=[{'Bearer': []}],
        request_body=CarSerializer,
        responses={
            200: openapi.Response(
                description="Машина обновлена",
                schema=CarSerializer
            ),
            400: openapi.Response(description="Неверные данные"),
            404: openapi.Response(description="Машина не найдена"),
            403: openapi.Response(description="Нет прав доступа")
        },
        tags=['Cars']
    )
    def put(self, request, pk):
        """Полное обновление машины"""
        car = self.get_object(pk)
        if not car:
            return Response(
                {'error': 'Машина не найдена'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = CarSerializer(car, data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @swagger_auto_schema(
        operation_description="Частичное обновление машины",
        security=[{'Bearer': []}],
        request_body=CarSerializer,
        responses={
            200: openapi.Response(
                description="Машина обновлена",
                schema=CarSerializer
            ),
            400: openapi.Response(description="Неверные данные"),
            404: openapi.Response(description="Машина не найдена"),
            403: openapi.Response(description="Нет прав доступа")
        },
        tags=['Cars']
    )
    def patch(self, request, pk):
        """Частичное обновление машины"""
        car = self.get_object(pk)
        if not car:
            return Response(
                {'error': 'Машина не найдена'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = CarSerializer(car, data=request.data, partial=True, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @swagger_auto_schema(
        operation_description="Удалить машину",
        security=[{'Bearer': []}],
        responses={
            204: openapi.Response(description="Машина удалена"),
            404: openapi.Response(description="Машина не найдена"),
            403: openapi.Response(description="Нет прав доступа")
        },
        tags=['Cars']
    )
    def delete(self, request, pk):
        """Удаление машины"""
        car = self.get_object(pk)
        if not car:
            return Response(
                {'error': 'Машина не найдена'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        
        car.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class CarStatsView(APIView):
    """Статистика машин пользователя - только для группы Driver"""
    permission_classes = [IsDriverGroup]
    
    def get_queryset(self):
        """Получение только машин текущего пользователя"""
        return Car.objects.filter(user=self.request.user)
    
    @swagger_auto_schema(
        operation_description="Получить статистику машин пользователя",
        security=[{'Bearer': []}],
        responses={
            200: openapi.Response(
                description="Статистика машин",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'total_cars': openapi.Schema(type=openapi.TYPE_INTEGER),
                        'cars_by_type': openapi.Schema(type=openapi.TYPE_OBJECT),
                        'cars_by_brand': openapi.Schema(type=openapi.TYPE_OBJECT)
                    }
                )
            ),
            403: openapi.Response(description="Нет прав доступа")
        },
        tags=['Cars']
    )
    def get(self, request):
        """Статистика машин пользователя"""
        cars = self.get_queryset()
        
        # Статистика по типам
        cars_by_type = {}
        for choice in Car.TypeCar.choices:
            cars_by_type[choice[1]] = cars.filter(type_car=choice[0]).count()
        
        # Статистика по маркам
        cars_by_brand = {}
        for car in cars:
            brand = car.brand or 'Не указано'
            cars_by_brand[brand] = cars_by_brand.get(brand, 0) + 1
        
        return Response({
            'total_cars': cars.count(),
            'cars_by_type': cars_by_type,
            'cars_by_brand': cars_by_brand
        }, status=status.HTTP_200_OK)