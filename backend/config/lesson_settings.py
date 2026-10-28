"""Explicit opt-in local exercise server with its own SQLite database."""
import os
from .settings import *  # noqa: F403

INSTALLED_APPS = [*INSTALLED_APPS, 'lessons', 'rest_framework.authtoken']  # noqa: F405
DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': BASE_DIR / 'lessons.sqlite3'}}  # noqa: F405
ROOT_URLCONF = 'lessons.urls'
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': ['rest_framework.authentication.TokenAuthentication'],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated'
        if os.environ.get('KITTYGRAM_LESSON_TOKEN') == '1'
        else 'rest_framework.permissions.AllowAny'
    ],
    'TEST_REQUEST_DEFAULT_FORMAT': 'json',
}
