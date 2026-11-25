import re
from datetime import timedelta
from decimal import Decimal
from PIL import Image
from django import forms
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import Dog, User, Order, Slot, WalkReport, Review


def validate_image_file(file_obj):
    if not file_obj or not hasattr(file_obj, 'size'):
        return file_obj
    if file_obj.size > 5 * 1024 * 1024:
        raise ValidationError('Загрузите изображение в формате JPG, PNG или WebP размером не более 5 МБ.')
    valid_types = ('image/jpeg', 'image/png', 'image/webp')
    content_type = getattr(file_obj, 'content_type', '')
    if content_type not in valid_types:
        raise ValidationError('Загрузите изображение в формате JPG, PNG или WebP размером не более 5 МБ.')
    try:
        img = Image.open(file_obj)
        img.verify()
        if img.format not in ('JPEG', 'PNG', 'WEBP'):
            raise ValidationError('Загрузите изображение в формате JPG, PNG или WebP размером не более 5 МБ.')
        file_obj.seek(0)
    except ValidationError:
        raise
    except Exception:
        raise ValidationError('Загрузите изображение в формате JPG, PNG или WebP размером не более 5 МБ.')
    return file_obj


class DogForm(forms.ModelForm):
    class Meta:
        model = Dog
        fields = [
            'name',
            'breed',
            'weight_kg',
            'birth_date',
            'sex',
            'photo',
            'behaviors',
            'care_instructions',
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Рекс',
            }),
            'breed': forms.Select(attrs={
                'class': 'form-control',
            }),
            'weight_kg': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '15.5',
                'step': '0.5',
                'min': '0.5',
                'max': '100',
            }),
            'birth_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
            }),
            'sex': forms.Select(attrs={
                'class': 'form-control',
            }),
            'photo': forms.ClearableFileInput(attrs={
                'class': 'form-control',
                'accept': 'image/jpeg,image/png,image/webp',
            }),
            'behaviors': forms.CheckboxSelectMultiple(attrs={
                'class': 'checkbox-list',
            }),
            'care_instructions': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Особенности кормления, амуниции или поведения на прогулке',
            }),
        }

    def clean_name(self):
        name = self.cleaned_data.get('name', '').strip()
        if len(name) < 2 or len(name) > 30:
            raise ValidationError('Укажите кличку питомца (от 2 до 30 символов).')
        return name

    def clean_weight_kg(self):
        weight = self.cleaned_data.get('weight_kg')
        if weight is None or weight < Decimal('0.5') or weight > Decimal('100.0'):
            raise ValidationError('Укажите реальный вес собаки от 0,5 до 100 кг.')
        return weight

    def clean_birth_date(self):
        birth_date = self.cleaned_data.get('birth_date')
        if birth_date:
            today = timezone.localdate()
            age_years = (today - birth_date).days / 365.25
            if birth_date > today or age_years > 25:
                raise ValidationError('Укажите возраст в годах (от 0 до 25).')
        return birth_date

    def clean_photo(self):
        return validate_image_file(self.cleaned_data.get('photo'))


class RegisterForm(forms.ModelForm):
    role = forms.ChoiceField(
        label='Кто вы',
        choices=[(User.Role.OWNER, 'Владелец собаки'), (User.Role.SITTER, 'Догситтер')],
        widget=forms.RadioSelect,
        error_messages={'required': 'Выберите, кто вы: владелец собаки или догситтер.'},
    )
    password = forms.CharField(
        label='Пароль',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Минимум 8 символов'}),
    )
    password_confirm = forms.CharField(
        label='Повторите пароль',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Повторите пароль'}),
    )

    class Meta:
        model = User
        fields = ['role', 'username', 'first_name', 'last_name', 'email', 'phone']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Логин'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Иван'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Петров'}),
            'email': forms.EmailInput(
                attrs={'class': 'form-control', 'placeholder': 'ivan@example.ru'},
            ),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+7 900 000-00-00'}),
        }
        error_messages = {
            'email': {
                'invalid': 'Введите корректный адрес электронной почты.',
                'unique': 'Этот email уже зарегистрирован.',
            }
        }

    def clean_first_name(self):
        first_name = self.cleaned_data.get('first_name', '').strip()
        if not re.fullmatch(r'[А-ЯЁа-яё\s-]{2,50}', first_name):
            raise ValidationError('Введите имя и фамилию кириллицей (от 2 до 50 символов).')
        return first_name

    def clean_last_name(self):
        last_name = self.cleaned_data.get('last_name', '').strip()
        if not re.fullmatch(r'[А-ЯЁа-яё\s-]{2,50}', last_name):
            raise ValidationError('Введите имя и фамилию кириллицей (от 2 до 50 символов).')
        return last_name

    def clean_phone(self):
        raw_phone = self.cleaned_data.get('phone', '').strip()
        digits = re.sub(r'\D', '', raw_phone)
        if len(digits) != 11 or digits[0] not in ('7', '8'):
            raise ValidationError('Введите номер телефона в формате +7 900 000-00-00.')
        return f'+7{digits[1:]}'

    def clean_password(self):
        password = self.cleaned_data.get('password', '')
        if len(password) < 8 or not re.search(r'[A-Za-zА-Яа-я]', password) or not re.search(r'\d', password):
            raise ValidationError('Пароль должен содержать не менее 8 символов, включая буквы и цифры.')
        try:
            validate_password(password)
        except ValidationError:
            raise ValidationError('Пароль должен содержать не менее 8 символов, включая буквы и цифры.')
        return password

    def clean(self):
        cleaned_data = super().clean()
        p1 = cleaned_data.get('password')
        p2 = cleaned_data.get('password_confirm')
        if p1 and p2 and p1 != p2:
            self.add_error('password_confirm', 'Введённые пароли не совпадают.')
        return cleaned_data


class BookingForm(forms.Form):
    slot_id = forms.IntegerField(widget=forms.HiddenInput())
    dog = forms.ModelChoiceField(
        queryset=Dog.objects.none(),
        label='Выберите питомца',
        widget=forms.Select(attrs={'class': 'form-control'}),
        empty_label=None,
        error_messages={'required': 'Выберите питомца из списка.', 'invalid_choice': 'Выберите питомца из списка.'},
    )
    address = forms.CharField(
        label='Адрес встречи',
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'ул. Ленина, д. 10, под. 2',
        }),
    )

    def __init__(self, *args, owner=None, **kwargs):
        super().__init__(*args, **kwargs)
        if owner is not None:
            self.fields['dog'].queryset = Dog.objects.filter(owner=owner).select_related('breed')
            if owner.pickup_address and not self.initial.get('address'):
                self.fields['address'].initial = owner.pickup_address

    def clean_address(self):
        address = self.cleaned_data.get('address', '').strip()
        if len(address) < 5:
            raise ValidationError('Укажите точный адрес встречи с выгульщиком (минимум 5 символов).')
        return address


class SlotForm(forms.ModelForm):
    class Meta:
        model = Slot
        fields = ['start_at', 'end_at', 'service_type']
        widgets = {
            'start_at': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'end_at': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'service_type': forms.Select(attrs={'class': 'form-control'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        start_at = cleaned_data.get('start_at')
        end_at = cleaned_data.get('end_at')
        if start_at and start_at <= timezone.now():
            self.add_error('start_at', 'Время начала слота должно быть в будущем.')
        if start_at and end_at and end_at <= start_at:
            self.add_error('end_at', 'Время окончания должно быть позже времени начала слота.')
        return cleaned_data


class WalkReportForm(forms.ModelForm):
    class Meta:
        model = WalkReport
        fields = ['actual_start', 'actual_end', 'route', 'is_fed', 'paws_washed', 'photo', 'sitter_comment']
        widgets = {
            'actual_start': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'actual_end': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'route': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Как прошла прогулка...',
            }),
            'sitter_comment': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'photo': forms.ClearableFileInput(attrs={
                'class': 'form-control',
                'accept': 'image/jpeg,image/png,image/webp',
            }),
        }
        error_messages = {
            'photo': {'required': 'Прикрепите фотографию в формате JPG, PNG или WebP (до 5 МБ).'},
        }

    def clean_route(self):
        route = self.cleaned_data.get('route', '').strip()
        if len(route) < 10 or len(route) > 1000:
            raise ValidationError('Напишите короткий рассказ о прогулке (минимум 10 символов).')
        return route

    def clean_photo(self):
        return validate_image_file(self.cleaned_data.get('photo'))

    def clean(self):
        cleaned_data = super().clean()
        start = cleaned_data.get('actual_start')
        end = cleaned_data.get('actual_end')
        if start and end:
            minutes = (end - start).total_seconds() / 60
            if minutes < 15 or minutes > 1440:
                self.add_error('actual_end', 'Укажите длительность прогулки в минутах (от 15 до 1440).')
        return cleaned_data


class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ['rating', 'comment']
        widgets = {
            'rating': forms.Select(
                choices=[
                    (5, '5 — Отлично'),
                    (4, '4 — Хорошо'),
                    (3, '3 — Нормально'),
                    (2, '2 — Плохо'),
                    (1, '1 — Ужасно'),
                ],
                attrs={'class': 'form-control'},
            ),
            'comment': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Поделитесь впечатлениями о прогулке и работе догситтера',
            }),
        }