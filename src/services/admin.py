from django.contrib import admin
from services.models import Institution, Bus, Organisation, Route, Stop, Registration, Schedule, Ticket, RouteFile, ReceiptFile, ExportedFile, ScheduleGroup


@admin.register(Organisation)
class OrganisationAdmin(admin.ModelAdmin):
    list_display = ('name', 'email')

@admin.register(Institution)
class InstitutionAdmin(admin.ModelAdmin):
    list_display = ('name', 'label', 'email')
    

@admin.register(Bus)
class BusAdmin(admin.ModelAdmin):
    list_display = ('registration_no', 'capacity')
    
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