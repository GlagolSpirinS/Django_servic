from django.urls import path
from .views import *

urlpatterns = [
    path('login/', login_with_email, name='login_with_email'),
    path('verify/', verify_login_code, name='verify_login_code'),
    path('register/', register_with_email, name='register_with_email'),
    path('register/verify/', verify_registration_code, name='verify_registration_code'),
]