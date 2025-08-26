# views.py
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, render
from django.contrib.auth import get_user_model
import json

User = get_user_model()

@login_required
def crm(request):
    allowed_roles = ['engineer', 'manager', 'admin']
    if not request.user.is_staff and request.user.role not in allowed_roles:
        raise PermissionDenied("У вас нет доступа к CRM-панели.")

    users = User.objects.all().order_by('-created_at')
    return render(request, 'system/user.html', {'users': users})


# Получение данных пользователя
@login_required
def get_user_data(request, user_id):
    if not request.user.is_staff and request.user.role not in ['manager', 'admin']:
        return JsonResponse({'error': 'Доступ запрещён'}, status=403)

    user = get_object_or_404(User, id=user_id)
    return JsonResponse({
        'id': user.id,
        'person_name': user.person_name,
        'email': user.email,
        'phone_number': user.phone_number,
        'address': user.address,
        'role': user.role,
        'job_title': user.job_title,
        'department': user.department,
        'work_schedule': user.work_schedule,
        'preferred_contact_method': user.preferred_contact_method,
        'avatar': user.avatar.url if user.avatar else None,
    })


# Обновление пользователя
@csrf_exempt
@login_required
def update_user(request):
    if request.user.role not in ['manager', 'admin'] or not request.method == 'POST':
        return JsonResponse({'success': False, 'error': 'Доступ запрещён'}, status=403)

    try:
        user_id = request.POST.get('user_id')
        user = get_object_or_404(User, id=user_id)

        # Обновляем поля
        user.person_name = request.POST.get('person_name', user.person_name)
        user.phone_number = request.POST.get('phone_number', user.phone_number)
        user.address = request.POST.get('address', user.address)
        user.role = request.POST.get('role', user.role)
        user.job_title = request.POST.get('job_title', user.job_title)
        user.department = request.POST.get('department', user.department)
        user.work_schedule = request.POST.get('work_schedule', user.work_schedule)
        user.preferred_contact_method = request.POST.get('preferred_contact_method', user.preferred_contact_method)

        if 'avatar' in request.FILES:
            user.avatar = request.FILES['avatar']

        user.save()
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


# Переключение активности
@csrf_exempt
@login_required
def toggle_user(request):
    if request.user.role != 'admin' or not request.method == 'POST':
        return JsonResponse({'success': False, 'error': 'Только администратор может управлять статусом.'}, status=403)

    try:
        user_id = request.POST.get('user_id')
        user = get_object_or_404(User, id=user_id)
        user.is_active = not user.is_active
        user.save()
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})