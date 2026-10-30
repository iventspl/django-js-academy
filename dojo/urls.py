from django.urls import path

from . import views

app_name = "dojo"

urlpatterns = [
    path("", views.home, name="home"),
    path("search/", views.search, name="search"),
    path("quiz/", views.quiz_setup, name="quiz_setup"),
    path("quiz/<int:attempt_id>/", views.quiz_question, name="quiz_question"),
    path("quiz/<int:attempt_id>/results/", views.quiz_results, name="quiz_results"),
    path(
        "quiz/<int:attempt_id>/retry/",
        views.retry_missed,
        name="retry_missed",
    ),
    path("quiz/weak-spots/", views.weak_spots_practice, name="weak_spots"),
    path("flashcards/", views.flashcards_index, name="flashcards"),
    path("flashcards/review/", views.flashcards_review_all, name="flashcards_review_all"),
    path(
        "flashcards/review/rate/<int:card_id>/",
        views.flashcards_rate,
        name="flashcards_rate_all",
    ),
    path("flashcards/<slug:topic_slug>/", views.flashcards_study, name="flashcards_study"),
    path(
        "flashcards/<slug:topic_slug>/rate/<int:card_id>/",
        views.flashcards_rate,
        name="flashcards_rate",
    ),
    path("field-guide/", views.field_guide, name="field_guide"),
    path("architecture/", views.architecture_studio, name="architecture_studio"),
    path(
        "architecture/<slug:key>/",
        views.architecture_case,
        name="architecture_case",
    ),
    path("field-guide/cheatsheets/", views.cheatsheets, name="cheatsheets"),
    path("field-guide/blueprints/", views.blueprints, name="blueprints"),
    path(
        "field-guide/blueprints/<slug:key>/",
        views.blueprint_detail,
        name="blueprint_detail",
    ),
    path("field-guide/releases/", views.release_radar, name="release_radar"),
    path("progress/", views.progress, name="progress"),
    path("progress/export/", views.progress_export, name="progress_export"),
    path("notes/", views.notes, name="notes"),
    path("notes/<int:note_id>/delete/", views.delete_note, name="delete_note"),
    path("progress/reset/", views.progress_reset, name="progress_reset"),
]
