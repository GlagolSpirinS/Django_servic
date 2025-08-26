# models.py
from django.db import models
from django.conf import settings
from .models import *
from django.core.validators import RegexValidator


class Tag(models.Model):
    """
    Модель для тегов с поддержкой цвета.
    """
    code = models.CharField(
        max_length=50,
        unique=True,
        verbose_name="Код тега"
    )
    name = models.CharField(max_length=100, verbose_name="Название тега")
    color = models.CharField(
        max_length=7,  # формат #RRGGBB
        default='#333333',
        verbose_name="Цвет тега",
        help_text="Выберите цвет в формате HEX, например: #007bff"
    )

    class Meta:
        verbose_name = "Тег"
        verbose_name_plural = "Теги"

    def __str__(self):
        return self.name


class IssueOption(models.Model):
    # Определим константу для выбора
    CODE_CHOICES = [
        ('no_power', 'Не включается'),
        ('screen_issue', 'Проблемы с экраном (мерцание, разбит, не реагирует)'),
        ('battery_problem', 'Быстро разряжается / не держит заряд'),
        ('overheating', 'Перегревается'),
        ('sound_issue', 'Проблемы со звуком'),
        ('camera_issue', 'Не работает камера'),
        ('wifi_bluetooth', 'Проблемы с Wi-Fi / Bluetooth'),
        ('software_crash', 'Зависает / перезагружается / ошибки ОС'),
        ('water_damage', 'Попадание влаги'),
        ('physical_damage', 'Механические повреждения'),
        ('performance_slow', 'Сильно тормозит'),
        ('charging_problem', 'Не заряжается / заряжается с перебоями'),
        ('other', 'Другое'),
    ]

    code = models.CharField(
        max_length=50,
        unique=True,
        choices=CODE_CHOICES,  # ← используем константу
        verbose_name="Код симптома"
    )
    description = models.CharField(max_length=100, verbose_name="Описание")

    class Meta:
        verbose_name = "Симптом неисправности"
        verbose_name_plural = "Симптомы неисправности"

    def __str__(self):
        return self.get_code_display() or self.description


class ServiceRequest(models.Model):
    # Связь с пользователем, который создал заявку
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='service_requests',
        verbose_name="Пользователь, создавший заявку"
    )

    # Тип клиента: физическое или юридическое лицо
    CUSTOMER_TYPE_CHOICES = [
        ('individual', 'Физическое лицо'),
        ('legal_entity', 'Юридическое лицо'),
    ]
    customer_type = models.CharField(
        max_length=20,
        choices=CUSTOMER_TYPE_CHOICES,
        default='individual',
        verbose_name="Тип заказчика"
    )

    # ФИО заказчика
    full_name = models.CharField(max_length=300, verbose_name="ФИО заказчика")

    # Поля для юридического лица
    organization_name = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="Название организации"
    )
    inn = models.CharField(
        max_length=12,
        blank=True,
        null=True,
        verbose_name="ИНН",
        validators=[
            RegexValidator(
                regex=r'^\d{10,12}$',
                message="ИНН должен содержать 10 (юр. лицо) или 12 (физ. лицо) цифр."
            )
        ]
    )

    # Контактная информация
    phone_number = models.CharField(
        max_length=20,
        verbose_name="Номер заказчика"
    )
    address = models.TextField(verbose_name="Адрес заказчика")
    external_links = models.TextField(
        blank=True,
        null=True,
        help_text="Ссылки на чаты, профили в мессенджерах и т.п.",
        verbose_name="Внешние источники связи"
    )
    email = models.EmailField(
        verbose_name="Email",
        help_text="Подтягивается из аккаунта пользователя"
    )

    # Информация об устройстве
    DEVICE_TYPE_CHOICES = [
        ('smartphone', 'Смартфон'),
        ('laptop', 'Ноутбук'),
        ('tablet', 'Планшет'),
        ('desktop', 'Системный блок'),
        ('monitor', 'Монитор'),
        ('printer', 'Принтер'),
        ('tv', 'Телевизор'),
        ('smartwatch', 'Умные часы'),
        ('other', 'Другое'),
    ]
    device_type = models.CharField(
        max_length=20,
        choices=DEVICE_TYPE_CHOICES,
        verbose_name="Тип устройства"
    )

    # Симптомы неисправности — можно выбрать несколько
    issues = models.ManyToManyField(
        IssueOption,
        verbose_name="Симптомы неисправности"
    )
    issues_other = models.TextField(
        blank=True,
        null=True,
        verbose_name="Другие симптомы",
        help_text="Укажите, если выбрано 'Другое'"
    )

    # Дополнительные поля (по желанию)
    description = models.TextField(
        blank=True,
        null=True,
        verbose_name="Дополнительное описание проблемы"
    )

    # Множественные теги
    tags = models.ManyToManyField(
        Tag,
        blank=True,
        verbose_name="Теги",
        help_text="Выберите один или несколько тегов"
    )

    # Статус (один из)
    STATUS_CHOICES = [
        ('waiting', 'Ожидание'),
        ('working', 'В работе'),
        ('finish', 'Готов к выдаче'),
    ]
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        verbose_name='Статус',
        default='waiting',
    )

    # Системные поля
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Последнее обновление")

    class Meta:
        verbose_name = "Заявка в сервисный центр"
        verbose_name_plural = "Заявки в сервисный центр"
        ordering = ['-created_at']

    def __str__(self):
        return f"Заявка #{self.id} от {self.full_name} — {self.get_device_type_display()}"

    def save(self, *args, **kwargs):
        # Подтягиваем email из пользователя, если не указан
        if not self.email:
            self.email = self.created_by.email
        # Очищаем поля организации, если тип — физлицо
        if self.customer_type == 'individual':
            self.organization_name = None
            self.inn = None
        super().save(*args, **kwargs)