from django.contrib import admin

from .models import (
    StudyNote,
    AppBlueprint,
    ArchitectureCase,
    Attempt,
    AttemptQuestion,
    Cheatsheet,
    Choice,
    Flashcard,
    FlashcardReview,
    Learner,
    Question,
    ReleaseNote,
    ReleaseSeries,
    StudyEvent,
    Topic,
)


class ChoiceInline(admin.TabularInline):
    model = Choice
    extra = 0
    fields = ("text", "is_correct", "position")


@admin.register(Topic)
class TopicAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "order", "glyph", "accent")
    list_editable = ("order",)
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ("short_prompt", "topic", "difficulty", "is_active", "position")
    list_filter = ("topic", "difficulty", "is_active")
    search_fields = ("prompt", "explanation", "key")
    inlines = [ChoiceInline]

    @admin.display(description="Prompt")
    def short_prompt(self, obj):
        return obj.prompt[:90]


@admin.register(Flashcard)
class FlashcardAdmin(admin.ModelAdmin):
    list_display = ("front", "topic", "difficulty", "position")
    list_filter = ("topic", "difficulty")
    search_fields = ("front", "back", "key")


class AttemptQuestionInline(admin.TabularInline):
    model = AttemptQuestion
    extra = 0
    readonly_fields = ("question", "position", "selected", "is_correct", "answered_at")
    can_delete = False


@admin.register(Attempt)
class AttemptAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "learner",
        "scope_label",
        "difficulty_label",
        "length",
        "current_index",
        "completed_at",
    )
    list_filter = ("difficulty", "completed_at")
    inlines = [AttemptQuestionInline]


admin.site.register(Learner)
admin.site.register(FlashcardReview)
admin.site.register(StudyEvent)


@admin.register(Cheatsheet)
class CheatsheetAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "topic", "order")
    list_filter = ("category", "topic")
    search_fields = ("title", "summary", "when_to_use", "code")


@admin.register(AppBlueprint)
class AppBlueprintAdmin(admin.ModelAdmin):
    list_display = ("name", "complexity", "topic", "order")
    list_filter = ("complexity", "topic")
    search_fields = ("name", "tagline", "problem", "stack_notes")


@admin.register(ArchitectureCase)
class ArchitectureCaseAdmin(admin.ModelAdmin):
    list_display = ("name", "complexity", "topic", "order")
    list_filter = ("complexity", "topic")
    search_fields = ("name", "tagline", "scenario", "decisions")


@admin.register(ReleaseNote)
class ReleaseNoteAdmin(admin.ModelAdmin):
    list_display = ("version", "kind", "released_on", "headline")
    list_filter = ("kind", "released_on")
    search_fields = ("version", "headline", "summary")


@admin.register(ReleaseSeries)
class ReleaseSeriesAdmin(admin.ModelAdmin):
    list_display = ("series", "latest_version", "status", "extended_ends")
    list_filter = ("status",)



@admin.register(StudyNote)
class StudyNoteAdmin(admin.ModelAdmin):
    list_display = ("title", "learner", "topic", "is_bookmarked", "updated_at")
    list_filter = ("is_bookmarked", "topic")
    search_fields = ("title", "body")
