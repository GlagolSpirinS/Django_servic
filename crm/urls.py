from django.urls import path

from . import views
from .views import *

from ServiceRequest import views as ServiceRequest_views


urlpatterns = [
    path('user/', crm, name='crm'),
    path('api/user/<int:user_id>/', views.get_user_data, name='get_user_data'),
    path('api/user/update/', views.update_user, name='update_user'),
    path('api/user/toggle/', views.toggle_user, name='toggle_user'),
    path('api/user/self/', views.user_self, name='user_self'),
    path('request/', ServiceRequest_views.request_list, name='create_service_request'),
    path('api/service-requests/<int:request_id>/', ServiceRequest_views.service_request_api, name='service_request_api'),
    path('api/service-requests/<int:request_id>/', ServiceRequest_views.service_request_api, name='service_request_api'),
    path('api/service-requests/<int:pk>/update/', ServiceRequest_views.update_service_request, name='update_service_request'),
    path('catalog/', ServiceRequest_views.computer_dashboard, name='computer_dashboard'),
    path('catalog/save/', ServiceRequest_views.computer_save, name='computer_save'),
    path('catalog/delete/', ServiceRequest_views.computer_delete, name='computer_delete'),
    path('catalog/delete-image/', ServiceRequest_views.computer_delete_image, name='computer_delete_image'),
    path('catalog/data/<int:pk>/', ServiceRequest_views.computer_data, name='computer_data'),
]