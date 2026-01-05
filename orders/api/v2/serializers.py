from rest_framework import serializers
from orders.models import Order, Restaurant, Rider

class RestaurantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Restaurant
        fields = ['id', 'name', 'address']

class RiderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Rider
        fields = ['id', 'name']

class OrderV2Serializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = ['id', 'restaurant_name', 'status', 'created_at', 'version', 'restaurant', 'rider']
        read_only_fields = ['id', 'created_at', 'version']

class OrderCancellationSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=200, required=True)

class OrderPaymentSerializer(serializers.Serializer):
    payment_method = serializers.CharField(max_length=50)
    amount = serializers.IntegerField()

class OrderRejectionSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=200, required=True)

# Empty serializers for actions that don't need input body, strictly for documentation purposes
class OrderAcceptanceSerializer(serializers.Serializer):
    pass

class OrderPreparationCompleteSerializer(serializers.Serializer):
    pass

class OrderPickupSerializer(serializers.Serializer):
    pass

class OrderDeliverySerializer(serializers.Serializer):
    pass
