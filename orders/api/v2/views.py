from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from orders.models import Order
from orders.api.v2.serializers import (
    OrderV2Serializer,
    OrderCancellationSerializer,
    OrderPaymentSerializer,
    OrderAcceptanceSerializer,
    OrderPickupSerializer,
    OrderDeliverySerializer,
    OrderRejectionSerializer,
    OrderPreparationCompleteSerializer
)
import time
import hashlib

from orders.decorators import idempotent

class OrderV2ViewSet(viewsets.ReadOnlyModelViewSet):
    """
    V2 API: Action-oriented Resources with Optimistic Locking
    """
    queryset = Order.objects.all()
    serializer_class = OrderV2Serializer

    def get_etag(self, order):
        # ETag 생성 로직: "order-{id}-v{version}"의 해시
        raw_data = f"order-{order.id}-v{order.version}"
        return hashlib.md5(raw_data.encode()).hexdigest()

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        
        # ?include=restaurant,rider 처리
        include_params = request.query_params.get('include', '').split(',')
        include_params = [param.strip() for param in include_params if param]
        
        # N+1 문제 해결을 위해 select_related 사용
        if 'restaurant' in include_params and 'rider' in include_params:
            queryset = queryset.select_related('restaurant', 'rider')
        elif 'restaurant' in include_params:
            queryset = queryset.select_related('restaurant')
        elif 'rider' in include_params:
            queryset = queryset.select_related('rider')

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            data = serializer.data
        else:
            serializer = self.get_serializer(queryset, many=True)
            data = serializer.data

        # 기본 응답 구조
        response_data = {
            "results": data
        }

        # Side-loading Data 추가
        if include_params:
            included = {}
            if 'restaurant' in include_params:
                # 중복 제거하여 Restaurant 목록 추출
                restaurant_ids = set()
                restaurants = []
                for order in (page if page else queryset):
                     if order.restaurant and order.restaurant.id not in restaurant_ids:
                         restaurant_ids.add(order.restaurant.id)
                         restaurants.append({
                             "id": order.restaurant.id,
                             "name": order.restaurant.name,
                             "address": order.restaurant.address
                         })
                included['restaurants'] = restaurants

            if 'rider' in include_params:
                rider_ids = set()
                riders = []
                for order in (page if page else queryset):
                     if order.rider and order.rider.id not in rider_ids:
                         rider_ids.add(order.rider.id)
                         riders.append({
                             "id": order.rider.id,
                             "name": order.rider.name
                         })
                included['riders'] = riders
            
            response_data['included'] = included
            
        return Response(response_data)

    def retrieve(self, request, *args, **kwargs):
        # 상세 조회에서도 동일하게 지원 가능여부는 선택사항. 여기선 리스트 위주로 구현.
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        response = Response(serializer.data)
        response['ETag'] = f'"{self.get_etag(instance)}"'
        return response

    def check_etag(self, request, order):
        if_match = request.headers.get('If-Match')
        if not if_match:
            # If-Match 헤더가 없으면 412가 아니라 428 Precondition Required를 줄 수도 있지만,
            # 여기서는 편의상 진행하거나 400을 줍니다. 과제 요구사항에 따라 필수로 합니다.
            # 하지만 테스트 편의를 위해 일단 없으면 패스하는 경우도 있지만,
            # 낙관적 락 강제를 위해 필수로 하겠습니다.
            return False, Response(
                {"error": "If-Match header is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # If-Match 헤더의 따옴표 제거
        if_match = if_match.strip('"')
        current_etag = self.get_etag(order)
        
        if if_match != current_etag:
            return False, Response(
                {
                    "error": "Precondition Failed", 
                    "message": "The resource has been modified by another request.",
                    "current_version": order.version
                },
                status=status.HTTP_412_PRECONDITION_FAILED
            )
        return True, None

    def perform_action_with_locking(self, request, action_func):
        order = self.get_object()
        
        # Optimistic Locking Check
        is_valid, error_response = self.check_etag(request, order)
        if not is_valid:
            return error_response
            
        response = action_func(request, order)
        
        # 상태가 변경되었다면 버전 증가 및 저장 (action_func 내부에서 save() 하지 말고 여기서 처리)
        # 하지만 action_func 내부 로직이 복잡할 수 있으니, 
        # action_func에서 business logic만 수행하고 여기서 save하는 패턴으로 리팩토링합니다.
        # 또는 action_func에서 save() 하고 버전을 증가시킵니다.
        
        return response

    @idempotent
    @action(detail=True, methods=['post'], url_path='payment')
    def payment(self, request, pk=None):
        order = self.get_object()
        
        # ETag Check
        is_valid, error_response = self.check_etag(request, order)
        if not is_valid: return error_response

        if order.status != Order.Status.PENDING_PAYMENT:
            return Response({"error": "Invalid state"}, status=status.HTTP_400_BAD_REQUEST)
            
        order.status = Order.Status.PENDING_ACCEPTANCE
        # 버전 증가
        order.version += 1
        time.sleep(0.5)
        order.save()
        
        response = Response(OrderV2Serializer(order).data)
        response['ETag'] = f'"{self.get_etag(order)}"'
        return response

    @action(detail=True, methods=['post'], url_path='cancellation')
    def cancellation(self, request, pk=None):
        order = self.get_object()
        
        # ETag Check
        is_valid, error_response = self.check_etag(request, order)
        if not is_valid: return error_response

        allowed_statuses = [Order.Status.PENDING_PAYMENT, Order.Status.PENDING_ACCEPTANCE]
        if order.status not in allowed_statuses:
             return Response({"error": "Cannot cancel"}, status=status.HTTP_400_BAD_REQUEST)

        order.status = Order.Status.CANCELLED
        order.version += 1
        order.save()
        
        response = Response(OrderV2Serializer(order).data)
        response['ETag'] = f'"{self.get_etag(order)}"'
        return response

    @action(detail=True, methods=['post'], url_path='acceptance')
    def acceptance(self, request, pk=None):
        order = self.get_object()
        
        # ETag Check
        is_valid, error_response = self.check_etag(request, order)
        if not is_valid: return error_response
        
        if order.status != Order.Status.PENDING_ACCEPTANCE:
             return Response({"error": "Invalid state"}, status=status.HTTP_400_BAD_REQUEST)
            
        order.status = Order.Status.PREPARING
        order.version += 1
        order.save()
        
        response = Response(OrderV2Serializer(order).data)
        response['ETag'] = f'"{self.get_etag(order)}"'
        return response

    @action(detail=True, methods=['post'], url_path='rejection')
    def rejection(self, request, pk=None):
        order = self.get_object()
        
        # ETag Check
        is_valid, error_response = self.check_etag(request, order)
        if not is_valid: return error_response

        if order.status != Order.Status.PENDING_ACCEPTANCE:
             return Response({"error": "Invalid state"}, status=status.HTTP_400_BAD_REQUEST)
        
        order.status = Order.Status.REJECTED
        order.version += 1
        order.save()
        
        response = Response(OrderV2Serializer(order).data)
        response['ETag'] = f'"{self.get_etag(order)}"'
        return response

    @action(detail=True, methods=['post'], url_path='preparation-complete')
    def preparation_complete(self, request, pk=None):
        order = self.get_object()
        
        # ETag Check
        is_valid, error_response = self.check_etag(request, order)
        if not is_valid: return error_response

        if order.status != Order.Status.PREPARING:
             return Response({"error": "Invalid state"}, status=status.HTTP_400_BAD_REQUEST)
        
        order.status = Order.Status.READY_FOR_PICKUP
        order.version += 1
        order.save()
        
        response = Response(OrderV2Serializer(order).data)
        response['ETag'] = f'"{self.get_etag(order)}"'
        return response

    @action(detail=True, methods=['post'], url_path='pickup')
    def pickup(self, request, pk=None):
        order = self.get_object()
        
        # ETag Check
        is_valid, error_response = self.check_etag(request, order)
        if not is_valid: return error_response

        if order.status != Order.Status.READY_FOR_PICKUP:
             return Response({"error": "Invalid state"}, status=status.HTTP_400_BAD_REQUEST)
        
        order.status = Order.Status.IN_TRANSIT
        order.version += 1
        order.save()
        
        response = Response(OrderV2Serializer(order).data)
        response['ETag'] = f'"{self.get_etag(order)}"'
        return response

    @action(detail=True, methods=['post'], url_path='delivery')
    def delivery(self, request, pk=None):
        order = self.get_object()
        
        # ETag Check
        is_valid, error_response = self.check_etag(request, order)
        if not is_valid: return error_response

        if order.status != Order.Status.IN_TRANSIT:
             return Response({"error": "Invalid state"}, status=status.HTTP_400_BAD_REQUEST)

        order.status = Order.Status.DELIVERED
        order.version += 1
        order.save()
        
        response = Response(OrderV2Serializer(order).data)
        response['ETag'] = f'"{self.get_etag(order)}"'
        return response
