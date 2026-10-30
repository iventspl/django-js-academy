from django.urls import path

from . import views

app_name = "js_academy"

urlpatterns = [
    path("", views.home, name="home"),
    path("sciezka/", views.path, name="path"),
    path("projekty/", views.projects, name="projects"),
    path("projekty/<slug:slug>/", views.project_detail, name="project"),
    path("projekty/<slug:slug>/<slug:step_slug>/ukoncz/", views.project_step_complete, name="project_step_complete"),
    path("wyzwania/", views.challenges, name="challenges"),
    path("piaskownica/", views.playground, name="playground"),
    path("szukaj/", views.search, name="search"),
    path("mvc/", views.mvc_guide, name="mvc_guide"),
    path("komponenty/", views.components, name="components"),
    path("komponenty/<slug:slug>/", views.component_detail, name="component"),
    path("wyzwania/<slug:slug>/", views.challenge_detail, name="challenge"),
    path(
        "wyzwania/<slug:slug>/ukoncz/",
        views.challenge_complete,
        name="challenge_complete",
    ),
    path("wiedza/", views.knowledge, name="knowledge"),
    path("wiedza/ciekawostki/", views.facts, name="facts"),
    path("wiedza/slownik/", views.glossary, name="glossary"),
    path("wiedza/wywiad/", views.interview, name="interview"),
    path("wiedza/ai-praca/", views.ai_career, name="ai_career"),
    path("fiszki/", views.flashcards_index, name="flashcards_index"),
    path("fiszki/powtorka/", views.flashcards_review, name="flashcards_review"),
    path(
        "fiszki/powtorka/ocena/<int:card_id>/",
        views.flashcards_rate,
        name="flashcards_rate_all",
    ),
    path("fiszki/<slug:module_slug>/", views.flashcards_study, name="flashcards"),
    path(
        "fiszki/<slug:module_slug>/ocena/<int:card_id>/",
        views.flashcards_rate,
        name="flashcards_rate",
    ),
    path("quiz/<int:attempt_id>/", views.quiz, name="quiz"),
    path("quiz/<int:attempt_id>/wynik/", views.quiz_results, name="quiz_results"),
    path("quiz/<int:attempt_id>/powtorka/", views.retry_missed, name="retry_missed"),
    path("quiz/slabe-punkty/", views.weak_spots_practice, name="weak_spots"),
    path("postepy/", views.progress, name="progress"),
    path("notatki/", views.notes, name="notes"),
    path("postepy/eksport/", views.progress_export, name="progress_export"),
    path("postepy/reset/", views.progress_reset, name="progress_reset"),
    path("<slug:module_slug>/quiz/start/", views.quiz_start, name="quiz_start"),
    path("<slug:module_slug>/", views.module_detail, name="module"),
    path("<slug:module_slug>/<slug:lesson_slug>/", views.lesson_detail, name="lesson"),
    path("<slug:module_slug>/<slug:lesson_slug>/notatka/", views.save_note, name="save_note"),
    path(
        "<slug:module_slug>/<slug:lesson_slug>/ukoncz/",
        views.complete_lesson,
        name="complete_lesson",
    ),
]
