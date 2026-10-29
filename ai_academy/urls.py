from django.urls import path

from . import views

app_name = "ai_academy"

urlpatterns = [
    path("", views.home, name="home"),
    path("path/", views.path, name="path"),
    path("projects/", views.projects, name="projects"),
    path("projects/<slug:slug>/", views.project_detail, name="project"),
    path(
        "projects/<slug:slug>/test-pack/",
        views.project_test_pack,
        name="project_test_pack",
    ),
    path("projects/<slug:slug>/complete/", views.project_complete, name="project_complete"),
    path("cards/", views.flashcards_index, name="flashcards_index"),
    path("cards/review/", views.flashcards_review, name="flashcards_review"),
    path(
        "cards/review/rate/<int:card_id>/",
        views.flashcards_rate,
        name="flashcards_rate_all",
    ),
    path("cards/<slug:module_slug>/", views.flashcards_study, name="flashcards"),
    path(
        "cards/<slug:module_slug>/rate/<int:card_id>/",
        views.flashcards_rate,
        name="flashcards_rate",
    ),
    path("quiz/<int:attempt_id>/", views.quiz, name="quiz"),
    path("quiz/<int:attempt_id>/result/", views.quiz_results, name="quiz_results"),
    path("progress/", views.progress, name="progress"),
    path("glossary/", views.glossary, name="glossary"),
    path("search/", views.search, name="search"),
    path("career/", views.career, name="career"),
    path("code-library/", views.code_library, name="code_library"),
    path(
        "python-for-ai/cheatsheet/",
        views.python_cheatsheet,
        name="python_cheatsheet",
    ),
    path("<slug:module_slug>/quiz/start/", views.quiz_start, name="quiz_start"),
    path("<slug:module_slug>/", views.module_detail, name="module"),
    path("<slug:module_slug>/<slug:lesson_slug>/", views.lesson_detail, name="lesson"),
    path(
        "<slug:module_slug>/<slug:lesson_slug>/complete/",
        views.complete_lesson,
        name="complete_lesson",
    ),
]
