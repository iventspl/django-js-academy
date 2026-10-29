from django.contrib import admin

from .models import (
    AiAttempt,
    AiChoice,
    AiFlashcard,
    AiLesson,
    AiModule,
    AiProject,
    AiProjectCompletion,
    AiQuestion,
    AiTerm,
)


class AiChoiceInline(admin.TabularInline):
    model = AiChoice
    extra = 4


@admin.register(AiModule)
class AiModuleAdmin(admin.ModelAdmin):
    list_display = ("title", "stage", "difficulty", "duration_weeks", "lesson_count")
    list_filter = ("stage", "difficulty")
    search_fields = ("title", "subtitle", "description")
    prepopulated_fields = {"slug": ("title",)}


@admin.register(AiLesson)
class AiLessonAdmin(admin.ModelAdmin):
    list_display = ("title", "module", "minutes", "order")
    list_filter = ("module",)
    search_fields = ("title", "summary")


@admin.register(AiQuestion)
class AiQuestionAdmin(admin.ModelAdmin):
    list_display = ("prompt", "module", "difficulty")
    list_filter = ("module", "difficulty")
    search_fields = ("prompt", "explanation")
    inlines = [AiChoiceInline]


@admin.register(AiFlashcard)
class AiFlashcardAdmin(admin.ModelAdmin):
    list_display = ("front", "module", "difficulty")
    list_filter = ("module", "difficulty")
    search_fields = ("front", "back")


@admin.register(AiProject)
class AiProjectAdmin(admin.ModelAdmin):
    list_display = ("title", "module", "difficulty", "duration_hours")
    list_filter = ("difficulty", "module")
    search_fields = ("title", "tagline", "scenario")


@admin.register(AiTerm)
class AiTermAdmin(admin.ModelAdmin):
    list_display = ("term", "category", "module")
    list_filter = ("category", "module")
    search_fields = ("term", "definition", "example")


admin.site.register(AiAttempt)
admin.site.register(AiProjectCompletion)
