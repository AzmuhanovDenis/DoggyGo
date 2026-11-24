from django import forms
from django.core.exceptions import ValidationError
from .models import Dog, User, Order, Slot, WalkReport, Review
from PIL import Image
from django.contrib.auth.password_validation import validate_password


def validate_image_file(file_obj):
    if not file_obj or not hasattr(file_obj, 'size'):
        return file_obj
    if file_obj.size > 10 * 1024 * 1024:
        raise ValidationError('Размер изображения не должен превышать 10 МБ.')
    valid_types = ('image/jpeg', 'image/png', 'image/webp')
    content_type = getattr(file_obj, 'content_type', '')
    if content_type not in valid_types:
        raise ValidationError('Допускаются только изображения формата JPG, PNG или WebP.')
    try:
        img = Image.open(file_obj)
        img.verify()
        if img.format not in ('JPEG', 'PNG', 'WEBP'):
            raise ValidationError('Файл не является корректным изображением JPG, PNG или WebP.')
        file_obj.seek(0)
    except Exception:
        raise ValidationError('Загруженный файл повреждён или не является изображением.')
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
                'placeholder': 'Например, Арчи',
            }),
            'breed': forms.Select(attrs={
                'class': 'form-control',
            }),
            'weight_kg': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '12.5',
                'step': '0.1',
                'min': '0.1',
                'max': '150',
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

    def clean_photo(self):
        return validate_image_file(self.cleaned_data.get('photo'))


class BookingForm(forms.Form):
    slot_id = forms.IntegerField(widget=forms.HiddenInput())
    dog = forms.ModelChoiceField(
        queryset=Dog.objects.none(),
        label='Выберите питомца',
        widget=forms.Select(attrs={'class': 'form-control'}),
        empty_label=None,
    )
    address = forms.CharField(
        label='Адрес встречи',
        max_length=255,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'ул. Ленина, д. 14, подъезд 2',
        }),
    )

    def __init__(self, *args, owner=None, **kwargs):
        super().__init__(*args, **kwargs)
        if owner is not None:
            self.fields['dog'].queryset = Dog.objects.filter(owner=owner).select_related('breed')
            if owner.pickup_address and not self.initial.get('address'):
                self.fields['address'].initial = owner.pickup_address


class RegisterForm(forms.ModelForm):
    password = forms.CharField(
        label='Пароль',
        min_length=8,
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Минимум 8 символов'}),
    )
    password_confirm = forms.CharField(
        label='Повторите пароль',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Повторите пароль'}),
    )

    class Meta:
        model = User
        fields = {
            'username': 'Логин', 
            'first_name': 'Имя', 
            'last_name': 'Фамилия', 
            'email': 'Электронная почта', 
            'phone': 'Телефон'
        }
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Логин'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Имя'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Фамилия'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'name@example.ru'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+79001234567'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        p1 = cleaned_data.get('password')
        p2 = cleaned_data.get('password_confirm')
        if p1 and p2 and p1 != p2:
            self.add_error('password_confirm', 'Пароли не совпадают.')
        if p1:
            validate_password(p1)
        return cleaned_data


class SlotForm(forms.ModelForm):
    class Meta:
        model = Slot
        fields = ['start_at', 'end_at', 'service_type']
        widgets = {
            'start_at': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'end_at': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'service_type': forms.Select(attrs={'class': 'form-control'}),
        }


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
                'placeholder': 'Укажите координаты или описание маршрута прогулки',
            }),
            'sitter_comment': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'photo': forms.ClearableFileInput(attrs={
                'class': 'form-control',
                'accept': 'image/jpeg,image/png,image/webp',
            }),
        }

    def clean_photo(self):
        return validate_image_file(self.cleaned_data.get('photo'))


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
