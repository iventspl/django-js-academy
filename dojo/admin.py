from django.contrib import admin

from .models import (
    DjangoCapstoneProgress,
    DjangoFeature,
    DjangoInterviewPractice,
    DjangoTrackProgress,
    HandbookExplanation,
    HandbookFeedback,
    HandbookLabProgress,
    HandbookNote,
    HandbookProgress,
    HandbookSearchLog,
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


@admin.register(HandbookProgress)
class HandbookProgressAdmin(admin.ModelAdmin):
    list_display = ("chapter_slug", "learner", "is_read", "is_bookmarked", "last_seen_at")
    list_filter = ("is_read", "is_bookmarked")
    search_fields = ("chapter_slug",)
    readonly_fields = ("last_seen_at", "read_at")


@admin.register(HandbookNote)
class HandbookNoteAdmin(admin.ModelAdmin):
    list_display = ("chapter_slug", "section_id", "learner", "is_bookmarked", "updated_at")
    list_filter = ("is_bookmarked",)
    search_fields = ("chapter_slug", "section_id", "body")
    readonly_fields = ("updated_at",)


@admin.register(HandbookFeedback)
class HandbookFeedbackAdmin(admin.ModelAdmin):
    list_display = ("chapter_slug", "helpful", "learner", "updated_at")
    list_filter = ("helpful",)
    search_fields = ("chapter_slug", "comment")
    readonly_fields = ("created_at", "updated_at")


@admin.register(DjangoFeature)
class DjangoFeatureAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "is_new", "order", "released_on")
    list_filter = ("category", "is_new")
    search_fields = ("title", "summary")
    prepopulated_fields = {"slug": ("title",)}


@admin.register(DjangoTrackProgress)
class DjangoTrackProgressAdmin(admin.ModelAdmin):
    list_display = ("track_slug", "learner", "completed_at", "updated_at")
    search_fields = ("track_slug", "evidence_what")


@admin.register(DjangoCapstoneProgress)
class DjangoCapstoneProgressAdmin(admin.ModelAdmin):
    list_display = ("capstone_slug", "learner", "completed_at", "updated_at")
    search_fields = ("capstone_slug", "evidence_what")


@admin.register(DjangoInterviewPractice)
class DjangoInterviewPracticeAdmin(admin.ModelAdmin):
    list_display = ("question_slug", "rating", "learner", "due_on", "repetitions")
    list_filter = ("rating",)
    search_fields = ("question_slug", "answer")


@admin.register(HandbookExplanation)
class HandbookExplanationAdmin(admin.ModelAdmin):
    list_display = ("chapter_slug", "rating", "learner", "updated_at")
    list_filter = ("rating",)
    search_fields = ("chapter_slug", "body")
    readonly_fields = ("updated_at",)


@admin.register(HandbookLabProgress)
class HandbookLabProgressAdmin(admin.ModelAdmin):
    list_display = ("lab_slug", "learner", "completed_at")
    search_fields = ("lab_slug",)


@admin.register(HandbookSearchLog)
class HandbookSearchLogAdmin(admin.ModelAdmin):
    list_display = ("query", "count", "hits", "last_seen")
    search_fields = ("query",)
    readonly_fields = ("query", "hits", "count", "first_seen", "last_seen")
