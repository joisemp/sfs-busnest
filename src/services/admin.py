"""
Django admin configuration for the services app.

This module registers models from the services app with the Django admin interface and customizes their display for easier management by administrators.

Admin Classes:
    OrganisationAdmin: Admin interface for Organisation model, showing name and email.
    InstitutionAdmin: Admin interface for Institution model, showing name, label, and email.
    BusAdmin: Admin interface for Bus model, showing registration number and capacity.
    RouteAdmin: Admin interface for Route model, showing organization and name.
    StopAdmin: Admin interface for Stop model, showing organization and name.
    RegistrationAdmin: Admin interface for Registration model, showing organization and name.

Direct Registrations:
    Schedule, Ticket, RouteFile, ReceiptFile, ExportedFile, ScheduleGroup: Registered with default admin options.
"""

from django.contrib import admin
from services.models import Institution, Bus, RefuelingRecord, Organisation, Route, Stop, Registration, Schedule, Ticket, RouteFile, ReceiptFile, ExportedFile, ScheduleGroup, TripExpense


@admin.register(Organisation)
class OrganisationAdmin(admin.ModelAdmin):
    list_display = ('name', 'email')

@admin.register(Institution)
class InstitutionAdmin(admin.ModelAdmin):
    list_display = ('name', 'label', 'email')
    

@admin.register(Bus)
class BusAdmin(admin.ModelAdmin):
    list_display = ('registration_no', 'capacity')


@admin.register(RefuelingRecord)
class RefuelingRecordAdmin(admin.ModelAdmin):
    list_display = ('bus', 'refuel_date', 'fuel_amount', 'fuel_cost', 'fuel_type', 'odometer_reading')
    list_filter = ('fuel_type', 'refuel_date')
    search_fields = ('bus__registration_no', 'notes')
    date_hierarchy = 'refuel_date'
    
@admin.register(Route)
class RouteAdmin(admin.ModelAdmin):
    list_display = ('org', 'name')
    

@admin.register(Stop)
class StopAdmin(admin.ModelAdmin):
    list_display = ('org', 'name',)


@admin.register(Registration)
class RegistrationAdmin(admin.ModelAdmin):
    list_display = ('org', 'name',)


admin.site.register(Schedule)

admin.site.register(Ticket)

admin.site.register(RouteFile)

admin.site.register(ReceiptFile)

admin.site.register(ExportedFile)

admin.site.register(ScheduleGroup)


@admin.register(TripExpense)
class TripExpenseAdmin(admin.ModelAdmin):
    list_display = ('bus_assignment', 'total_expense', 'driver_bonus', 'recorded_by', 'recorded_at')
    list_filter = ('recorded_at',)
    search_fields = ('bus_assignment__bus__registration_no', 'bus_assignment__reservation_request__event_name')
    readonly_fields = ('total_expense', 'recorded_at', 'updated_at')