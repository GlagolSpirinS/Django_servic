from django.conf import settings
from django.contrib import admin
from django.templatetags.static import static
from django.urls import path, include
from django.urls import path

from crm import views as crm_views

from core import views as core_views

from ServiceRequest import views as ServiceRequest_views

from django.conf import settings
from django.conf.urls.static import static



urlpatterns = [
    path('admin/', admin.site.urls),
    path('', core_views.home, name='home'),
    path('catalog/', core_views.computer_catalog, name='computer_catalog'),
    path('api/computer/<int:computer_id>/', core_views.computer_api_detail, name='computer_api_detail'),
    path('search/', core_views.search, name='search'),
    path('contact/', core_views.contact, name='contact'),
    path('article/', core_views.article, name='article'),
    path('profile/', core_views.profile, name='profile'),
    path('request/', ServiceRequest_views.create_service_request, name='request'),
    path('logout/', core_views.custom_logout_view, name='logout'),
    path('system/', include('crm.urls')),
    path('auth/', include('core.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
