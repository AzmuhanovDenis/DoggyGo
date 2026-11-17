from django.urls import path
from . import views


urlpatterns = [
    path('', views.index, name='index'),
    path('how-it-works/', views.how_it_works, name='how_it_works'),
    path('sitters/', views.sitter_catalog, name='catalog'),
    path('sitters/<int:pk>/', views.sitter_detail, name='sitter_detail'),
    path('profile/dogs/', views.my_dogs, name='my_dogs'),
    path('profile/dogs/<int:pk>/edit/', views.edit_dog, name='edit_dog'),
    path('profile/dogs/<int:pk>/delete/', views.delete_dog, name='delete_dog'),
    path('profile/orders/', views.my_orders, name='my_orders'),
    path('profile/orders/<int:pk>/', views.order_detail, name='order_detail'),
    path('profile/orders/<int:pk>/receipt/', views.order_receipt, name='order_receipt'),
    path('analytics/', views.analytics, name='analytics'),
    path('analytics/export-csv/', views.analytics_export_csv, name='analytics_export_csv'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.register_view, name='register'),
]
