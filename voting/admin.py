from django.contrib import admin, messages
from voting.models import (
    Role, User, Maintainer, Voting, Subject, Count, UserData, VotingRecord
)


class NoDeleteMixin:
    """Impide eliminar registros desde el admin"""
    def has_delete_permission(self, request, obj=None):
        return False


class NoAddMixin:
    """Impide crear registros desde el admin"""
    def has_add_permission(self, request):
        return False


class ReadOnlyMixin(NoDeleteMixin, NoAddMixin):
    """Hace un modelo completamente de solo lectura en el admin"""
    def has_change_permission(self, request, obj=None):
        return False


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ['name', 'created_at']
    search_fields = ['name']


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ['name', 'lastname', 'rut', 'mail', 'created_at']
    search_fields = ['name', 'lastname', 'rut', 'mail']
    readonly_fields = ['created_at']


@admin.register(Maintainer)
class MaintainerAdmin(admin.ModelAdmin):
    list_display = ['name', 'lastname', 'mail', 'id_role', 'is_active', 'created_at']
    list_filter = ['id_role', 'is_active', 'created_at']
    search_fields = ['name', 'lastname', 'mail']
    readonly_fields = ['created_at']


@admin.register(Voting)
class VotingAdmin(admin.ModelAdmin):
    list_display = ['title', 'start_date', 'finish_date', 'created_at']
    list_filter = ['created_at']
    search_fields = ['title', 'description']
    readonly_fields = ['created_at']


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ['name', 'id_voting', 'created_at']
    list_filter = ['id_voting', 'created_at']
    search_fields = ['name', 'id_voting__title']
    readonly_fields = ['name', 'description', 'id_voting', 'created_at']

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Count)
class CountAdmin(ReadOnlyMixin, admin.ModelAdmin):
    """Conteos de votos - SOLO LECTURA. Los conteos se derivan de VotingRecords."""
    list_display = ['id_subject', 'number', 'verified_count', 'is_consistent', 'updated_at']
    list_filter = ['updated_at']
    search_fields = ['id_subject__name']

    @admin.display(description='Conteo verificado')
    def verified_count(self, obj):
        return obj.get_verified_count()

    @admin.display(description='Íntegro', boolean=True)
    def is_consistent(self, obj):
        return obj.is_consistent()


@admin.register(UserData)
class UserDataAdmin(admin.ModelAdmin):
    list_display = ['rut', 'id_voting', 'has_voted', 'register', 'created_at']
    list_filter = ['id_voting', 'has_voted', 'register', 'created_at']
    search_fields = ['rut', 'id_voting__title']
    readonly_fields = ['rut', 'id_voting', 'has_voted', 'register', 'created_at']

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(VotingRecord)
class VotingRecordAdmin(ReadOnlyMixin, admin.ModelAdmin):
    """Registros de votos - SOLO LECTURA. No se pueden crear, editar ni eliminar."""
    list_display = ['pk', 'id_voting', 'id_subject', 'integrity_status']
    list_filter = ['id_voting']
    search_fields = ['id_voting__title', 'id_subject__name']
    actions = ['verify_chain_action']

    @admin.display(description='Hash íntegro', boolean=True)
    def integrity_status(self, obj):
        return obj.verify_integrity()

    @admin.action(description='Verificar cadena de integridad de la votación')
    def verify_chain_action(self, request, queryset):
        voting_ids = queryset.values_list('id_voting_id', flat=True).distinct()
        from voting.models import VotingRecord as VR
        for vid in voting_ids:
            ok, broken_at = VR.verify_chain(vid)
            if ok:
                self.message_user(request, f"Votación #{vid}: cadena íntegra ✓", messages.SUCCESS)
            else:
                self.message_user(request, f"Votación #{vid}: cadena ROTA en registro #{broken_at} ✗", messages.ERROR)
