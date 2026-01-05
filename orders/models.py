from django.db import models

class Order(models.Model):
    # 주문 상태 정의
    class Status(models.TextChoices):
        PENDING_PAYMENT = 'pending_payment', '결제 대기'
        PENDING_ACCEPTANCE = 'pending_acceptance', '주문 접수 대기'
        PREPARING = 'preparing', '조리중'
        READY_FOR_PICKUP = 'ready_for_pickup', '픽업 대기'
        CANCELLED = 'cancelled', '주문 취소' # 고객 취소
        REJECTED = 'rejected', '주문 거절' # 사장님 거절
        IN_TRANSIT = 'in_transit', '배달중'
        DELIVERED = 'delivered', '배달 완료'

    # 간단하게 구현하기 위해 레스토랑 정보 등은 생략하고 상태에 집중합니다.
    restaurant_name = models.CharField(max_length=100, default="맛있는 치킨집")
    status = models.CharField(
        max_length=20, 
        choices=Status.choices, 
        default=Status.PENDING_PAYMENT
    )
    created_at = models.DateTimeField(auto_now_add=True)
    version = models.IntegerField(default=1) # 낙관적 락을 위한 버전 필드

    def __str__(self):
        return f"Order {self.id} ({self.status})"