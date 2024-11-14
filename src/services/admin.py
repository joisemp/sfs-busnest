from django.contrib import admin
from services.models import Institution, Bus, Organisation


@admin.register(Organisation)
class OrganisationAdmin(admin.ModelAdmin):
    list_display = ('name', 'email')

@admin.register(Institution)
class InstitutionAdmin(admin.ModelAdmin):
    list_display = ('name', 'label', 'email')
    

@admin.register(Bus)
class BusAdmin(admin.ModelAdmin):
    list_display = ('label', 'bus_no')

