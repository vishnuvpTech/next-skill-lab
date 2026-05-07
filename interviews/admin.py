from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import AdminUser, Department, Topic, Question, InterviewLink, CandidateResponse, QuestionAnswer


@admin.register(AdminUser)
class AdminUserAdmin(BaseUserAdmin):
    list_display = ('email', 'name', 'role', 'is_active')
    list_filter = ('role', 'is_active')
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Info', {'fields': ('name', 'role')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser')}),
    )
    add_fieldsets = (
        (None, {'fields': ('email', 'name', 'password1', 'password2', 'role')}),
    )
    search_fields = ('email', 'name')
    ordering = ('email',)
    filter_horizontal = ()


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'topic_count', 'created_at')


@admin.register(Topic)
class TopicAdmin(admin.ModelAdmin):
    list_display = ('name', 'department', 'created_at')
    list_filter = ('department',)


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ('text', 'topic', 'level', 'created_at')
    list_filter = ('level', 'topic__department')


@admin.register(InterviewLink)
class InterviewLinkAdmin(admin.ModelAdmin):
    list_display = ('topic', 'level', 'question_count', 'time_per_question', 'is_active', 'created_at')
    list_filter = ('level', 'is_active')


@admin.register(CandidateResponse)
class CandidateResponseAdmin(admin.ModelAdmin):
    list_display = ('candidate_name', 'candidate_email', 'link', 'ai_score', 'submitted_at')


@admin.register(QuestionAnswer)
class QuestionAnswerAdmin(admin.ModelAdmin):
    list_display = ('response', 'question_text', 'is_recorded', 'ai_score')
