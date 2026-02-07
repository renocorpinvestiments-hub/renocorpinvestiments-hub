#apps/dashboard/urls.py
from .views import gifts_data_api
from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    # -----------------------------
    # Page Views
    # -----------------------------
    path('', views.home_view, name='home'),
    path('tasks/', views.tasks_view, name='tasks'),
    path('gifts/', views.gifts_view, name='gifts'),
    path('account/', views.account_view, name='account'),

    # -----------------------------
    # Action / AJAX Endpoints
    # -----------------------------
    path('account/subscribe/', views.subscribe_view, name='subscribe'),
    path('account/withdraw/', views.withdraw_view, name='withdraw'),
    path('account/change_password/', views.change_password_view, name='change_password'),
    path("logout/", views.logout_view, name="logout"), 
    path("api/gifts/", gifts_data_api, name="gifts_data_api"),
]
