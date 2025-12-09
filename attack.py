import threading
import requests
import time

# 방금 만든 주문의 주소 (ID가 1번이라고 가정)
# 주의: 주소 끝에 슬래시(/)가 있어야 합니다.
URL = "http://127.0.0.1:8000/api/v1/orders/1/"

def customer_cancel():
    print("🙋 [고객] '취소해주세요!' 요청 보냄")
    # 고객은 'cancelled'로 상태 변경 요청
    res = requests.put(URL, json={'status': 'cancelled'})
    print(f"🙋 [고객] 응답 받음: {res.json()['status']}")

def restaurant_accept():
    print("👨‍🍳 [사장님] '주문 접수!' 요청 보냄")
    # 사장님은 'preparing'(조리중)으로 상태 변경 요청
    res = requests.put(URL, json={'status': 'preparing'})
    print(f"👨‍🍳 [사장님] 응답 받음: {res.json()['status']}")

# --- 시나리오 시작 ---
print("=== 🔥 동시성 테스트 시작 (Race Condition) 🔥 ===")

# 두 개의 스레드(Thread)를 생성하여 동시에 실행 준비
t1 = threading.Thread(target=customer_cancel)
t2 = threading.Thread(target=restaurant_accept)

# 거의 동시에 실행!
t1.start()
t2.start()

# 두 작업이 다 끝날 때까지 대기
t1.join()
t2.join()

# 최종 결과 확인
print("\n=== 🔍 최종 결과 확인 ===")
final_res = requests.get(URL).json()
print(f"DB에 저장된 최종 상태: {final_res['status']}")

if final_res['status'] == 'preparing':
    print("😱 [결론] 망했습니다. 고객은 취소한 줄 아는데, 주방에선 치킨을 튀기고 있습니다. (사장님 승리)")
elif final_res['status'] == 'cancelled':
    print("😱 [결론] 망했습니다. 사장님은 접수된 줄 알고 치킨을 튀기는데, 사실 취소된 주문입니다. (고객 승리)")