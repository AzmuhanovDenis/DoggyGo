import csv
from datetime import datetime
from decimal import Decimal
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Avg, Count, Q, Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from .forms import BookingForm, DogForm, RegisterForm
from .models import Area, Behavior, Dog, Order, Owner, ServiceType, Sitter, Slot



def index(request):
    areas = Area.objects.all()
    return render(request, 'index.html', {'areas': areas})


def how_it_works(request):
    return render(request, 'how_it_works.html')


def sitter_catalog(request):
    sitters_qs = (
        Sitter.objects.filter(verification_status=Sitter.Verification.APPROVED, user__is_active=True)
        .select_related('user')
        .prefetch_related('areas', 'behaviors')
        .annotate(
            avg_rating=Avg('slots__order__review__rating'),
            reviews_count=Count('slots__order__review', distinct=True),
        )
    )

    q = request.GET.get('q', '').strip()
    area_id = request.GET.get('area', '').strip()
    weight_raw = request.GET.get('weight', '').strip()
    selected_behaviors = request.GET.getlist('behaviors')
    service_type = request.GET.get('service_type', '').strip()
    sort = request.GET.get('sort', 'rating')

    if q:
        sitters_qs = sitters_qs.filter(
            Q(user__first_name__icontains=q)
            | Q(user__last_name__icontains=q)
            | Q(user__username__icontains=q)
        )

    if area_id.isdigit():
        sitters_qs = sitters_qs.filter(areas__id=int(area_id))

    if service_type == ServiceType.BOARDING:
        sitters_qs = sitters_qs.filter(accepts_boarding=True)

    if selected_behaviors:
        behavior_ids = [int(b) for b in selected_behaviors if b.isdigit()]
        for b_id in behavior_ids:
            sitters_qs = sitters_qs.filter(behaviors__id=b_id)

    sort_map = {
        'rating': ['-avg_rating', '-experience_years', 'pk'],
        'price_asc': ['walk_hour_rate', '-avg_rating', 'pk'],
        'price_desc': ['-walk_hour_rate', '-avg_rating', 'pk'],
        'experience': ['-experience_years', '-avg_rating', 'pk'],
    }
    sitters_qs = sitters_qs.distinct().order_by(*sort_map.get(sort, sort_map['rating']))

    user_weight = None
    if weight_raw:
        try:
            user_weight = Decimal(weight_raw.replace(',', '.'))
        except Exception:
            user_weight = None

    sitters_list = list(sitters_qs)
    for sitter in sitters_list:
        sitter.weight_incompatible = False
        if user_weight is not None:
            if user_weight > sitter.max_weight_kg or (user_weight > 25 and not sitter.accepts_large_dogs):
                sitter.weight_incompatible = True

    paginator = Paginator(sitters_list, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    query_params = request.GET.copy()
    query_params.pop('page', None)

    context = {
        'page_obj': page_obj,
        'total_count': paginator.count,
        'areas': Area.objects.all(),
        'behaviors': Behavior.objects.all(),
        'q': q,
        'selected_area': area_id,
        'weight': weight_raw,
        'user_weight': user_weight,
        'selected_behaviors': [int(b) for b in selected_behaviors if b.isdigit()],
        'sort': sort,
        'query_string': query_params.urlencode(),
    }
    return render(request, 'catalog.html', context)


def sitter_detail(request, pk):
    sitter = get_object_or_404(
        Sitter.objects.select_related('user')
        .prefetch_related('areas', 'behaviors')
        .annotate(
            avg_rating=Avg('slots__order__review__rating'),
            reviews_count=Count('slots__order__review', distinct=True),
        ),
        pk=pk,
    )

    slots = Slot.objects.filter(sitter=sitter, start_at__gte=timezone.now()).select_related('order').order_by('start_at')[:12]

    owner = getattr(request.user, 'owner_profile', None) if request.user.is_authenticated else None
    form = BookingForm(request.POST or None, owner=owner)

    if request.method == 'POST':
        if not request.user.is_authenticated or owner is None:
            messages.error(request, 'Для бронирования прогулки войдите как владелец собаки.')
            return redirect('login')

        if form.is_valid():
            slot = get_object_or_404(Slot, pk=form.cleaned_data['slot_id'], sitter=sitter)
            dog = form.cleaned_data['dog']
            address = form.cleaned_data['address']

            area_coeff = owner.area.distance_coefficient if owner.area else Decimal('1.00')
            base_rate = sitter.boarding_day_rate if slot.service_type == ServiceType.BOARDING else sitter.walk_hour_rate
            total_price = (base_rate * area_coeff).quantize(Decimal('0.01'))

            try:
                with transaction.atomic():
                    order = Order(
                        dog=dog,
                        slot=slot,
                        total_price=total_price,
                        owner_wishes=f'Адрес встречи: {address}',
                    )
                    order.full_clean()
                    order.save()
                messages.success(request, f'Заказ №{order.pk} успешно оформлен!')
                return redirect('order_detail', pk=order.pk)
            except ValidationError as exc:
                for err in exc.messages:
                    messages.error(request, err)

    context = {
        'sitter': sitter,
        'slots': slots,
        'form': form,
        'owner': owner,
    }
    return render(request, 'sitter_detail.html', context)

@login_required
def my_dogs(request):
    owner = getattr(request.user, 'owner_profile', None)
    if owner is None:
        default_area = Area.objects.first()
        if default_area:
            owner = Owner.objects.create(
                user=request.user,
                area=default_area,
                pickup_address='Не указан',
                emergency_contact=request.user.phone or '+79000000000',
            )
        else:
            messages.error(request, 'Сначала добавьте хотя бы один район в админке.')
            return redirect('index')

    if request.method == 'POST':
        form = DogForm(request.POST, request.FILES)
        if form.is_valid():
            dog = form.save(commit=False)
            dog.owner = owner
            dog.full_clean()
            dog.save()
            form.save_m2m()
            messages.success(request, f'Карточка питомца «{dog.name}» добавлена.')
            return redirect('my_dogs')
    else:
        form = DogForm()

    dogs = Dog.objects.filter(owner=owner).select_related('breed').prefetch_related('behaviors')
    today = timezone.localdate()
    for dog in dogs:
        years = today.year - dog.birth_date.year - ((today.month, today.day) < (dog.birth_date.month, dog.birth_date.day))
        dog.age_years = max(0, years)

    return render(request, 'my_dogs.html', {'dogs': dogs, 'form': form})


@login_required
def edit_dog(request, pk):
    owner = get_object_or_404(Owner, user=request.user)
    dog = get_object_or_404(Dog, pk=pk)
    if dog.owner_id != owner.id:
        raise PermissionDenied('Вы можете редактировать только своих питомцев.')

    if request.method == 'POST':
        form = DogForm(request.POST, request.FILES, instance=dog)
        if form.is_valid():
            updated_dog = form.save(commit=False)
            updated_dog.full_clean()
            updated_dog.save()
            form.save_m2m()
            messages.success(request, f'Данные питомца «{dog.name}» обновлены.')
            return redirect('my_dogs')
    else:
        form = DogForm(instance=dog)

    return render(request, 'edit_dog.html', {'form': form, 'dog': dog})


@login_required
def delete_dog(request, pk):
    owner = get_object_or_404(Owner, user=request.user)
    dog = get_object_or_404(Dog, pk=pk)
    if dog.owner_id != owner.id:
        raise PermissionDenied('Вы можете удалять только своих питомцев.')

    if request.method == 'POST':
        if dog.orders.exists():
            messages.error(request, 'Нельзя удалить питомца, у которого уже есть заказы.')
        else:
            dog_name = dog.name
            dog.delete()
            messages.success(request, f'Карточка питомца «{dog_name}» удалена.')
    return redirect('my_dogs')


@login_required
def my_orders(request):
    orders = (
        Order.objects.filter(Q(dog__owner__user=request.user) | Q(slot__sitter__user=request.user))
        .select_related('dog', 'slot', 'slot__sitter__user')
        .order_by('-created_at')
    )
    paginator = Paginator(orders, 20)
    page_obj = paginator.get_page(request.GET.get('page'))
    return render(request, 'my_orders.html', {'page_obj': page_obj})


@login_required
def order_detail(request, pk):
    order = get_object_or_404(
        Order.objects.select_related('dog', 'dog__owner__user', 'slot', 'slot__sitter__user'),
        pk=pk,
    )
    is_owner = order.dog.owner.user_id == request.user.id
    is_sitter = order.slot.sitter.user_id == request.user.id
    is_staff = request.user.is_staff or request.user.role in ('curator', 'admin')

    if not (is_owner or is_sitter or is_staff):
        raise PermissionDenied('Нет доступа к чужому заказу.')

    report = getattr(order, 'report', None)
    return render(request, 'order_detail.html', {'order': order, 'report': report})


@login_required
def order_receipt(request, pk):
    order = get_object_or_404(
        Order.objects.select_related('dog', 'dog__owner__user', 'slot', 'slot__sitter__user'),
        pk=pk,
    )
    is_owner = order.dog.owner.user_id == request.user.id
    is_sitter = order.slot.sitter.user_id == request.user.id
    is_staff = request.user.is_staff or request.user.role in ('curator', 'admin')
    if not (is_owner or is_sitter or is_staff):
        raise PermissionDenied('Нет доступа к квитанции.')
    return render(request, 'order_receipt.html', {'order': order})


def analytics(request):
    orders_qs = Order.objects.exclude(status=Order.Status.CANCELLED)

    date_from = request.GET.get('date_from', '').strip()
    date_to = request.GET.get('date_to', '').strip()
    if date_from:
        try:
            dt_from = datetime.strptime(date_from, '%Y-%m-%d').date()
            orders_qs = orders_qs.filter(created_at__date__gte=dt_from)
        except ValueError:
            pass
    if date_to:
        try:
            dt_to = datetime.strptime(date_to, '%Y-%m-%d').date()
            orders_qs = orders_qs.filter(created_at__date__lte=dt_to)
        except ValueError:
            pass

    stats = orders_qs.aggregate(
        total_orders=Count('id'),
        total_revenue=Sum('total_price'),
        avg_check=Avg('total_price'),
    )
    total_orders = stats['total_orders'] or 0
    total_revenue = stats['total_revenue'] or Decimal('0.00')
    avg_check = stats['avg_check'] or Decimal('0.00')

    owners_with_orders = orders_qs.values('dog__owner_id').annotate(cnt=Count('id'))
    total_unique_owners = owners_with_orders.count()
    repeat_owners = owners_with_orders.filter(cnt__gt=1).count()
    repeat_share = round((repeat_owners / total_unique_owners) * 100, 1) if total_unique_owners else 0

    area_stats_raw = (
        orders_qs.values('dog__owner__area__name')
        .annotate(count=Count('id'))
        .order_by('-count')
    )
    area_stats = []
    for item in area_stats_raw:
        pct = round((item['count'] / total_orders) * 100) if total_orders else 0
        area_stats.append({
            'name': item['dog__owner__area__name'] or 'Не указан',
            'count': item['count'],
            'percent': pct,
        })

    walk_count = orders_qs.filter(slot__service_type=ServiceType.WALK).count()
    boarding_count = orders_qs.filter(slot__service_type=ServiceType.BOARDING).count()
    walk_pct = round((walk_count / total_orders) * 100) if total_orders else 0
    boarding_pct = round((boarding_count / total_orders) * 100) if total_orders else 0

    pending_sitters_count = Sitter.objects.filter(verification_status=Sitter.Verification.PENDING).count()

    context = {
        'date_from': date_from,
        'date_to': date_to,
        'total_orders': total_orders,
        'total_revenue': total_revenue,
        'avg_check': avg_check,
        'repeat_share': repeat_share,
        'area_stats': area_stats,
        'walk_count': walk_count,
        'boarding_count': boarding_count,
        'walk_pct': walk_pct,
        'boarding_pct': boarding_pct,
        'pending_sitters_count': pending_sitters_count,
    }
    return render(request, 'analytics.html', context)


def analytics_export_csv(request):
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="doggygo_analytics.csv"'
    response.write('\ufeff')
    writer = csv.writer(response, delimiter=';')
    writer.writerow(['Номер заказа', 'Дата создания', 'Питомец', 'Владелец', 'Догситтер', 'Услуга', 'Статус', 'Сумма (руб.)'])

    orders = Order.objects.select_related('dog', 'dog__owner__user', 'slot', 'slot__sitter__user')
    for order in orders:
        writer.writerow([
            order.pk,
            order.created_at.strftime('%d.%m.%Y %H:%M'),
            order.dog.name,
            str(order.dog.owner),
            str(order.slot.sitter),
            order.slot.get_service_type_display(),
            order.get_status_display(),
            f'{order.total_price:.2f}',
        ])
    return response


def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            messages.success(request, f'Добро пожаловать, {user}!')
            return redirect('index')
        messages.error(request, 'Неверный логин или пароль.')
    return render(request, 'login.html')


def logout_view(request):
    logout(request)
    messages.info(request, 'Вы вышли из аккаунта.')
    return redirect('index')


def register_view(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password'])
            user.save()
            default_area = Area.objects.first()
            if default_area:
                Owner.objects.create(
                    user=user,
                    area=default_area,
                    pickup_address='Укажите адрес в профиле',
                    emergency_contact=user.phone or '+79000000000',
                )
            login(request, user)
            messages.success(request, 'Регистрация прошла успешно!')
            return redirect('my_dogs')
    else:
        form = RegisterForm()
    return render(request, 'register.html', {'form': form})

