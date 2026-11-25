from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import patch
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from .models import (
    Area,
    Breed,
    Dog,
    Order,
    Owner,
    ServiceType,
    Sitter,
    SitterArea,
    Slot,
    User,
)


class NegativeExceptionsTests(TestCase):
    def setUp(self):
        self.area = Area.objects.create(
            name='Центральный',
            district='ЦАО',
            distance_coefficient=Decimal('1.00'),
        )
        self.breed = Breed.objects.create(name='Лабрадор')

        # Владелец и его питомец
        self.owner_user = User.objects.create_user(
            username='owner_test',
            email='owner@example.ru',
            password='Password123',
            first_name='Иван',
            last_name='Петров',
            role=User.Role.OWNER,
        )
        self.owner = Owner.objects.create(
            user=self.owner_user,
            area=self.area,
            pickup_address='ул. Ленина, д. 10',
            emergency_contact='+79001112233',
        )
        self.dog = Dog.objects.create(
            owner=self.owner,
            name='Рекс',
            breed=self.breed,
            birth_date=date(2022, 5, 10),
            weight_kg=Decimal('18.00'),
            sex=Dog.Sex.MALE,
        )

        # Догситтер и свободный слот в будущем
        self.sitter_user = User.objects.create_user(
            username='sitter_test',
            email='sitter@example.ru',
            password='Password123',
            first_name='Анна',
            last_name='Смирнова',
            role=User.Role.SITTER,
        )
        self.sitter = Sitter.objects.create(
            user=self.sitter_user,
            about='Большой опыт выгула собак средних и крупных пород в парках.',
            experience_years=4,
            max_weight_kg=Decimal('35.00'),
            accepts_large_dogs=True,
            walk_hour_rate=Decimal('600.00'),
            verification_status=Sitter.Verification.APPROVED,
        )
        SitterArea.objects.create(sitter=self.sitter, area=self.area)

        start = timezone.now() + timedelta(days=1, hours=2)
        self.slot = Slot.objects.create(
            sitter=self.sitter,
            start_at=start,
            end_at=start + timedelta(hours=1),
            service_type=ServiceType.WALK,
        )

        # Куратор для проверки аналитики
        self.curator_user = User.objects.create_user(
            username='curator_test',
            email='curator@example.ru',
            password='Password123',
            role=User.Role.CURATOR,
        )

    # Тест 1: обращение к несуществующей записи возвращает 404
    def test_nonexistent_sitter_returns_404(self):
        url = reverse('sitter_detail', kwargs={'pk': 999999})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    # Тест 2: доступ без прав возвращает 403
    def test_owner_accessing_analytics_returns_403(self):
        self.client.force_login(self.owner_user)
        url = reverse('analytics')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

    # Тест 3: форма с неверными данными не создаёт запись и показывает сообщение
    def test_invalid_dog_form_does_not_create_record_and_shows_error(self):
        self.client.force_login(self.owner_user)
        initial_count = Dog.objects.count()

        response = self.client.post(
            reverse('my_dogs'),
            data={
                'name': 'А',  # короче 2 символов
                'breed': self.breed.pk,
                'weight_kg': '500.0',  # превышает допустимый максимум 100 кг
                'birth_date': '2023-01-15',
                'sex': Dog.Sex.MALE,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Dog.objects.count(), initial_count)
        self.assertContains(response, 'Укажите кличку питомца (от 2 до 30 символов).')
        self.assertContains(response, 'Укажите реальный вес собаки от 0,5 до 100 кг.')

    # Тест 4: при ошибке в середине операции данные не меняются (откат транзакции)
    def test_transaction_rollback_on_error_in_middle_of_booking(self):
        self.client.force_login(self.owner_user)
        initial_orders_count = Order.objects.count()
        url = reverse('sitter_detail', kwargs={'pk': self.sitter.pk})

        with patch.object(Order, 'save', side_effect=RuntimeError('Сбой БД при сохранении заказа')):
            with self.assertRaises(RuntimeError):
                self.client.post(
                    url,
                    data={
                        'slot_id': self.slot.pk,
                        'dog': self.dog.pk,
                        'address': 'ул. Ленина, д. 10, под. 2',
                    },
                )

        self.assertEqual(Order.objects.count(), initial_orders_count)
        self.assertEqual(self.slot.status, 'free')

    # Тест 5: расчёт на пустой выборке не падает
    def test_analytics_calculation_on_empty_queryset_does_not_crash(self):
        Order.objects.all().delete()
        self.client.force_login(self.curator_user)

        response = self.client.get(reverse('analytics'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['total_orders'], 0)
        self.assertEqual(response.context['repeat_share'], 0)
        self.assertEqual(response.context['walk_pct'], 0)
        self.assertEqual(response.context['boarding_pct'], 0)
