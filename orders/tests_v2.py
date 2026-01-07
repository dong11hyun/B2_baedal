from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from orders.models import Order

class OrderV2ActionTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.order = Order.objects.create(status=Order.Status.PENDING_PAYMENT)
        self.url_base = '/orders/api/v2/orders' 
    
    def get_etag(self, order):
        import hashlib
        raw_data = f"order-{order.id}-v{order.version}"
        return f'"{hashlib.md5(raw_data.encode()).hexdigest()}"'

    def test_payment_action(self):
        url = reverse('order-v2-payment', args=[self.order.id])
        data = {'payment_method': 'card', 'amount': 20000}
        headers = {'HTTP_IF_MATCH': self.get_etag(self.order)}
        response = self.client.post(url, data, **headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.Status.PENDING_ACCEPTANCE)

    def test_cancellation_success(self):
        url = reverse('order-v2-cancellation', args=[self.order.id])
        data = {'reason': 'Changed mind'}
        headers = {'HTTP_IF_MATCH': self.get_etag(self.order)}
        response = self.client.post(url, data, **headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.Status.CANCELLED)

    def test_rejection_success(self):
        # Pending payment -> PENDING_ACCEPTANCE
        self.order.status = Order.Status.PENDING_ACCEPTANCE
        self.order.save()
        
        url = reverse('order-v2-rejection', args=[self.order.id])
        data = {'reason': 'Out of stock'}
        headers = {'HTTP_IF_MATCH': self.get_etag(self.order)}
        response = self.client.post(url, data, **headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.Status.REJECTED)

    def test_acceptance_flow(self):
        self.order.status = Order.Status.PENDING_ACCEPTANCE
        self.order.save()
        
        url = reverse('order-v2-acceptance', args=[self.order.id])
        headers = {'HTTP_IF_MATCH': self.get_etag(self.order)}
        response = self.client.post(url, **headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.Status.PREPARING)

    def test_preparation_complete_success(self):
        self.order.status = Order.Status.PREPARING
        self.order.save()
        
        url = reverse('order-v2-preparation-complete', args=[self.order.id])
        headers = {'HTTP_IF_MATCH': self.get_etag(self.order)}
        response = self.client.post(url, **headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.Status.READY_FOR_PICKUP)

    def test_pickup_success(self):
        # PREPARING -> READY_FOR_PICKUP
        self.order.status = Order.Status.READY_FOR_PICKUP
        self.order.save()
        
        url = reverse('order-v2-pickup', args=[self.order.id])
        headers = {'HTTP_IF_MATCH': self.get_etag(self.order)}
        response = self.client.post(url, **headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.Status.IN_TRANSIT)

    def test_delivery_success(self):
        self.order.status = Order.Status.IN_TRANSIT
        self.order.save()
        
        url = reverse('order-v2-delivery', args=[self.order.id])
        headers = {'HTTP_IF_MATCH': self.get_etag(self.order)}
        response = self.client.post(url, **headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, Order.Status.DELIVERED)
