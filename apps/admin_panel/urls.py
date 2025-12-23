from django.urls import path
from . import views

app_name = "admin_panel"

urlpatterns = [
    # Admin auth
    path('login/', views.admin_login, name='login'),
    path('logout/', views.admin_logout, name='logout'),

    # Dashboard
    path('dashboard/', views.admin_dashboard, name='dashboard'),

    # Manual user creation / OTP
    path('manual-login/', views.manual_login, name='manual_login'),
    path('verify-otp/', views.verify_otp, name='verify_otp'),

    # Gift offers management
    path('gift-offers/', views.gift_offer_list, name='gift_offer_list'),
    path('gift-offers/add/', views.gift_offer_create, name='gift_offer_create'),
    path('gift-offers/<str:pk>/edit/', views.gift_offer_edit, name='gift_offer_edit'),  # Fixed to str
    path('gift-offers/<str:pk>/delete/', views.gift_offer_delete, name='gift_offer_delete'),  # Fixed to str

    # Task control
    path('tasks/', views.task_control_view, name='task_control'),

    # Payroll management
    path('payrolls/', views.payroll_list, name='payroll_list'),
    path('payrolls/add/', views.payroll_add, name='payroll_add'),
    path('payrolls/<int:pk>/edit/', views.payroll_edit, name='payroll_edit'),
    path('payrolls/<int:pk>/delete/', views.payroll_delete, name='payroll_delete'),

    # Admin settings
    path('settings/', views.admin_settings_view, name='settings'),

    # Graphs / analytics
    path('graphs/', views.graphs_view, name='graphs'),
]