import json

from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .models import ServiceRequest, IssueOption, Tag
from django.http import HttpResponseForbidden
from django.http import JsonResponse

import json
from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from core.models import Computer, ComputerImage


@login_required
def create_service_request(request):
    if request.method == 'POST':
        try:
            # === Обязательные поля ===
            customer_type = request.POST.get('customer_type')
            full_name = request.POST.get('full_name')
            phone_number = request.POST.get('phone_number')
            address = request.POST.get('address')
            device_type = request.POST.get('device_type')

            # Email — берём из пользователя
            email = request.user.email

            # === Поля для юрлица (если применимо) ===
            organization_name = None
            inn = None
            if customer_type == 'legal_entity':
                organization_name = request.POST.get('organization_name')
                inn = request.POST.get('inn')
                if not organization_name or not inn:
                    raise ValueError("Для юридического лица нужно указать название организации и ИНН.")

            # === Симптомы неисправности ===
            selected_issues = request.POST.getlist('issues')  # список кодов
            issues_other = request.POST.get('issues_other', '').strip()

            # Валидация хотя бы одного симптома
            if not selected_issues and not issues_other:
                raise ValueError("Укажите хотя бы один симптом неисправности.")

            # Создаём заявку
            service_request = ServiceRequest.objects.create(
                created_by=request.user,
                customer_type=customer_type,
                full_name=full_name,
                phone_number=phone_number,
                address=address,
                email=email,
                device_type=device_type,
                organization_name=organization_name,
                inn=inn,
                external_links=request.POST.get('external_links', '').strip(),
                description=request.POST.get('description', '').strip(),
                issues_other=issues_other,
            )

            # Добавляем симптомы
            for issue_code in selected_issues:
                issue_obj, created = IssueOption.objects.get_or_create(
                    code=issue_code,
                    defaults={'description': dict(IssueOption.CODE_CHOICES).get(issue_code, issue_code)}
                )
                service_request.issues.add(issue_obj)

            # Добавляем теги
            selected_tag_codes = request.POST.getlist('tags')
            if selected_tag_codes:
                tags = Tag.objects.filter(code__in=selected_tag_codes)
                service_request.tags.set(tags)

            messages.success(request, "Ваша заявка успешно отправлена! Мы свяжемся с вами в ближайшее время.")
            # return redirect('create_service_request')  # перезагружаем страницу

        except Exception as e:
            messages.error(request, f"Ошибка при создании заявки: {str(e)}")

    # Для GET-запроса (и после POST с ошибкой) — показываем форму и заявки
    issue_choices = IssueOption.objects.all()
    all_tags = Tag.objects.all()

    # 🔽 Получаем заявки текущего пользователя
    user_requests = ServiceRequest.objects.filter(created_by=request.user).order_by('-created_at')

    return render(request, 'request/request.html', {
        'issue_choices': issue_choices,
        'device_choices': ServiceRequest.DEVICE_TYPE_CHOICES,
        'all_tags': all_tags,
        'user_requests': user_requests,  # передаём заявки в шаблон
    })

@login_required
def request_list(request):
    # 🔒 Проверяем: только staff или определённые роли могут заходить
    allowed_roles = ['manager', 'admin', 'engineer']
    if not request.user.is_staff and request.user.role not in allowed_roles:
        return HttpResponseForbidden("У вас нет доступа к этой странице.")

    # Теперь все, кто прошёл проверку, видят все заявки
    requests = ServiceRequest.objects.all().select_related('created_by').order_by('-created_at')

    return render(request, 'system/requests.html', {
        'service_requests': requests
    })


@login_required
def service_request_api(request, request_id):
    try:
        req = ServiceRequest.objects.select_related('created_by').prefetch_related('issues', 'tags').get(id=request_id)
        allowed_roles = ['manager', 'admin', 'engineer']
        # Проверка доступа
        if not request.user.is_staff and request.user.role not in allowed_roles and req.created_by != request.user:
            return JsonResponse({'error': 'Доступ запрещён'}, status=403)

        # Собираем данные
        data = {
            'id': req.id,
            'full_name': req.full_name,
            'customer_type': req.customer_type,
            'customer_type_display': req.get_customer_type_display(),
            'organization_name': req.organization_name,
            'inn': req.inn,
            'phone_number': req.phone_number,
            'email': req.email,
            'address': req.address,
            'device_type': req.device_type,
            'device_type_display': req.get_device_type_display(),
            'issues': [
                {'code': i.code, 'description': i.description}
                for i in req.issues.all()
            ],
            'issues_other': req.issues_other or '',
            'description': req.description or '',
            'external_links': req.external_links or '',
            'status': req.status,
            'created_at': req.created_at.isoformat(),

            # 🔴 Теги текущей заявки (с цветами)
            'tags': [
                {'code': tag.code, 'name': tag.name, 'color': tag.color}
                for tag in req.tags.all()
            ],

            # ✅ Все теги из базы (для чекбоксов)
            'available_tags': [
                {'code': tag.code, 'name': tag.name, 'color': tag.color}
                for tag in Tag.objects.all()
            ],
        }

        return JsonResponse(data, json_dumps_params={'ensure_ascii': False, 'indent': 2})

    except ServiceRequest.DoesNotExist:
        return JsonResponse({'error': 'Заявка не найдена'}, status=404)


@csrf_protect
@login_required
def update_service_request(request, pk):
    if request.method == "POST":
        try:
            req = ServiceRequest.objects.get(id=pk)
            allowed_roles = ['manager', 'admin', 'engineer']
            # Проверка прав
            if not request.user.is_staff and request.user.role not in allowed_roles and req.created_by != request.user:
                return JsonResponse({'error': 'Доступ запрещён'}, status=403)

            data = json.loads(request.body)

            # Обновляем статус
            if 'status' in data:
                if data['status'] in dict(ServiceRequest.STATUS_CHOICES):
                    req.status = data['status']
                else:
                    return JsonResponse({'error': 'Недопустимое значение статуса'}, status=400)

            # ✅ Обновляем теги (множественный выбор)
            if 'tags' in data:
                req.tags.clear()  # удаляем старые
                tag_codes = data['tags']
                if isinstance(tag_codes, list):
                    tags = Tag.objects.filter(code__in=tag_codes)
                    req.tags.set(tags)
                else:
                    return JsonResponse({'error': 'Поле "tags" должно быть списком'}, status=400)

            req.save()

            return JsonResponse({'success': True})
        except ServiceRequest.DoesNotExist:
            return JsonResponse({'error': 'Заявка не найдена'}, status=404)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    return JsonResponse({'error': 'Invalid method'}, status=405)


def computer_dashboard(request):
    computers = Computer.objects.prefetch_related('images').all()
    categories = Computer.CATEGORY_CHOICES

    return render(request, 'system/catalog.html', {
        'computers': computers,
        'categories': categories,
    })




@csrf_exempt
@require_http_methods(["POST"])
def computer_save(request):
    try:
        # === 1. Извлечение данных формы ===
        computer_id = request.POST.get('id')
        name = request.POST.get('name')
        category = request.POST.get('category')
        short_description = request.POST.get('short_description')
        full_description = request.POST.get('full_description')
        price_str = request.POST.get('price')
        is_available = 'is_available' in request.POST  # checkbox: есть — True, нет — False
        processor = request.POST.get('processor')
        graphics_card = request.POST.get('graphics_card')
        ram = request.POST.get('ram')
        storage = request.POST.get('storage')
        power_supply = request.POST.get('power_supply')
        case = request.POST.get('case')
        cooling = request.POST.get('cooling')
        operating_system = request.POST.get('operating_system')

        # === 2. Валидация обязательных полей ===
        if not name or not category or not price_str:
            return JsonResponse({
                'success': False,
                'error': 'Имя, категория и цена обязательны.'
            }, status=400)

        try:
            price = float(price_str)
            if price < 0:
                raise ValueError
        except (ValueError, TypeError):
            return JsonResponse({
                'success': False,
                'error': 'Цена должна быть положительным числом.'
            }, status=400)

        # === 3. Получаем или создаём объект Computer ===
        if computer_id:
            computer = get_object_or_404(Computer, id=computer_id)
            # Обновляем поля
            computer.name = name
            computer.category = category
            computer.short_description = short_description
            computer.full_description = full_description
            computer.price = price
            computer.is_available = is_available
            computer.processor = processor
            computer.graphics_card = graphics_card
            computer.ram = ram
            computer.storage = storage
            computer.power_supply = power_supply
            computer.case = case
            computer.cooling = cooling
            computer.operating_system = operating_system
            computer.save()
        else:
            # Создаём новый объект
            computer = Computer.objects.create(
                name=name,
                category=category,
                short_description=short_description,
                full_description=full_description,
                price=price,
                is_available=is_available,
                processor=processor,
                graphics_card=graphics_card,
                ram=ram,
                storage=storage,
                power_supply=power_supply,
                case=case,
                cooling=cooling,
                operating_system=operating_system,
            )

        # === 4. Обработка изображений ===
        # Удаляем старые изображения, если нужно
        if 'clear_images' in request.POST:
            computer.images.all().delete()

        # Добавляем новые
        uploaded_files = request.FILES.getlist('images')
        for uploaded_file in uploaded_files:
            ComputerImage.objects.create(
                computer=computer,
                image=uploaded_file,
                # is_main и order можно добавить, если нужны
                # is_main = ...
                # order = ...
            )

        # === 5. Ответ с данными ===
        main_image = computer.images.first()
        return JsonResponse({
            'success': True,
            'id': computer.id,
            'name': computer.name,
            'price': computer.get_price_display(),
            'category': computer.get_category_display(),
            'image_url': main_image.image.url if main_image else None,
        })

    except Exception as e:
        # Логируй ошибку в продакшене
        import logging
        logging.getLogger(__name__).error(f"Ошибка в computer_save: {e}")
        return JsonResponse({
            'success': False,
            'error': f'Ошибка сервера: {str(e)}'
        }, status=500)


def computer_delete(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            computer = get_object_or_404(Computer, id=data['id'])
            computer.delete()
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False}, status=400)


def computer_delete_image(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            image = get_object_or_404(ComputerImage, id=data['image_id'])
            image.delete()
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    return JsonResponse({'success': False}, status=400)


def handle_images(request, computer):
    if 'clear_images' in request.POST:
        computer.images.all().delete()

    for f in request.FILES.getlist('images'):
        ComputerImage.objects.create(computer=computer, image=f)


def computer_data(request, pk):
    computer = get_object_or_404(Computer, pk=pk)
    images = [
        {
            'id': img.id,
            'url': img.image.url,
            'is_main': img.is_main,
            'order': img.order
        }
        for img in computer.images.all()
    ]
    return JsonResponse({
        'id': computer.id,
        'name': computer.name,
        'category': computer.category,
        'short_description': computer.short_description,
        'full_description': computer.full_description,
        'price': str(computer.price),
        'is_available': computer.is_available,
        'processor': computer.processor,
        'graphics_card': computer.graphics_card,
        'ram': computer.ram,
        'storage': computer.storage,
        'power_supply': computer.power_supply,
        'case': computer.case,
        'cooling': computer.cooling,
        'operating_system': computer.operating_system,
        'images': images,
    })