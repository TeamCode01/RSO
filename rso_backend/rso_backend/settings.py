import os
from datetime import timedelta
from pathlib import Path

from celery.schedules import crontab
from dotenv import load_dotenv
from pythonjsonlogger import jsonlogger

load_dotenv()

# Redis cache TTL
DETACHMENT_LIST_TTL = 120
EDUCATIONALS_LIST_TTL = 120
LOCALS_LIST_TTL = 240
REGIONALS_LIST_TTL = 300
DISTRICTS_LIST_TTL = 300
POSITIONS_LIST_TTL = 60
AREAS_LIST_TTL = 60
REGIONS_LIST_TTL = 300
CENTRAL_OBJECT_CACHE_TTL = 30
DISTR_OBJECT_CACHE_TTL = 30
REG_OBJECT_CACHE_TTL = 30
RSOUSERS_CACHE_TTL = 30
HEADQUARTERS_MEMBERS_CACHE_TTL = 30
DISTRCICTHQ_MEMBERS_CACHE_TTL = 40
CENTRALHQ_MEMBERS_CACHE_TTL = 180
EVENTS_CACHE_TTL = 45
EDU_INST_CACHE_TTL = 180


MIN_FOUNDING_DATE = 1000
MAX_FOUNDING_DATE = 9999
CENTRAL_HEADQUARTER_FOUNDING_DATE = 1959
MASTER_METHODIST_POSITION_NAME = 'Мастер (методист)'
COMMISSIONER_POSITION_NAME = 'Комиссар'
NOT_LEADERSHIP_POSITIONS = ('Боец', 'Кандидат')
DEFAULT_POSITION_NAME = 'Боец'
DATE_JUNIOR_SQUAD = (2024, 1, 25)

BASE_DIR = Path(__file__).resolve().parent.parent


SECRET_KEY = os.getenv('SECRET_KEY', default='key')

DEBUG = os.getenv('DEBUG', default=False) == 'True'

ALLOWED_HOSTS = os.getenv(
    'ALLOWED_HOSTS',
    default='127.0.0.1,localhost,0.0.0.0'
).split(',')

DEFAULT_SITE_URL = os.getenv('DEFAULT_SITE_URL', default='127.0.0.1:8000')

DATABASE = os.getenv('DATABASE', default='sqlite')

# RUN TYPES:

# DOCKER - для запуска проекта через docker compose.
# Коннект к Redis происходит по имени сервиса - redis.

# LOCAL - для локального запуска проекта.
# Коннект к Redis происходит по локальной сети.
RUN_TYPE = os.getenv('RUN_TYPE', default='LOCAL')

AUTH_USER_MODEL = 'users.RSOUser'

# EMAIL BACKEND
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = "smtp.yandex.ru"
EMAIL_PORT = 465
EMAIL_USE_SSL = True

EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD')

EMAIL_SERVER = EMAIL_HOST_USER
DEFAULT_FROM_EMAIL = EMAIL_HOST_USER
EMAIL_ADMIN = EMAIL_HOST_USER

COMPETITION_ID = 1

INSTALLED_APPS = [
    'dal',
    'dal_select2',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'rest_framework.authtoken',
    'drf_yasg',
    'djoser',
    'corsheaders',
    'django_filters',
    'django_celery_beat',
    'import_export',
]

INSTALLED_APPS += [
    'api.apps.ApiConfig',
    'users.apps.UsersConfig',
    'headquarters.apps.HeadquartersConfig',
    'events.apps.EventsConfig',
    'competitions.apps.CompetitionsConfig',
    'questions.apps.QuestionsConfig'
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'rso_backend.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'rso_backend.wsgi.application'

if DATABASE == 'sqlite':
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / '_db.sqlite3',
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.getenv('POSTGRES_DB', 'django'),
            'USER': os.getenv('POSTGRES_USER', 'django'),
            'PASSWORD': os.getenv('POSTGRES_PASSWORD', 'django'),
            'HOST': os.getenv('DB_HOST', 'db'),
            'PORT': os.getenv('DB_PORT', 5432)
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


LANGUAGE_CODE = 'ru-ru'

TIME_ZONE = 'Europe/Moscow'

USE_I18N = True

USE_TZ = True


STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'collected_static'

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')


DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,

    'formatters': {
        'main_formatter': {
            'format': '{asctime} - {name} - {levelname} - {module} - {pathname} - {message}',
            'style': '{',
        },
        'json_formatter': {
            '()': 'pythonjsonlogger.jsonlogger.JsonFormatter',
            'format': '%(asctime)s %(name)s %(levelname)s %(message)s',
            'json_ensure_ascii': False
        },
    },

    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'main_formatter',
        },
        'tasks': {
            'level': 'DEBUG',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': 'logs/tasks_logs.log',
            'maxBytes': 1024 * 1024 * 1024,
            'backupCount': 15,
            'formatter': 'json_formatter',
        },
        'request': {
            'class': 'logging.FileHandler',
            'formatter': 'json_formatter',
            'filename': 'logs/requests_logs.log',
            'encoding': 'UTF-8',
        },
        'server_handler': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': 'logs/server_commands_logs.log',
            'maxBytes': 1024 * 1024 * 1024,
            'backupCount': 15,
            'formatter': 'json_formatter',
        },
        'db': {
            'class': 'logging.FileHandler',
            'formatter': 'json_formatter',
            'filename': 'logs/db_queries_logs.log',
            'encoding': 'UTF-8',
        },
        'security': {
            'class': 'logging.FileHandler',
            'formatter': 'json_formatter',
            'filename': 'logs/security_logs.log',
            'encoding': 'UTF-8',
        },
        'security_csrf': {
            'class': 'logging.FileHandler',
            'formatter': 'json_formatter',
            'filename': 'logs/security_csrf_logs.log',
            'encoding': 'UTF-8',
        }
    },

    'loggers': {
        'tasks': {
            'handlers': ['console', 'tasks'],
            'level': 'DEBUG',
        },
        'django.request': {
            'level': 'INFO',
            'handlers': ['console', 'request']
        },
        'django.server': {
            'level': 'INFO',
            'handlers': ['console', 'server_handler']
        },
        'django.db.backends': {
            'level': 'INFO',
            'handlers': ['console', 'db']
        },
        'django.security.*': {
            'level': 'INFO',
            'handlers': ['console', 'security']
        },
        'django.security.csrf': {
            'level': 'INFO',
            'handlers': ['console', 'security_csrf']
        }
    }
}


REDIS_HOST = '127.0.0.1' if RUN_TYPE != 'DOCKER' else 'redis'

# REDIS CACHE
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': f'redis://{REDIS_HOST}:6379',
        'OPTIONS': {
            'db': '1',
            'parser_class': 'redis.connection.PythonParser',
            'pool_class': 'redis.BlockingConnectionPool',
        }
    },
}

# CELERY-REDIS CONFIG
REDIS_PORT = '6379'
CELERY_TIMEZONE = TIME_ZONE
CELERY_BROKER_URL = f'redis://{REDIS_HOST}:{REDIS_PORT}/0'
CELERY_BROKEN_TRANSPORT_OPTIONS = {'visibility_timeout': 3600}
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True
CELERY_RESULT_BACKEND = f'redis://{REDIS_HOST}:{REDIS_PORT}/0'
CELERY_ACCEPT_CONTENT = ['application/json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'

CELERY_BEAT_SCHEDULE = {
    'reset_membership_fee_task': {
        'task': 'users.tasks.reset_membership_fee',
        'schedule': crontab(
            hour=0,
            minute=0,
            day_of_month=1,
            month_of_year=10,
        )
    },
    'calculate_q1_score': {
        'task': 'competitions.tasks.calculate_q1_score_task',
        'schedule': timedelta(hours=24)
    },
    'calculate_q1': {
        'task': 'competitions.tasks.calculate_q1_places_task',
        'schedule': timedelta(hours=24)
    },
    'calculate_q3_q4': {
        'task': 'competitions.tasks.calculate_q3_q4_places_task',
        'schedule': timedelta(minutes=10)
    },
    'calculate_q5': {
        'task': 'competitions.tasks.calculate_q5_places_task',
        'schedule': timedelta(seconds=25)
    },
    'calculate_q7': {
        'task': 'competitions.tasks.calculate_q7_places_task',
        'schedule': timedelta(hours=24)
    },
    'calculate_q8': {
        'task': 'competitions.tasks.calculate_q7_places_task',
        'schedule': timedelta(hours=24)
    },
    'calculate_q9': {
        'task': 'competitions.tasks.calculate_q9_places_task',
        'schedule': timedelta(hours=24)
    },
    'calculate_q10': {
        'task': 'competitions.tasks.calculate_q10_places_task',
        'schedule': timedelta(hours=24)
    },
    'calculate_q11': {
        'task': 'competitions.tasks.calculate_q11_places_task',
        'schedule': timedelta(hours=24)
    },
    'calculate_q12': {
        'task': 'competitions.tasks.calculate_q12_places_task',
        'schedule': timedelta(hours=24)
    },
    'calculate_q17': {
        'task': 'competitions.tasks.calculate_q17_places_task',
        'schedule': timedelta(hours=24)
    },
    'calculate_q16_score': {
        'task': 'competitions.tasks.calculate_q16_score_task',
        'schedule': timedelta(seconds=24)
    },
    'calculate_q16': {
        'task': 'competitions.tasks.calculate_q16_places_task',
        'schedule': timedelta(seconds=24)
    },
    'calculate_q18': {
        'task': 'competitions.tasks.calculate_q18_places_task',
        'schedule': timedelta(hours=24)
    },
    'calculate_q19': {
        'task': 'competitions.tasks.calculate_q19',
        'schedule': timedelta(hours=30)
    },
    'calculate_q20_': {
        'task': 'competitions.tasks.calculate_q20_places_task',
        'schedule': timedelta(hours=24)
    },
}

if DEBUG:
    CELERY_BEAT_SCHEDULE['debug_periodic_task'] = {
        'task': 'users.tasks.debug_periodic_task',
        'schedule': timedelta(seconds=90),
    }

# FOR LINUX:
# celery -A rso_backend worker --loglevel=info
# celery -A rso_backend beat -l info

# FOR WINDOWS:
# celery -A rso_backend worker --loglevel=info -P eventlet

CORS_ORIGIN_WHITELIST = [
    'http://localhost:3000',
    'http://localhost:8080',
    'http://127.0.0.1:8080',
    'http://localhost:80',
    'http://localhost',
    'https://d2avids.sytes.net',
    'https://rso.sprint.1t.ru',
    'https://лк.трудкрут.рф',
    'http://213.139.208.147',
    'https://213.139.208.147',
    'http://xn--j1ab.xn--d1amqcgedd.xn--p1ai',
    'https://xn--j1ab.xn--d1amqcgedd.xn--p1ai',
]

CSRF_TRUSTED_ORIGINS = [
    'http://localhost:3000',
    'http://localhost:8080',
    'http://localhost:80',
    'http://127.0.0.1:8080',
    'http://localhost'
    'https://127.0.0.1',
    'https://rso.sprint.1t.ru',
    'https://лк.трудкрут.рф',
    'http://xn--j1ab.xn--d1amqcgedd.xn--p1ai',
    'https://xn--j1ab.xn--d1amqcgedd.xn--p1ai',
    'http://213.139.208.147',
    'https://213.139.208.147',
]

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.TokenAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticatedOrReadOnly',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.LimitOffsetPagination',
    'PAGE_SIZE': 100
}

DJOSER = {
    'LOGIN_FIELD': 'username',
    'USERNAME_FIELD': 'username',
    'USER_CREATE_PASSWORD_RETYPE': True,
    'SEND_ACTIVATION_EMAIL': False,
    'PASSWORD_CHANGED_EMAIL_CONFIRMATION': False,
    'PASSWORD_RESET_CONFIRM_RETYPE': False,
    'HIDE_USERS': False,
    'PASSWORD_RESET_CONFIRM_URL': 'password/reset/confirm/{uid}/{token}',
    'SERIALIZERS': {
        'user': 'users.serializers.ShortUserSerializer',
        'current_user': 'users.serializers.RSOUserSerializer',
        'user_create_password_retype': 'users.serializers.UserCreateSerializer',
    },
    'PERMISSIONS': {
        'user_list': ['rest_framework.permissions.IsAuthenticated'],
        'user': ['rest_framework.permissions.IsAuthenticated'],
    }
}

SWAGGER_SETTINGS = {
    'SECURITY_DEFINITIONS': {
        'Bearer': {
            'type': 'apiKey',
            'name': 'Authorization',
            'in': 'header'
        }
    }
}
