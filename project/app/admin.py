from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import (
    Area,
    Behavior,
    Breed,
    Dog,
    DogBehavior,
    Order,
    Owner,
    Review,
    Sitter,
    SitterArea,
    SitterBehavior,
    Slot,
    User,
    WalkReport,
)


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'role', 'is_staff')
    list_filter = ('role', 'is_staff', 'is_active')
    fieldsets = UserAdmin.fieldsets + (
        ('Дополнительные данные', {'fields': ('phone', 'role')}),
    )


class SitterAreaInline(admin.TabularInline):
    model = SitterArea
    extra = 1


class SitterBehaviorInline(admin.TabularInline):
    model = SitterBehavior
    extra = 1


@admin.register(Sitter)
class SitterAdmin(admin.ModelAdmin):
    list_display = ('user', 'experience_years', 'max_weight_kg', 'walk_hour_rate', 'verification_status')
    list_filter = ('verification_status', 'accepts_large_dogs', 'accepts_boarding')
    search_fields = ('user__username', 'user__first_name', 'user__last_name')
    inlines = [SitterAreaInline, SitterBehaviorInline]

    def _is_curator(self, request):
            return request.user.is_authenticated and (
                request.user.is_superuser or getattr(request.user, 'role', '') in ('curator', 'admin')
            )
    
    def has_module_permission(self, request):
        return self._is_curator(request)
    
    def has_view_permission(self, request, obj=None):
        return self._is_curator(request)
    
    def has_change_permission(self, request, obj=None):
        return self._is_curator(request)


class DogBehaviorInline(admin.TabularInline):
    model = DogBehavior
    extra = 1

@admin.register(Dog)
class DogAdmin(admin.ModelAdmin):
    list_display = ('name', 'breed', 'owner', 'weight_kg', 'sex', 'is_vaccinated')
    list_filter = ('breed', 'sex', 'is_vaccinated')
    search_fields = ('name', 'owner__user__username')
    inlines = [DogBehaviorInline]


@admin.register(Area)
class AreaAdmin(admin.ModelAdmin):
    list_display = ('name', 'district', 'distance_coefficient')


@admin.register(Breed)
class BreedAdmin(admin.ModelAdmin):
    search_fields = ('name',)


@admin.register(Behavior)
class BehaviorAdmin(admin.ModelAdmin):
    list_display = ('name', 'difficulty')


@admin.register(Owner)
class OwnerAdmin(admin.ModelAdmin):
    list_display = ('user', 'area', 'pickup_address', 'emergency_contact')


@admin.register(Slot)
class SlotAdmin(admin.ModelAdmin):
    list_display = ('sitter', 'start_at', 'end_at', 'service_type', 'is_blocked')
    list_filter = ('service_type', 'is_blocked')


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'dog', 'slot', 'total_price', 'status', 'created_at')
    list_filter = ('status',)


@admin.register(WalkReport)
class WalkReportAdmin(admin.ModelAdmin):
    list_display = ('order', 'actual_start', 'actual_end', 'is_fed', 'paws_washed')


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('order', 'rating', 'published_at')
