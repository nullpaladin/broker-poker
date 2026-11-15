from django.urls import path

from app import views
from app.runs import api

urlpatterns = [
    path("", views.welcome, name="welcome"),
    path("setup/<str:key>/", views.step, name="step"),
    path("summary/", views.summary, name="summary"),
    path("runs/<int:run_id>/", views.run_page, name="run"),
    path("runs/<int:run_id>/done/", views.done, name="done"),
    path("runs/<int:run_id>/shot/<str:slug>/<path:name>", views.screenshot, name="shot"),
    path("runs/<int:run_id>/reminders.ics", views.reminders, name="reminders"),
    path("export/", views.export_profile, name="export"),
    path("import/", views.import_profile, name="import"),
    path("import-env/", views.import_env, name="import_env"),
    path("history/", views.history, name="history"),
    path("api/runs/<int:run_id>/status/", api.RunStatus.as_view()),
    path("api/runs/<int:run_id>/captcha/<int:captcha_id>/answer/", api.CaptchaAnswer.as_view()),
    path("api/runs/<int:run_id>/cancel/", api.CancelRun.as_view()),
]
