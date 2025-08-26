import random
import smtplib
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.contrib.auth.decorators import login_required
from django import forms
from .models import User
from django.contrib import messages
from django.conf import settings
from .models import Computer
from django.template.loader import render_to_string
from django.core.mail import get_connection
from django.core.cache import cache  # <-- Импортируем кэш


def _send_beautiful_email(email, code, subject, title, body_text):
    """
    Вспомогательная функция для отправки красивого HTML-письма.
    """
    html_message = render_to_string(
        'email_template.html',
        {
            'code': code,
            'title': title,
            'body_text': body_text,
        }
    )

    try:
        if not all([settings.EMAIL_HOST_USER, settings.EMAIL_HOST_PASSWORD, settings.EMAIL_HOST]):
            raise Exception("Настройки EMAIL в settings.py неполные или отсутствуют.")

        connection = get_connection()
        connection.open()

        send_mail(
            subject,
            f'{body_text}: {code}',
            settings.EMAIL_HOST_USER,
            [email],
            html_message=html_message,
            fail_silently=False,
            connection=connection
        )
    except smtplib.SMTPAuthenticationError:
        raise Exception(
            "Ошибка аутентификации SMTP. Проверьте EMAIL_HOST_USER и EMAIL_HOST_PASSWORD. Возможно, вам нужно создать пароль приложения для Google.")
    except smtplib.SMTPException as e:
        raise Exception(
            f"Ошибка SMTP: {e}. Возможно, порт или хост настроены неверно, или брандмауэр блокирует соединение.")
    except Exception as e:
        raise Exception(f"Неизвестная ошибка при отправке письма: {e}")
    finally:
        if 'connection' in locals():
            connection.close()


# === Вход через email ===
def login_with_email(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        if not email:
            return HttpResponse("Email is required.")

        User = get_user_model()
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return HttpResponse("User with this email does not exist.")

        code = str(random.randint(100000, 999999))

        # Сохраняем код в кэше на 5 минут
        cache.set(f'login_code_{email}', code, 300)

        try:
            _send_beautiful_email(
                email,
                code,
                'Ваш код для входа',
                'Ваш код для входа',
                'Мы отправили вам этот код для подтверждения входа в вашу учетную запись. Пожалуйста, используйте его, чтобы завершить процесс.'
            )
            # Сохраняем email в сессии только для перехода (не влияет на срок)
            request.session['login_email_attempt'] = email
            return redirect('verify_login_code')
        except Exception as e:
            return HttpResponse(f"Ошибка отправки письма: {e}")

    return render(request, 'login_with_email.html')


def verify_login_code(request):
    if request.method == 'POST':
        code = request.POST.get('code')
        email = request.session.get('login_email_attempt')  # берём из сессии

        if not email:
            return HttpResponse("Сессия истекла. Пожалуйста, начните сначала.")

        # Получаем код из кэша
        stored_code = cache.get(f'login_code_{email}')

        if not stored_code:
            return HttpResponse("Код истёк или уже использован. Запросите новый.")

        if code == stored_code:
            User = get_user_model()
            user = User.objects.get(email=email)
            login(request, user)

            # Удаляем временные данные
            if 'login_email_attempt' in request.session:
                del request.session['login_email_attempt']
            # Код в кэше автоматически удалится через TTL, но можно вручную:
            cache.delete(f'login_code_{email}')

            return redirect('home')
        else:
            cache.delete(f'login_code_{email}')  # защита от повторных попыток
            return HttpResponse("Неверный код. Пожалуйста, запросите новый.")

    return render(request, 'verify_login_code.html')


# === Регистрация через email ===
def register_with_email(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        person_name = request.POST.get('person_name', '').strip()

        if not email:
            return HttpResponse("Email is required.")
        if not person_name:
            return HttpResponse("Имя пользователя обязательно.")

        # Проверка длины
        if len(person_name) < 3:
            return HttpResponse("Имя пользователя должно быть не менее 3 символов.")
        if len(person_name) > 150:
            return HttpResponse("Имя пользователя слишком длинное.")

        # Проверка на уникальность (опционально, можно и на этапе создания)
        User = get_user_model()
        if User.objects.filter(person_name=person_name).exists():
            return HttpResponse("Это имя пользователя уже занято.")

        if User.objects.filter(email=email).exists():
            return HttpResponse("Пользователь с таким email уже существует.")

        code = str(random.randint(100000, 999999))

        # Сохраняем в кэш и сессию
        cache.set(f'registration_code_{email}', code, 300)
        request.session['registration_email_attempt'] = email
        request.session['registration_person_name_attempt'] = person_name  # <-- Сохраняем!

        try:
            _send_beautiful_email(
                email,
                code,
                'Ваш код для регистрации',
                'Ваш код для регистрации',
                'Мы отправили вам этот код для завершения регистрации. Пожалуйста, используйте его, чтобы продолжить.'
            )
            return redirect('verify_registration_code')
        except Exception as e:
            return HttpResponse(f"Ошибка отправки письма: {e}")

    return render(request, 'register_with_email.html')


def verify_registration_code(request):
    if request.method == 'POST':
        code = request.POST.get('code')
        email = request.session.get('registration_email_attempt')
        person_name = request.session.get('registration_person_name_attempt')

        if not email:
            return HttpResponse("Сессия истекла. Пожалуйста, начните сначала.")
        if not person_name:
            return HttpResponse("Имя пользователя не указано. Начните регистрацию заново.")

        stored_code = cache.get(f'registration_code_{email}')
        if not stored_code:
            return HttpResponse("Код истёк. Запросите новый.")

        if code == stored_code:
            User = get_user_model()

            # Повторная проверка на уникальность
            if User.objects.filter(email=email).exists():
                return HttpResponse("Этот email уже занят.")
            if User.objects.filter(person_name=person_name).exists():
                return HttpResponse("Это имя пользователя уже занято.")

            # Создаём пользователя
            user = User.objects.create_user(
                person_name=person_name,
                email=email,
                password=None  # можно установить позже, если нужно
            )
            user.is_active = True
            user.save()

            login(request, user)

            # Очистка
            request.session.pop('registration_email_attempt', None)
            request.session.pop('registration_person_name_attempt', None)
            cache.delete(f'registration_code_{email}')

            return redirect('home')
        else:
            cache.delete(f'registration_code_{email}')
            return HttpResponse("Неверный код. Пожалуйста, запросите новый.")

    return render(request, 'verify_registration_code.html')


# === Остальные функции без изменений ===
def custom_logout_view(request):
    logout(request)
    return redirect('home')


def home(request):
    context = {
        'user': request.user,
    }
    return render(request, 'home/home.html', context)


def my_view(request):
    if request.user.is_authenticated:
        email = request.user.email
        return HttpResponse(f"Привет, {email}! Ты авторизован.")
    else:
        return HttpResponse("Привет, аноним. Пожалуйста, войди.")


def computer_catalog(request):
    computers = Computer.objects.filter(is_available=True)
    return render(request, 'catalog/catalog.html', {'computers': computers})

def computer_api_detail(request, computer_id):
    computer = get_object_or_404(Computer, id=computer_id, is_available=True)

    # Собираем данные в словарь
    data = {
        'id': computer.id,
        'name': computer.name,
        'price': computer.get_price_display(),
        'short_description': computer.short_description,
        'full_description': computer.full_description,
        'processor': computer.processor,
        'graphics_card': computer.graphics_card,
        'ram': computer.ram,
        'storage': computer.storage,
        'power_supply': computer.power_supply,
        'case': computer.case,
        'cooling': computer.cooling,
        'operating_system': computer.operating_system or 'Не установлена',
        'specs': f"""
            <strong>Процессор:</strong> {computer.processor}<br>
            <strong>Видеокарта:</strong> {computer.graphics_card}<br>
            <strong>Оперативная память:</strong> {computer.ram}<br>
            <strong>Накопитель:</strong> {computer.storage}<br>
            <strong>Блок питания:</strong> {computer.power_supply}<br>
            <strong>Корпус:</strong> {computer.case}<br>
            <strong>Охлаждение:</strong> {computer.cooling}<br>
            <strong>ОС:</strong> {computer.operating_system or 'Не установлена'}
        """,
        'images': [
            {
                'image': img.image.url,
                'is_main': img.is_main,
                'order': img.order
            } for img in computer.images.all().order_by('order')
        ] or [
            {
                'image': request.build_absolute_uri(static('images/default_computer.png')),
                'is_main': True,
                'order': 0
            }
        ]
    }

    return JsonResponse(data, json_dumps_params={'ensure_ascii': False})


def contact(request):
    return render(request, "contact/contact.html")


def search(request):
    return render(request, "search/search.html")

def create_request(request):
    return render(request, "request/request.html")

def article(request):
    return render(request, "article/article.html")

@login_required
def profile(request):
    user = request.user

    # Создаём ModelForm динамически, чтобы не использовать отдельный forms.py
    class ProfileForm(forms.ModelForm):
        class Meta:
            model = User
            fields = [
                'person_name',
                'phone_number',
                'address',
                'avatar',
                'preferred_contact_method'
            ]
            widgets = {
                'person_name': forms.TextInput(attrs={
                    'class': 'form-input',
                    'placeholder': 'Ваше имя'
                }),
                'phone_number': forms.TextInput(attrs={
                    'class': 'form-input',
                    'placeholder': '+7 (999) 123-45-67'
                }),
                'address': forms.Textarea(attrs={
                    'class': 'form-input',
                    'rows': 3,
                    'placeholder': 'Улица, дом, квартира'
                }),
                'preferred_contact_method': forms.Select(attrs={
                    'class': 'form-input'
                }),
                'avatar': forms.FileInput(attrs={
                    'class': 'form-input'
                })
            }

    if request.method == 'POST':
        form = ProfileForm(request.POST, request.FILES, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Профиль успешно обновлён!')
            return redirect('profile')
        else:
            messages.error(request, 'Пожалуйста, исправьте ошибки.')
    else:
        form = ProfileForm(instance=user)

    return render(request, "profile/profile.html", {
        'form': form,
        'user': user,
        'messages': messages.get_messages(request)
    })