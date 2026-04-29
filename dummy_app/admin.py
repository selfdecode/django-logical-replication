from django.contrib import admin

from dummy_app.models import Marker, Outcome, Result, Unit


@admin.register(Unit)
class UnitAdmin(admin.ModelAdmin):
    pass


@admin.register(Outcome)
class OutcomeAdmin(admin.ModelAdmin):
    pass


@admin.register(Marker)
class MarkerAdmin(admin.ModelAdmin):
    pass


@admin.register(Result)
class ResultAdmin(admin.ModelAdmin):
    pass
