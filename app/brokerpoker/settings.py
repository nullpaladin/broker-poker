from app import paths

SECRET_KEY = paths.django_secret_key()
DEBUG = False
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "testserver"]
ROOT_URLCONF = "app.brokerpoker.urls"
WSGI_APPLICATION = "app.brokerpoker.wsgi.application"
INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.staticfiles",
    "rest_framework",
    "app.profiles",
    "app.runs",
    "app.submissions",
]
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]
TEMPLATES = [{
    "BACKEND": "django.template.backends.django.DjangoTemplates",
    "DIRS": [paths.REPO_ROOT / "app" / "templates"],
    "APP_DIRS": False,
    "OPTIONS": {"context_processors": ["django.template.context_processors.request"]},
}]
DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": paths.data_dir() / "db.sqlite3"}}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
STATIC_URL = "/static/"
STATICFILES_DIRS = [paths.REPO_ROOT / "app" / "static"]
USE_TZ = True
TIME_ZONE = "UTC"
REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_PARSER_CLASSES": ["rest_framework.parsers.JSONParser"],
    "DEFAULT_AUTHENTICATION_CLASSES": [],
    "DEFAULT_PERMISSION_CLASSES": [],
    "UNAUTHENTICATED_USER": None,
}
SESSION_COOKIE_HTTPONLY = True
X_FRAME_OPTIONS = "DENY"
