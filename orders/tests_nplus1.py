from django.test import TestCase
from rest_framework.test import APIClient
from orders.models import Order, Restaurant, Rider

class NPlusOneTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        
        # 데이터 생성
        self.restaurant1 = Restaurant.objects.create(name="치킨집 1호점", address="서울시 강남구")
        self.restaurant2 = Restaurant.objects.create(name="피자집 1호점", address="서울시 서초구")
        
        self.rider1 = Rider.objects.create(name="배달원 김씨")
        self.rider2 = Rider.objects.create(name="배달원 이씨")
        
        # 주문 10개 생성 (5개씩 각 식당/라이더)
        for i in range(5):
            Order.objects.create(
                restaurant=self.restaurant1,
                rider=self.rider1,
                status=Order.Status.DELIVERED
            )
        for i in range(5):
            Order.objects.create(
                restaurant=self.restaurant2,
                rider=self.rider2,
                status=Order.Status.DELIVERED
            )

    def test_n_plus_one_without_include(self):
        # include 없이 호출 시 쿼리 확인
        # 기본적으로 select_related를 안하므로, 만약 serializer에서 restaurant.name을 접근한다면 
        # N+1이 터지겠지만, 현재 OrderV2Serializer에는 'restaurant', 'rider' 필드가 그냥 ID만 나감 (ModelSerializer 기본).
        # 하지만 만약 Serializer를 바꿔서 name을 찍게 했다면 문제가 됨.
        # 여기서는 Side-loading 방식이므로, 기본 호출은 Order 테이블만 조회해야 함.
        
        with self.assertNumQueries(1): # Order 목록 조회 1회
            res = self.client.get('/api/v2/orders/')
            
        self.assertEqual(res.status_code, 200)
        # DRF PageNumberPagination이 있으면 count 쿼리가 추가될 수 있음.
        # 설정에 따라 2회가 될 수도 있음. (count + select)
        # 여기서는 assertNumQueries 범위가 좀 유연해야 할 수도.
        
    def test_side_loading_and_query_optimization(self):
        # ?include=restaurant,rider 호출
        # 예상: 
        # 1. Count Query (Pagination)
        # 2. Main Query (Order JOIN Restaurant JOIN Rider) - select_related 덕분
        # 총 2회 (혹은 pagination 없으면 1회)
        
        # 주의: assertNumQueries는 정확한 숫자를 요구함.
        # Pagination이 켜져있다면 count(*) 쿼리가 하나 더 나감.
        
        with self.assertNumQueries(1): 
            res = self.client.get('/api/v2/orders/?include=restaurant,rider')
            
        self.assertEqual(res.status_code, 200)
        data = res.json()
        
        # 응답 구조 확인
        self.assertIn('results', data)
        self.assertIn('included', data)
        
        included = data['included']
        self.assertIn('restaurants', included)
        self.assertIn('riders', included)
        
        self.assertEqual(len(included['restaurants']), 2) # 식당 2개
        self.assertEqual(len(included['riders']), 2) # 라이더 2개
        
        print("\n[N+1 Test] Side-loading Structure Verified:")
        print(f"Restaurants: {len(included['restaurants'])}")
        print(f"Riders: {len(included['riders'])}")
