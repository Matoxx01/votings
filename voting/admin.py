from django.contrib import admin
from voting.models import (
    Role, User, Maintainer, Voting, Subject, Count, UserData, VotingRecord
)


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
    list_display = ['title', 'start_date', 'finish_date', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['title', 'description']
    readonly_fields = ['created_at']


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ['name', 'id_voting', 'created_at']
    list_filter = ['id_voting', 'created_at']
    search_fields = ['name', 'id_voting__title']
    readonly_fields = ['created_at']


@admin.register(Count)
class CountAdmin(admin.ModelAdmin):
    list_display = ['id_subject', 'number', 'updated_at']
    list_filter = ['updated_at']
    search_fields = ['id_subject__name']
    readonly_fields = ['updated_at']


@admin.register(UserData)
class UserDataAdmin(admin.ModelAdmin):
    list_display = ['rut', 'id_voting', 'has_voted', 'register', 'created_at']
    list_filter = ['id_voting', 'has_voted', 'register', 'created_at']
    search_fields = ['rut', 'id_voting__title']
    readonly_fields = ['created_at']


@admin.register(VotingRecord)
class VotingRecordAdmin(admin.ModelAdmin):
    list_display = ['rut', 'id_voting', 'id_subject', 'voted_at']
    list_filter = ['id_voting', 'id_subject', 'voted_at']
    search_fields = ['rut', 'mail', 'id_voting__title']
    readonly_fields = ['voted_at']
