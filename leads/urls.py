from django.urls import path
from .views import (
    login_view,
    register_view,
    home,
    loginberhasil,
    dashboard_analisis,
    distribusi_lead_page,
    update_leads_page,
    api_login,
    api_create_lead,
    api_assign_lead,
    api_update_lead_status,
    api_dashboard,
    # TAMBAHAN BARU:
    api_distribusi_stats,
    api_distribusi_leads,
    api_sales_list,
    input_manual_page
)

urlpatterns = [
    path('login/', login_view, name='login'),
    path('register/', register_view, name='register'),
    path('', home, name="home"),
    path('berhasil/', loginberhasil, name="login_berhasil"),

    path('dashboard/', dashboard_analisis, name='dashboard_analisis'),
    path('distribusi/', distribusi_lead_page, name='distribusi_lead'),
    path('update-leads/', update_leads_page, name='update_leads'),
    path('input-manual/', input_manual_page, name='input_manual'),

    path('api/login/', api_login, name='api_login'),
    path('api/leads/', api_create_lead, name='api_create_lead'),
    path('api/assign/', api_assign_lead, name='api_assign_lead'),
    path('api/leads/update-status/', api_update_lead_status, name='api_update_lead_status'),
    path('api/dashboard/', api_dashboard, name='api_dashboard'),

    path('api/distribusi/stats/', api_distribusi_stats, name='api_distribusi_stats'),
    path('api/distribusi/leads/', api_distribusi_leads, name='api_distribusi_leads'),
    path('api/sales/', api_sales_list, name='api_sales_list'),
]