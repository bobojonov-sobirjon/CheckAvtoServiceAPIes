from rest_framework import serializers
from apps.categories.models import Category


class CategorySerializer(serializers.ModelSerializer):

    class Meta:
        model = Category
        fields = ['id', 'name', 'type_category', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']