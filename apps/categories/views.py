from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from apps.categories.models import Category
from apps.categories.serializers import CategorySerializer
from rest_framework.permissions import AllowAny

from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi


class CategoryListAPIView(APIView):
    permission_classes = [AllowAny]
    
    @swagger_auto_schema(
        operation_description="Получить список всех категорий с возможностью фильтрации по типу",
        security=[{'Bearer': []}],
        manual_parameters=[
            openapi.Parameter(
                'type',
                openapi.IN_QUERY,
                description="Фильтр по типу категории (by_master, by_car)",
                type=openapi.TYPE_STRING,
                enum=['by_master', 'by_car', 'by_order'],
                required=False
            )
        ],
        responses={
            200: openapi.Response(
                description="Список категорий", 
                schema=CategorySerializer
            )
        },
        tags=['Categories']
    )
    def get(self, request):
        type_filter = request.query_params.get('type')
        
        if type_filter == 'by_master':
            categories = Category.by_master.all()
        elif type_filter == 'by_car':
            categories = Category.by_car.all()
        elif type_filter == 'by_order':
            categories = Category.by_order.all()
        else:
            categories = Category.objects.all()
        
        serializer = CategorySerializer(categories, many=True, context={'request': request})
        return Response(serializer.data)