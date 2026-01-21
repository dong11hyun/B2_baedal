from django.contrib import admin
from .models import Order, Restaurant, Rider

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'status', 'restaurant', 'rider', 'created_at')
    list_filter = ('status',)

@admin.register(Restaurant)
class RestaurantAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'address')

@admin.register(Rider)
class RiderAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')