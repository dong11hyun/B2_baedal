import threading
import requests
import time
import sys

# 서버 주소
BASE_URL = "http://127.0.0.1:8000"

def create_order():
    # V1 API를 사용하여 주문 생성 (테스트 데이터 준비)
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

def customer_cancel(order_id, etag):
    print(f"[고객] '취소해주세요!' 요청 보냄 (ETag: {etag})")
    headers = {'If-Match': etag} if etag else {}
    # V2 행위 기반 API 호출
    res = requests.post(f"{BASE_URL}/api/v2/orders/{order_id}/cancellation/", headers=headers, json={'reason': '변심'})
    
    if res.status_code == 200:
        print(f"[고객] 성공! 상태: {res.json()['status']}")
    elif res.status_code == 412:
        print(f"[고객] 실패! (412 Precondition Failed) - 누군가 먼저 선수쳤네요.")
    else:
        print(f"[고객] 오류: {res.status_code} - {res.text}")

def restaurant_accept(order_id, etag):
    print(f"[사장님] '주문 접수!' 요청 보냄 (ETag: {etag})")
    headers = {'If-Match': etag} if etag else {}
    # V2 행위 기반 API 호출
    res = requests.post(f"{BASE_URL}/api/v2/orders/{order_id}/acceptance/", headers=headers)
    
    if res.status_code == 200:
        print(f"[사장님] 성공! 상태: {res.json()['status']}")
    elif res.status_code == 412:
        print(f"[사장님] 실패! (412 Precondition Failed) - 이미 취소되었거나 변경된 주문입니다.")
    else:
        print(f"[사장님] 오류: {res.status_code} - {res.text}")

# --- 시나리오 시작 ---
print("=== 동시성 테스트 시작 (Optimistic Locking) ===")

# 1. 주문 생성
ORDER_ID = create_order()
print(f"테스트용 주문 생성 완료: ID {ORDER_ID}")

# 2. 초기 상태 조회 (ETag 획득)
# 결제 대기 상태에서 시작하므로, 먼저 '결제'를 진행하여 '접수 대기' 상태로 만들어야 
# 취소(cancellation)와 접수(acceptance) 간의 경쟁을 테스트할 수 있음.
# 하지만 V2 cancellation은 pending_payment에서도 가능.
# V2 acceptance는 pending_acceptance에서만 가능.
# 따라서 시나리오를 수정해야 함.
# README 시나리오는 "고객 취소" vs "사장 접수".
# 사장 접수가 가능하려면 상태가 'pending_acceptance'여야 함.
# 따라서 먼저 결제를 완료시켜야 함.

print("\n[사전 작업] 결제 진행 (V2 Payment)")
order_info, etag = get_order_v2(ORDER_ID)
res = requests.post(f"{BASE_URL}/api/v2/orders/{ORDER_ID}/payment/", headers={'If-Match': etag}, json={'payment_method':'card', 'amount':20000})
if res.status_code != 200:
    print("결제 실패, 테스트 중단")
    sys.exit(1)
print("결제 완료. 상태: pending_acceptance")

# 3. 레이스 컨디션 준비
# 두 클라이언트(고객, 사장)가 동시에 조회했다고 가정 (동일한 ETag 보유)
order_info, initial_etag = get_order_v2(ORDER_ID)
print(f"\n[초기 상태] ETag: {initial_etag}")

t1 = threading.Thread(target=customer_cancel, args=(ORDER_ID, initial_etag))
t2 = threading.Thread(target=restaurant_accept, args=(ORDER_ID, initial_etag))

# 4. 동시 실행
t1.start()
t2.start()

t1.join()
t2.join()

# 5. 최종 결과 확인
print("\n=== 🔍 최종 결과 확인 ===")
final_info, final_etag = get_order_v2(ORDER_ID)
print(f"최종 상태: {final_info['status']}")
print(f"최종 버전: {order_info.get('version')} (NOTE: API Response에 version 필드가 없다면 확인 불가)")
