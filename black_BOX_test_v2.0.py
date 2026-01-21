import threading
import requests
import time
import sys
import uuid

# 서버 주소
BASE_URL = "http://127.0.0.1:8000"

def create_order():
    resp = requests.post(f"{BASE_URL}/api/orders/", json={
        "restaurant_name": "치킨집",
        "status": "pending_payment"
    })
    if resp.status_code == 201:
        return resp.json()['id']
    else:
        print("주문 생성 실패:", resp.text)
        sys.exit(1)

def get_order_v2(order_id):
    resp = requests.get(f"{BASE_URL}/api/v2/orders/{order_id}/")
    return resp.json(), resp.headers.get('ETag')

# --- 시나리오 시작 ---
print("=== 멱등성 테스트 시작 (Idempotency) ===")

# 1. 주문 생성
ORDER_ID = create_order()
print(f"테스트용 주문 생성 완료: ID {ORDER_ID}")

# 2. 초기 상태 확인
order_info, etag = get_order_v2(ORDER_ID)
print(f"초기 상태: {order_info['status']}")

# 3. 멱등성 키 생성
idem_key = str(uuid.uuid4())
print(f"생성된 Idempotency-Key: {idem_key}")

# 4. 첫 번째 결제 요청 (정상 처리되어야 함)
print("\n[요청 1] 첫 번째 결제 요청 전송...")
headers = {
    'If-Match': etag,
    'Idempotency-Key': idem_key
}
res1 = requests.post(f"{BASE_URL}/api/v2/orders/{ORDER_ID}/payment/", headers=headers, json={'payment_method':'card', 'amount':20000})

if res1.status_code == 200:
    print(f"[결과 1] 성공 (200 OK). 상태: {res1.json()['status']}")
    print(f"응답 본문: {res1.json()}")
else:
    print(f"[결과 1] 실패: {res1.status_code} - {res1.text}")
    sys.exit(1)

# 5. 두 번째 결제 요청 (동일한 키 사용 -> 저장된 응답 반환되어야 함)
# 만약 멱등성이 없다면: 
#   - 이미 status가 pending_acceptance라서 'Invalid state transition' 에러(400)가 뜨거나
#   - ETag가 변경되어서 'Precondition Failed'(412)가 떠야 함.
#   - 또는 로직이 중복 실행되어 엉뚱한 결과 초래.
# 멱등성이 있다면:
#   - 첫 번째와 '정확히 동일한' 200 응답이 와야 함.

print("\n[요청 2] 두 번째 결제 요청 전송 (동일 키)...")
# ETag는 첫 번째 요청 후 변경되었겠지만, 멱등성 로직이 먼저 동작하면 ETag 체크 전에 캐시된 응답을 줄 것임.
# (데코레이터 위치가 action 메서드 위이므로, 메서드 내부의 ETag 체크보다 먼저 실행됨)
# 따라서 헤더에 옛날 ETag를 넣든 새 ETag를 넣든 상관없이 저장된 응답이 와야 함.
# 테스트를 위해 '틀린 ETag' (첫번째때 썼던거) 그대로 보내봄.

res2 = requests.post(f"{BASE_URL}/api/v2/orders/{ORDER_ID}/payment/", headers=headers, json={'payment_method':'card', 'amount':20000})

if res2.status_code == 200:
    print(f"[결과 2] 성공 (200 OK).")
    print(f"응답 본문: {res2.json()}")
    
    if res1.json() == res2.json():
        print("✅ [검증] 응답 본문이 첫 번째와 완전히 동일함. (시간, 상태 등)")
    else:
        print("❌ [검증] 응답 본문이 다름.")
        
    # 만약 실제 로직이 다시 돌았다면 version이 증가했을 텐데, 
    # 저장된 응답을 줬다면 version이 그대로일 것임.
    # (Serializer에 version 필드 추가했으므로 확인 가능)
    v1 = res1.json().get('version')
    v2 = res2.json().get('version')
    if v1 == v2:
        print(f"✅ [검증] Version 변화 없음 ({v1} -> {v2}). 멱등성 동작 확인!")
    else:
        print(f"❌ [검증] Version이 변경됨 ({v1} -> {v2}). 중복 처리 발생!")

else:
    print(f"[결과 2] 실패 (기대치 않음): {res2.status_code} - {res2.text}")
    if res2.status_code == 412:
        print("-> 멱등성 체크보다 낙관적 락 체크가 먼저 일어났거나, 멱등성 키 저장을 못 찾음.")
    elif res2.status_code == 400:
        print("-> 멱등성 체크 실패로 인해 비즈니스 로직(상태 검증)이 실행됨.")

