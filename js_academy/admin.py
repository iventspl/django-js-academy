from django.contrib import admin

from .models import (
    JsChallenge,
    JsChallengeCompletion,
    JsComponent,
    JsFact,
    JsInterviewQuestion,
    JsTerm,
    JsAttempt,
    JsAttemptQuestion,
    JsChoice,
    JsFlashcard,
    JsFlashcardReview,
    JsLesson,
    JsLessonProgress,
    JsModule,
    JsQuestion,
)


class JsChoiceInline(admin.TabularInline):
    model = JsChoice
    extra = 0
    fields = ("text", "is_correct", "position")


class JsLessonInline(admin.TabularInline):
    model = JsLesson
    extra = 0
    fields = ("title", "slug", "minutes", "order")
    prepopulated_fields = {"slug": ("title",)}


@admin.register(JsModule)
class JsModuleAdmin(admin.ModelAdmin):
    list_display = ("title", "level", "order", "duration_minutes")
    list_filter = ("level",)
    prepopulated_fields = {"slug": ("title",)}
    inlines = [JsLessonInline]


@admin.register(JsQuestion)
class JsQuestionAdmin(admin.ModelAdmin):
    list_display = ("short_prompt", "module", "difficulty", "position")
    list_filter = ("module", "difficulty")
    search_fields = ("prompt", "explanation", "key")
    inlines = [JsChoiceInline]

    @admin.display(description="Pytanie")
    def short_prompt(self, obj):
        return obj.prompt[:90]


@admin.register(JsFlashcard)
class JsFlashcardAdmin(admin.ModelAdmin):
    list_display = ("front", "module", "position")
    list_filter = ("module",)
    search_fields = ("front", "back", "key")


class JsAttemptQuestionInline(admin.TabularInline):
    model = JsAttemptQuestion
    extra = 0
    can_delete = False
    readonly_fields = ("question", "position", "selected", "is_correct", "answered_at")


@admin.register(JsAttempt)
class JsAttemptAdmin(admin.ModelAdmin):
    list_display = ("id", "module", "learner", "score_percent", "started_at", "completed_at")
    list_filter = ("module", "completed_at")
    inlines = [JsAttemptQuestionInline]


admin.site.register(JsLessonProgress)
admin.site.register(JsFlashcardReview)


@admin.register(JsChallenge)
class JsChallengeAdmin(admin.ModelAdmin):
    list_display = ("title", "difficulty", "module", "xp", "order")
    list_filter = ("difficulty", "module")
    search_fields = ("title", "prompt", "slug")
    prepopulated_fields = {"slug": ("title",)}


@admin.register(JsChallengeCompletion)
class JsChallengeCompletionAdmin(admin.ModelAdmin):
    list_display = ("challenge", "learner", "passed", "completed_at")
    list_filter = ("passed", "completed_at")


@admin.register(JsFact)
class JsFactAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "order")
    list_filter = ("category",)
    search_fields = ("title", "body")


@admin.register(JsTerm)
class JsTermAdmin(admin.ModelAdmin):
    list_display = ("term", "category", "order")
    list_filter = ("category",)
    search_fields = ("term", "definition", "example")


@admin.register(JsInterviewQuestion)
class JsInterviewQuestionAdmin(admin.ModelAdmin):
    list_display = ("question", "category", "difficulty", "order")
    list_filter = ("category", "difficulty")
    search_fields = ("question", "answer")


@admin.register(JsComponent)
class JsComponentAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "difficulty", "order")
    list_filter = ("category", "difficulty")
    search_fields = ("title", "description", "key")
