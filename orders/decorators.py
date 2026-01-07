import functools
from rest_framework.response import Response
from rest_framework import status
from .models import IdempotencyKey
import uuid

def idempotent(func):
    @functools.wraps(func)
    def wrapper(view_set, request, *args, **kwargs):
        # 1. 헤더에서 Idempotency-Key 추출
        idem_key = request.headers.get('Idempotency-Key')
        
        # 키가 없으면 멱등성 보장 없이 그냥 실행 (또는 400 에러 - 여기선 선택)
        # README 요구사항에 따라 멱등성 보장을 위해 키가 있으면 로직 수행
        if not idem_key:
            # 키가 없어서 그냥 통과시킴
            return func(view_set, request, *args, **kwargs)

        try:
            # UUID 형식 검증 (선택사항이나 안전을 위해)
            uuid_key = uuid.UUID(idem_key)
        except ValueError:
             return Response({"error": "Invalid Idempotency-Key format. Must be UUID."}, status=status.HTTP_400_BAD_REQUEST)

        # 2. 키가 이미 존재하는지 확인
        existing_key = IdempotencyKey.objects.filter(key=uuid_key).first()
        if existing_key:
            # 존재하면 저장된 응답 반환
            return Response(existing_key.response_body, status=existing_key.response_status)

        # 3. 존재하지 않으면 실제 로직 실행
        response = func(view_set, request, *args, **kwargs)

        # 4. 성공 응답(2xx)인 경우에만 저장? 또는 모든 응답 저장?
        # 보통은 부작용이 발생한 성공 케이스를 저장하여 재시도 막음.
        # 실패(4xx, 5xx)는 저장 여부 정책 나름.
        # 요구사항: "네트워크 오류 발생 시... 중복 처리 방지" -> 성공했으면 저장해서 중복 방지.
        
        if 200 <= response.status_code < 300:
            IdempotencyKey.objects.create(
                key=uuid_key,
                response_status=response.status_code,
                response_body=response.data
            )
            
        return response
    return wrapper
