from decimal import Decimal
from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator, RegexValidator
from django.db import models
from django.db.models import Avg, F, Q
from django.utils import timezone


phone_validator = RegexValidator(r"^\+?[0-9]{10,15}$", "Введите телефон: 10–15 цифр, возможен + в начале.")


class User(AbstractUser):
    class Role(models.TextChoices):
        OWNER = "owner", "Владелец"
        SITTER = "sitter", "Догситтер"
        CURATOR = "curator", "Куратор"
        ADMIN = "admin", "Администратор"

    email = models.EmailField("Электронная почта", unique=True)
    phone = models.CharField("Телефон", max_length=16, validators=[phone_validator], blank=True)
    role = models.CharField("Основная роль", max_length=10, choices=Role.choices, default=Role.OWNER)

    class Meta:
        db_table = "service_user"
        verbose_name = "Пользователь"
        verbose_name_plural = "Пользователи"
        ordering = ["username"]
        constraints = [models.CheckConstraint(condition=Q(role__in=["owner", "sitter", "curator", "admin"]), name="user_role_valid")]

    def __str__(self):
        return self.get_full_name() or self.username


class Area(models.Model):
    name = models.CharField("Название района", max_length=120)
    district = models.CharField("Административный округ", max_length=120)
    distance_coefficient = models.DecimalField("Коэффициент удалённости", max_digits=4, decimal_places=2, default=Decimal("1.00"), validators=[MinValueValidator(Decimal("0.01"))])

    class Meta:
        db_table = "area"
        verbose_name = "Район обслуживания"
        verbose_name_plural = "Районы обслуживания"
        ordering = ["district", "name"]
        constraints = [
            models.UniqueConstraint(fields=["district", "name"], name="area_district_name_unique"),
            models.CheckConstraint(condition=Q(distance_coefficient__gt=0), name="area_coefficient_positive"),
        ]

    def __str__(self):
        return f"{self.name} ({self.district})"


class Owner(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, verbose_name="Пользователь", on_delete=models.CASCADE, related_name="owner_profile")
    area = models.ForeignKey(Area, verbose_name="Район проживания", on_delete=models.PROTECT, related_name="owners")
    pickup_address = models.CharField("Адрес забора питомца", max_length=255)
    emergency_contact = models.CharField("Экстренный контакт", max_length=16, validators=[phone_validator])
    access_notes = models.TextField("Домофон и доступ", blank=True)

    class Meta:
        db_table = "owner"
        verbose_name = "Владелец собаки"
        verbose_name_plural = "Владельцы собак"
        ordering = ["user__username"]

    def __str__(self):
        return str(self.user)


class Breed(models.Model):
    name = models.CharField("Название породы", max_length=120, unique=True)

    class Meta:
        db_table = "breed"
        verbose_name = "Порода"
        verbose_name_plural = "Породы"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Behavior(models.Model):
    class Difficulty(models.TextChoices):
        BASIC = "basic", "Базовый"
        HIGH = "high", "Повышенный"

    name = models.CharField("Название особенности", max_length=120, unique=True)
    difficulty = models.CharField("Уровень сложности", max_length=8, choices=Difficulty.choices, default=Difficulty.BASIC)
    recommendations = models.TextField("Рекомендации", blank=True)

    class Meta:
        db_table = "behavior"
        verbose_name = "Поведенческая особенность"
        verbose_name_plural = "Поведенческие особенности"
        ordering = ["name"]
        constraints = [models.CheckConstraint(condition=Q(difficulty__in=["basic", "high"]), name="behavior_difficulty_valid")]

    def __str__(self):
        return self.name


class Dog(models.Model):
    class Sex(models.TextChoices):
        MALE = "male", "Кобель"
        FEMALE = "female", "Сука"

    owner = models.ForeignKey(Owner, verbose_name="Владелец", on_delete=models.PROTECT, related_name="dogs")
    name = models.CharField("Кличка", max_length=80)
    breed = models.ForeignKey(Breed, verbose_name="Порода", on_delete=models.PROTECT, related_name="dogs")
    birth_date = models.DateField("Дата рождения")
    weight_kg = models.DecimalField("Вес, кг", max_digits=5, decimal_places=2, validators=[MinValueValidator(Decimal("0.10")), MaxValueValidator(Decimal("150.00"))])
    sex = models.CharField("Пол", max_length=6, choices=Sex.choices)
    is_vaccinated = models.BooleanField("Привита", default=False)
    has_vet_passport = models.BooleanField("Есть ветпаспорт", default=False)
    photo = models.FileField("Фотография", upload_to="dogs/", blank=True)
    care_instructions = models.TextField("Кормление и амуниция", blank=True)
    behaviors = models.ManyToManyField(Behavior, verbose_name="Особенности поведения", through="DogBehavior", related_name="dogs", blank=True)

    class Meta:
        db_table = "dog"
        verbose_name = "Собака"
        verbose_name_plural = "Собаки"
        ordering = ["name", "pk"]
        constraints = [
            models.CheckConstraint(condition=Q(weight_kg__gte=Decimal("0.10"), weight_kg__lte=150), name="dog_weight_range"),
            models.CheckConstraint(condition=Q(sex__in=["male", "female"]), name="dog_sex_valid"),
        ]

    @property
    def size_category(self):
        if self.weight_kg < 5:
            return "Мини"
        if self.weight_kg < 15:
            return "Малая"
        if self.weight_kg <= 25:
            return "Средняя"
        return "Крупная"

    def clean(self):
        super().clean()
        if self.birth_date and self.birth_date > timezone.localdate():
            raise ValidationError({"birth_date": "Дата рождения не может быть в будущем."})

    def __str__(self):
        return f"{self.name} — {self.owner}"


class DogBehavior(models.Model):
    dog = models.ForeignKey(Dog, verbose_name="Собака", on_delete=models.CASCADE, related_name="behavior_links")
    behavior = models.ForeignKey(Behavior, verbose_name="Особенность", on_delete=models.PROTECT, related_name="dog_links")
    notes = models.TextField("Индивидуальные рекомендации", blank=True)

    class Meta:
        db_table = "dog_behavior"
        verbose_name = "Особенность собаки"
        verbose_name_plural = "Особенности собак"
        ordering = ["dog_id", "behavior_id"]
        constraints = [models.UniqueConstraint(fields=["dog", "behavior"], name="dog_behavior_unique")]

    def __str__(self):
        return f"{self.dog.name}: {self.behavior.name}"


class Sitter(models.Model):
    class Verification(models.TextChoices):
        PENDING = "pending", "На проверке"
        APPROVED = "approved", "Одобрена"
        REJECTED = "rejected", "Отклонена"

    user = models.OneToOneField(settings.AUTH_USER_MODEL, verbose_name="Пользователь", on_delete=models.CASCADE, related_name="sitter_profile")
    photo = models.FileField("Фотография", upload_to="sitters/", blank=True)
    about = models.TextField("О себе и опыте")
    experience_years = models.PositiveSmallIntegerField("Стаж, лет", default=0, validators=[MaxValueValidator(80)])
    max_weight_kg = models.DecimalField("Допустимый вес, кг", max_digits=5, decimal_places=2, validators=[MinValueValidator(Decimal("0.10")), MaxValueValidator(Decimal("150.00"))])
    accepts_large_dogs = models.BooleanField("Работает с крупными собаками", default=False)
    accepts_boarding = models.BooleanField("Принимает на передержку", default=False)
    walk_hour_rate = models.DecimalField("Цена часа выгула", max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))])
    boarding_day_rate = models.DecimalField("Цена суток передержки", max_digits=10, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(Decimal("0.01"))])
    verification_status = models.CharField("Верификация", max_length=8, choices=Verification.choices, default=Verification.PENDING)
    curator_comment = models.TextField("Комментарий куратора", blank=True)
    areas = models.ManyToManyField(Area, verbose_name="Районы выезда", through="SitterArea", related_name="sitters", blank=True)
    behaviors = models.ManyToManyField(Behavior, verbose_name="Компетенции", through="SitterBehavior", related_name="sitters", blank=True)

    class Meta:
        db_table = "sitter"
        verbose_name = "Анкета догситтера"
        verbose_name_plural = "Анкеты догситтеров"
        ordering = ["user__username"]
        constraints = [
            models.CheckConstraint(condition=Q(experience_years__lte=80), name="sitter_experience_range"),
            models.CheckConstraint(condition=Q(max_weight_kg__gte=Decimal("0.10"), max_weight_kg__lte=150), name="sitter_weight_range"),
            models.CheckConstraint(condition=Q(walk_hour_rate__gt=0), name="sitter_walk_rate_positive"),
            models.CheckConstraint(condition=Q(boarding_day_rate__isnull=True) | Q(boarding_day_rate__gt=0), name="sitter_boarding_rate_positive"),
            models.CheckConstraint(condition=Q(accepts_boarding=False) | Q(boarding_day_rate__isnull=False), name="sitter_boarding_rate_required"),
            models.CheckConstraint(condition=Q(verification_status__in=["pending", "approved", "rejected"]), name="sitter_verification_valid"),
        ]

    @property
    def average_rating(self):
        return Review.objects.filter(order__slot__sitter=self).aggregate(value=Avg("rating"))["value"]

    def __str__(self):
        return str(self.user)


class SitterArea(models.Model):
    sitter = models.ForeignKey(Sitter, verbose_name="Догситтер", on_delete=models.CASCADE, related_name="area_links")
    area = models.ForeignKey(Area, verbose_name="Район", on_delete=models.PROTECT, related_name="sitter_links")

    class Meta:
        db_table = "sitter_area"
        verbose_name = "Район догситтера"
        verbose_name_plural = "Районы догситтеров"
        ordering = ["sitter_id", "area_id"]
        constraints = [models.UniqueConstraint(fields=["sitter", "area"], name="sitter_area_unique")]

    def __str__(self):
        return f"{self.sitter}: {self.area}"


class SitterBehavior(models.Model):
    sitter = models.ForeignKey(Sitter, verbose_name="Догситтер", on_delete=models.CASCADE, related_name="behavior_links")
    behavior = models.ForeignKey(Behavior, verbose_name="Компетенция", on_delete=models.PROTECT, related_name="sitter_links")

    class Meta:
        db_table = "sitter_behavior"
        verbose_name = "Компетенция догситтера"
        verbose_name_plural = "Компетенции догситтеров"
        ordering = ["sitter_id", "behavior_id"]
        constraints = [models.UniqueConstraint(fields=["sitter", "behavior"], name="sitter_behavior_unique")]

    def __str__(self):
        return f"{self.sitter}: {self.behavior}"


class ServiceType(models.TextChoices):
    WALK = "walk", "Выгул"
    BOARDING = "boarding", "Передержка"


class Slot(models.Model):
    sitter = models.ForeignKey(Sitter, verbose_name="Догситтер", on_delete=models.PROTECT, related_name="slots")
    start_at = models.DateTimeField("Начало интервала")
    end_at = models.DateTimeField("Конец интервала")
    service_type = models.CharField("Услуга", max_length=8, choices=ServiceType.choices, default=ServiceType.WALK)
    is_blocked = models.BooleanField("Заблокирован догситтером", default=False)

    class Meta:
        db_table = "slot"
        verbose_name = "Слот расписания"
        verbose_name_plural = "Слоты расписания"
        ordering = ["start_at", "pk"]
        constraints = [
            models.CheckConstraint(condition=Q(end_at__gt=F("start_at")), name="slot_end_after_start"),
            models.CheckConstraint(condition=Q(service_type__in=["walk", "boarding"]), name="slot_service_valid"),
            models.UniqueConstraint(fields=["sitter", "start_at", "end_at"], name="slot_interval_unique"),
        ]

    @property
    def status(self):
        if self.is_blocked:
            return "blocked"
        return "booked" if Order.objects.filter(slot_id=self.pk).exists() else "free"

    def clean(self):
        super().clean()
        if self.start_at and self.end_at and self.sitter_id:
            overlaps = Slot.objects.filter(sitter_id=self.sitter_id, start_at__lt=self.end_at, end_at__gt=self.start_at).exclude(pk=self.pk)
            if overlaps.exists():
                raise ValidationError("Интервал пересекается с другим слотом догситтера.")
            if self.pk and Order.objects.filter(slot_id=self.pk).exists():
                old = Slot.objects.get(pk=self.pk)
                if any(getattr(self, f) != getattr(old, f) for f in ("sitter_id", "start_at", "end_at", "service_type", "is_blocked")):
                    raise ValidationError("Нельзя изменять слот, связанный с заказом.")

    def __str__(self):
        return f"{self.sitter}: {self.start_at:%d.%m.%Y %H:%M}"


class Order(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Ожидает подтверждения"
        CONFIRMED = "confirmed", "Подтверждён"
        IN_PROGRESS = "in_progress", "В процессе"
        COMPLETED = "completed", "Завершён"
        CANCELLED = "cancelled", "Отменён"

    dog = models.ForeignKey(Dog, verbose_name="Собака", on_delete=models.PROTECT, related_name="orders")
    slot = models.OneToOneField(Slot, verbose_name="Забронированный слот", on_delete=models.PROTECT, related_name="order")
    total_price = models.DecimalField("Итоговая стоимость", max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))])
    status = models.CharField("Статус", max_length=12, choices=Status.choices, default=Status.PENDING)
    owner_wishes = models.TextField("Пожелания владельца", blank=True)
    created_at = models.DateTimeField("Дата создания", auto_now_add=True)

    class Meta:
        db_table = "booking_order"
        verbose_name = "Заказ"
        verbose_name_plural = "Заказы"
        ordering = ["-created_at", "-pk"]
        constraints = [
            models.CheckConstraint(condition=Q(total_price__gt=0), name="order_price_positive"),
            models.CheckConstraint(condition=Q(status__in=["pending", "confirmed", "in_progress", "completed", "cancelled"]), name="order_status_valid"),
        ]

    def clean(self):
        super().clean()
        if not self.dog_id or not self.slot_id:
            return
        # Совместимость проверяется при создании, не при закрытии старого заказа.
        if self.pk:
            old = Order.objects.get(pk=self.pk)
            if old.dog_id != self.dog_id or old.slot_id != self.slot_id:
                raise ValidationError("У существующего заказа нельзя менять собаку или слот.")
            return
        dog, slot = self.dog, self.slot
        sitter = slot.sitter
        errors = []
        if slot.is_blocked:
            errors.append("Слот заблокирован.")
        if slot.start_at <= timezone.now():
            errors.append("Начало услуги должно быть в будущем.")
        if sitter.verification_status != Sitter.Verification.APPROVED or not sitter.user.is_active:
            errors.append("Догситтер не допущен к заказам.")
        if dog.owner.user_id == sitter.user_id:
            errors.append("Нельзя заказать услугу у самого себя.")
        if dog.weight_kg > sitter.max_weight_kg:
            errors.append("Вес собаки превышает допустимый.")
        if dog.weight_kg > 25 and not sitter.accepts_large_dogs:
            errors.append("Догситтер не работает с крупными собаками.")
        if slot.service_type == ServiceType.BOARDING and not sitter.accepts_boarding:
            errors.append("Догситтер не принимает на передержку.")
        if not sitter.areas.filter(pk=dog.owner.area_id).exists():
            errors.append("Догситтер не обслуживает район владельца.")
        if dog.behaviors.exclude(pk__in=sitter.behaviors.values_list("pk", flat=True)).exists():
            errors.append("Не хватает компетенций по поведению собаки.")
        if Order.objects.filter(slot_id=self.slot_id).exists():
            errors.append("Слот уже использован в заказе.")
        if errors:
            raise ValidationError(errors)

    @property
    def owner(self):
        return self.dog.owner

    @property
    def sitter(self):
        return self.slot.sitter

    def __str__(self):
        return f"Заказ №{self.pk}: {self.dog.name}"


class WalkReport(models.Model):
    order = models.OneToOneField(Order, verbose_name="Заказ", on_delete=models.CASCADE, related_name="report")
    actual_start = models.DateTimeField("Фактическое начало")
    actual_end = models.DateTimeField("Фактическое окончание")
    route = models.TextField("Маршрут")
    is_fed = models.BooleanField("Питомец покормлен", default=False)
    paws_washed = models.BooleanField("Лапы помыты", default=False)
    photo = models.FileField("Фотография с прогулки", upload_to="reports/")
    sitter_comment = models.TextField("Комментарий догситтера", blank=True)
    published_at = models.DateTimeField("Дата публикации", auto_now_add=True)

    class Meta:
        db_table = "walk_report"
        verbose_name = "Отчёт о прогулке"
        verbose_name_plural = "Отчёты о прогулках"
        ordering = ["-published_at", "-pk"]
        constraints = [models.CheckConstraint(condition=Q(actual_end__gt=F("actual_start")), name="report_end_after_start")]

    @property
    def duration_minutes(self):
        return (self.actual_end - self.actual_start).total_seconds() / 60

    def clean(self):
        super().clean()
        if self.order_id and self.order.slot.service_type != ServiceType.WALK:
            raise ValidationError({"order": "Отчёт о прогулке привязывается к услуге выгула."})

    def __str__(self):
        return f"Отчёт по заказу №{self.order_id}"


class Review(models.Model):
    order = models.OneToOneField(Order, verbose_name="Завершённый заказ", on_delete=models.CASCADE, related_name="review")
    rating = models.PositiveSmallIntegerField("Оценка", validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField("Комментарий", blank=True)
    published_at = models.DateTimeField("Дата публикации", auto_now_add=True)

    class Meta:
        db_table = "review"
        verbose_name = "Отзыв"
        verbose_name_plural = "Отзывы"
        ordering = ["-published_at", "-pk"]
        constraints = [models.CheckConstraint(condition=Q(rating__gte=1, rating__lte=5), name="review_rating_range")]

    def clean(self):
        super().clean()
        if self.order_id and self.order.status != Order.Status.COMPLETED:
            raise ValidationError({"order": "Отзыв разрешён только после завершения заказа."})

    def __str__(self):
        return f"Заказ №{self.order_id}: {self.rating}/5"
