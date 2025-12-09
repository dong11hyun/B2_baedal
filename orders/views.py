import time
import logging
import threading
from rest_framework import viewsets
from rest_framework.response import Response
from .models import Order
from .serializers import OrderV1Serializer

# 로그를 터미널에 찍기 위한 설정
logger = logging.getLogger('django')

class OrderV1ViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.all()
    serializer_class = OrderV1Serializer

    # PUT 요청이 오면 실행되는 함수 (정보 수정)
    def update(self, request, *args, **kwargs):
        order = self.get_object()
        new_status = request.data.get('status')
        
        thread_id = threading.get_ident()
        print(f"\n[Thread {thread_id}] 요청 도착! 주문번호:{order.id} / 현재상태:{order.status} -> 변경할상태:{new_status}")

        if new_status:
            # === [문제 지점] Race Condition 시뮬레이션 ===
            # DB에서 데이터를 읽은 후, 저장하기 직전에 시간이 걸린다고 가정합니다.
            # 이 3초 동안 다른 누군가가 상태를 바꿔버리면 덮어쓰기 문제가 발생합니다.
            print(f"[Thread {thread_id}] 처리중... (3초 대기)")
            time.sleep(3) 

            # DB를 다시 확인하지 않고 메모리에 있는 객체 그대로 저장
            order.status = new_status
            order.save()
            
            print(f"[Thread {thread_id}] 저장 완료! 최종상태:{order.status}\n")
            return Response({'status': order.status, 'message': '상태 변경 성공'})
            
        return super().update(request, *args, **kwargs)