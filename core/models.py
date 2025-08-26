from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.core.validators import MinValueValidator

class Computer(models.Model):
    CATEGORY_CHOICES = [
        ('gaming', 'Игровой'),
        ('workstation', 'Рабочая станция'),
        ('office', 'Офисный'),
        ('home', 'Домашний'),
    ]
    
    name = models.CharField(max_length=255, verbose_name="Название")
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, verbose_name="Категория")
    short_description = models.TextField(max_length=500, verbose_name="Краткое описание")
    full_description = models.TextField(verbose_name="Полное описание")
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)], verbose_name="Цена")
    is_available = models.BooleanField(default=True, verbose_name="Доступен для заказа")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")
    
    # Характеристики
    processor = models.CharField(max_length=255, verbose_name="Процессор")
    graphics_card = models.CharField(max_length=255, verbose_name="Видеокарта")
    ram = models.CharField(max_length=100, verbose_name="Оперативная память")
    storage = models.CharField(max_length=255, verbose_name="Накопитель")
    power_supply = models.CharField(max_length=100, verbose_name="Блок питания")
    case = models.CharField(max_length=255, verbose_name="Корпус")
    cooling = models.CharField(max_length=255, verbose_name="Охлаждение")
    operating_system = models.CharField(max_length=100, blank=True, verbose_name="Операционная система")
    
    class Meta:
        verbose_name = "Компьютер"
        verbose_name_plural = "Компьютеры"
        ordering = ['-created_at']
    
    def __str__(self):
        return self.name
    
    def get_price_display(self):
        return f"{self.price:,.0f} ₽".replace(',', ' ')


class ComputerImage(models.Model):
    computer = models.ForeignKey(Computer, on_delete=models.CASCADE, related_name='images', verbose_name="Компьютер")
    image = models.ImageField(upload_to='computers/%Y/%m/%d/', verbose_name="Изображение")
    is_main = models.BooleanField(default=False, verbose_name="Основное изображение")
    order = models.PositiveIntegerField(default=0, verbose_name="Порядок")
    
    class Meta:
        verbose_name = "Изображение компьютера"
        verbose_name_plural = "Изображения компьютеров"
        ordering = ['order']
    
    def __str__(self):
        return f"Изображение для {self.computer.name}"

class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, person_name=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)

        if not person_name:
            # Генерируем person_name из email (до символа @)
            person_name = email.split('@')[0]
            # Делаем его уникальным, если такой уже существует
            base_person_name = person_name
            counter = 1
            while User.objects.filter(person_name=person_name).exists():
                person_name = f"{base_person_name}{counter}"
                counter += 1

        user = self.model(email=email, person_name=person_name, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, person_name=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        # Если person_name не передан — использовать email как основу
        if not person_name:
            person_name = email.split('@')[0]

        return self.create_user(email, password, person_name=person_name, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    # Основные идентификаторы пользователя
    email = models.EmailField(unique=True)  # Уникальный email — используется как логин (USERNAME_FIELD)

    person_name = models.CharField(max_length=150,
                                   unique=True)  # Отображаемое имя пользователя (например, "Иван23"), должно быть уникальным

    # Контактная и профильная информация
    phone_number = models.CharField(max_length=20, blank=True, null=True)  # Номер телефона для связи (необязательно)
    address = models.TextField(blank=True,
                               null=True)  # Полный адрес (улица, дом, квартира) — полезно для курьерской доставки или выезда
    avatar = models.ImageField(upload_to='avatars/', blank=True,
                               null=True)  # Фото профиля пользователя, сохраняется в папке media/avatars/

    # Системные флаги доступа (используются Django)
    is_active = models.BooleanField(default=True)  # Активен ли аккаунт (False — заблокирован)
    is_staff = models.BooleanField(default=False)  # Имеет ли доступ к админ-панели Django

    # Роль пользователя в системе сервисного центра
    role = models.CharField(
        max_length=20,
        choices=[
            ('client', 'Клиент'),  # Обычный пользователь, приносит устройства в ремонт
            ('engineer', 'Инженер'),  # Специалист, выполняющий диагностику и ремонт
            ('manager', 'Менеджер'),  # Управляет заказами, коммуницирует с клиентами
            ('admin', 'Администратор'),  # Полный доступ к системе (обычно is_staff=True)
        ],
        default='client'  # По умолчанию новый пользователь — клиент
    )

    # Дополнительная информация (актуальна в основном для сотрудников)
    job_title = models.CharField(max_length=100, blank=True,
                                 null=True)  # Должность сотрудника (например, "старший инженер")
    department = models.CharField(max_length=100, blank=True,
                                  null=True)  # Отдел, в котором работает сотрудник (например, "Ремонт телефонов")
    work_schedule = models.TextField(blank=True,
                                     null=True)  # График работы (например, "Пн-Пт 9:00–18:00, перерыв 13:00–14:00")

    # Предпочтения клиента по связи
    preferred_contact_method = models.CharField(
        max_length=10,
        choices=[('email', 'Email'), ('phone', 'Телефон')],
        default='email'  # Каким способом пользователь предпочитает получать уведомления
    )

    # Системные поля аудита
    created_at = models.DateTimeField(auto_now_add=True)  # Дата и время регистрации пользователя
    updated_at = models.DateTimeField(auto_now=True)  # Дата и время последнего изменения профиля

    # Менеджер для создания пользователей (с учётом email как логина)
    objects = CustomUserManager()

    # Поле, используемое для аутентификации
    USERNAME_FIELD = 'email'  # Вход в систему осуществляется по email

    # Поля, обязательные при создании через команду createsuperuser
    REQUIRED_FIELDS = ['person_name']  # При создании суперпользователя нужно указать person_name