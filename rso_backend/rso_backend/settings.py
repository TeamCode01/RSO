import os
from datetime import timedelta
from pathlib import Path

import boto3
from celery.schedules import crontab
from dotenv import load_dotenv
from pythonjsonlogger import jsonlogger


load_dotenv()

SHOW_RESERVED_PLACE = False

DEFAULT_POSITION_ID = 1
CENTRAL_HQ_ID = 1

# Redis cache TTL
DETANCHMENT_LIST_CACHE_TTL = 120
SUB_COMMANDER_LIST_TTL = 120
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
USER_ME_TTL = 20


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
PRODUCTION = os.getenv('DEBUG', default=False) == 'True'

TEST_EMAIL_ADDRESSES = os.getenv('TEST_EMAIL_ADDRESSES', default='').split(',')

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
    'rest_framework_simplejwt',
    'log_viewer',
    'dbbackup',
]

INSTALLED_APPS += [
    'api.apps.ApiConfig',
    'users.apps.UsersConfig',
    'headquarters.apps.HeadquartersConfig',
    'events.apps.EventsConfig',
    'competitions.apps.CompetitionsConfig',
    'questions.apps.QuestionsConfig',
    'regional_competitions.apps.RegionalCompetitionsConfig',
    'services.apps.ServicesConfig',
    'regional_competitions_2025.apps.RegionalCompetitions2025Config',
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
if not DEBUG:
    MIDDLEWARE += ['requestlogs.middleware.RequestLogsMiddleware',]

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

# S3 settings
DB_ACCESS_KEY_ID = os.getenv('DB_ACCESS_KEY_ID')
DB_SECRET_ACCESS_KEY = os.getenv('DB_SECRET_ACCESS_KEY')
DATABASE_BUCKET_NAME = os.getenv('DATABASE_BUCKET_NAME')
AWS_S3_ENDPOINT_URL = os.getenv('AWS_S3_ENDPOINT_URL')
AWS_DEFAULT_ACL = None  # права доступа тянуть с s3
AWS_S3_OBJECT_PARAMETERS = {'CacheControl': 'max-age=86400'}
USE_S3 = int(os.getenv('USE_S3', '0'))
AWS_QUERYSTRING_AUTH = False  # отключаем авторизацию через параметры url

if USE_S3:
    # создание бэкапа python manage.py dbbackup (вынесено в таску)
    # восстановление бд из последнего бэкапа python manage.py dbrestore
    DBBACKUP_STORAGE = 'rso_backend.s3_storage.DataBaseStorage'
    DBBACKUP_STORAGE_OPTIONS = {
        'access_key': DB_ACCESS_KEY_ID,
        'secret_key': DB_SECRET_ACCESS_KEY,
        'bucket_name': DATABASE_BUCKET_NAME,
        'default_acl': 'private',
    }
else:
    DBBACKUP_STORAGE = 'django.core.files.storage.FileSystemStorage'
    DBBACKUP_STORAGE_OPTIONS = {
        'location': Path(BASE_DIR).joinpath('backup').resolve()
    }


STATIC_URL = 'static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'collected_static')

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')


DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOGS_PATH = os.path.join(BASE_DIR, 'logs')
os.makedirs(LOGS_PATH, exist_ok=True)

LOGS_FILENAME = os.path.join(LOGS_PATH, 'backend.log')
LOG_MAX_BYTES = 20 * 1024 * 1024  # 20 MB
LOGS_BACKUP_COUNT = 10

LOGGING = {
    'version': 1,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'filters': {
        'require_debug_true': {
            '()': 'django.utils.log.RequireDebugTrue',
        }
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'debug_console': {
            'level': 'DEBUG',
            'filters': ['require_debug_true'],
            'class': 'logging.StreamHandler',
        },
        'tasks': {
            'level': 'DEBUG',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': 'logs/tasks_logs.log',
            'maxBytes': 20 * 1024 * 1024,
            'backupCount': 15,
            'formatter': 'verbose',
            'encoding': 'UTF-8',
        },
        'regional_tasks': {
            'level': 'DEBUG',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': 'logs/regional_tasks_logs.log',
            'maxBytes': 20 * 1024 * 1024,
            'backupCount': 15,
            'formatter': 'verbose',
            'encoding': 'UTF-8',
        },
        'django': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': LOGS_FILENAME,
            'maxBytes': LOG_MAX_BYTES,
            'backupCount': LOGS_BACKUP_COUNT,
            'level': 'INFO',
            'formatter': 'verbose',
            'encoding': 'UTF-8',
        },
        'requestlogs_to_file': {
            'level': 'DEBUG',
            'class': 'logging.handlers.TimedRotatingFileHandler',
            'filename': 'logs/request_logs.log',
            'when': 'midnight',
            'backupCount': 90,
            'encoding': 'UTF-8',
        },
    },

    'loggers': {
        'tasks': {
            'handlers': ['console', 'tasks'],
            'level': 'DEBUG',
        },
        'regional_tasks': {
            'handlers': ['console', 'regional_tasks'],
            'level': 'DEBUG',
        },
        'django': {
            'handlers': ['console', 'django'],
            'level': 'INFO',
            'propagate': True,
        },
        'requestlogs': {
            'handlers': ['requestlogs_to_file'],
            'level': 'DEBUG',
            'propagate': False,
        },
        # 'django.db.backends': {
        #     'level': 'DEBUG',
        #     'handlers': ['debug_console'],
        # }
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


if DEBUG:
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
        'delete_temp_reports': {
            'task': 'reports.tasks.delete_temp_reports_task',
            'schedule': timedelta(hours=12)
        },
        'delete_front_logs': {
            'task': 'services.tasks.delete_front_logs',
            'schedule': crontab(
                hour=0,
                minute=0,
                day_of_week='sunday'
            )
        },
    }
else:
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
        'delete_front_logs': {
            'task': 'services.tasks.delete_front_logs',
            'schedule': crontab(
                hour=0,
                minute=0,
                day_of_week='sunday'
            )
        },
        'delete_temp_reports': {
            'task': 'reports.tasks.delete_temp_reports_task',
            'schedule': crontab(hour=3, minute=0)
        },
        'run-dbbackup-every-24-hours': {
            'task': 'rso_backend.celery.run_dbbackup_task',
            'schedule': crontab(hour=4, minute=25),
        }
    }

if DEBUG:
    CELERY_BEAT_SCHEDULE['debug_periodic_task'] = {
        'task': 'users.tasks.debug_periodic_task',
        'schedule': timedelta(seconds=90),
    }
CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers.DatabaseScheduler'

# FOR LINUX:
# celery -A rso_backend worker --loglevel=info
# celery -A rso_backend beat -l info

# FOR WINDOWS:
# celery -A rso_backend worker --loglevel=info -P eventlet

if DEBUG and not PRODUCTION:
    CORS_ALLOW_ALL_ORIGINS = True

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
    'http://213.139.208.147:30000',
    'http://213.139.208.147:3000',
    'http://xn--j1ab.xn--d1amqcgedd.xn--p1ai',
    'https://xn--j1ab.xn--d1amqcgedd.xn--p1ai',
]

CSRF_TRUSTED_ORIGINS = [
    'http://localhost:3000',
    'http://localhost:8080',
    'http://localhost:80',
    'http://127.0.0.1:8080',
    'http://localhost',
    'https://127.0.0.1',
    'https://rso.sprint.1t.ru',
    'https://лк.трудкрут.рф',
    'http://xn--j1ab.xn--d1amqcgedd.xn--p1ai',
    'https://xn--j1ab.xn--d1amqcgedd.xn--p1ai',
    'http://213.139.208.147',
    'http://213.139.208.147:30000',
    'http://213.139.208.147:3000',
    'https://213.139.208.147',
]

REST_FRAMEWORK = {
    'DEFAULT_THROTTLE_CLASSES': [
        'api.throttling.AnonRateThrottleCustom',
        'api.throttling.UserRateThrottleCustom',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '65/min',
        'user': '6000/min'
    },
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.TokenAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticatedOrReadOnly',
    ],
    'DEFAULT_PAGINATION_CLASS': 'api.utils.Limit250OffsetPagination',
    'EXCEPTION_HANDLER': 'requestlogs.views.exception_handler',
    'NUM_PROXIES': 1,
}

# For VK ID
VK_API_VERSION = '5.199'
VITE_SERVICE_TOKEN = os.getenv('VITE_SERVICE_TOKEN')


AUTHENTICATION_BACKENDS = [
    'api.backends.UserModelBackend',
]

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

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=300),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": False,
    "BLACKLIST_AFTER_ROTATION": False,
    "UPDATE_LAST_LOGIN": True,

    "ALGORITHM": "HS256",
    "SIGNING_KEY": SECRET_KEY,
    "VERIFYING_KEY": "",
    "AUDIENCE": None,
    "ISSUER": None,
    "JSON_ENCODER": None,
    "JWK_URL": None,
    "LEEWAY": 0,

    "AUTH_HEADER_TYPES": ("JWT",),
    "AUTH_HEADER_NAME": "HTTP_AUTHORIZATION",
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
    "USER_AUTHENTICATION_RULE": "rest_framework_simplejwt.authentication.default_user_authentication_rule",

    "AUTH_TOKEN_CLASSES": ("rest_framework_simplejwt.tokens.AccessToken",),
    "TOKEN_TYPE_CLAIM": "token_type",
    "TOKEN_USER_CLASS": "rest_framework_simplejwt.models.TokenUser",

    "JTI_CLAIM": "jti",

    "SLIDING_TOKEN_REFRESH_EXP_CLAIM": "refresh_exp",
    "SLIDING_TOKEN_LIFETIME": timedelta(minutes=5),
    "SLIDING_TOKEN_REFRESH_LIFETIME": timedelta(days=1),

    "TOKEN_OBTAIN_SERIALIZER": "rest_framework_simplejwt.serializers.TokenObtainPairSerializer",
    "TOKEN_REFRESH_SERIALIZER": "rest_framework_simplejwt.serializers.TokenRefreshSerializer",
    "TOKEN_VERIFY_SERIALIZER": "rest_framework_simplejwt.serializers.TokenVerifySerializer",
    "TOKEN_BLACKLIST_SERIALIZER": "rest_framework_simplejwt.serializers.TokenBlacklistSerializer",
    "SLIDING_TOKEN_OBTAIN_SERIALIZER": "rest_framework_simplejwt.serializers.TokenObtainSlidingSerializer",
    "SLIDING_TOKEN_REFRESH_SERIALIZER": "rest_framework_simplejwt.serializers.TokenRefreshSlidingSerializer",
}

SWAGGER_SETTINGS = {
    'SECURITY_DEFINITIONS': {
        'Bearer': {
            'type': 'apiKey',
            'name': 'Authorization',
            'in': 'header'
        }
    },
    'DOC_EXPANSION': 'none',

}

REQUESTLOGS = {
    'STORAGE_CLASS': 'requestlogs.storages.LoggingStorage',
    'ENTRY_CLASS': 'api.log_entries.CustomRequestLogEntry',
    'SERIALIZER_CLASS': 'requestlogs.storages.BaseEntrySerializer',
    'SECRETS': ['password', 'token', 'HTTP_COOKIE', 'HTTP_X_CSRFTOKEN'],
    'ATTRIBUTE_NAME': '_requestlog',
    'METHODS': ('GET', 'PUT', 'PATCH', 'POST', 'DELETE'),
    'JSON_ENSURE_ASCII': True,
    'IGNORE_USER_FIELD': None,
    'IGNORE_USERS': [],
    'IGNORE_PATHS': None,
}

LOG_VIEWER_FILES_PATTERN = '*'
LOG_VIEWER_FILES_DIR = LOGS_PATH
LOG_VIEWER_PAGE_LENGTH = 75
LOG_VIEWER_MAX_READ_LINES = 12000
LOG_VIEWER_FILE_LIST_MAX_ITEMS_PER_PAGE = 25
LOG_VIEWER_PATTERNS = ['INFO', 'DEBUG', 'WARNING', 'ERROR', 'CRITICAL', "{'action_name':"]
LOG_VIEWER_EXCLUDE_TEXT_PATTERN = None

DATA_UPLOAD_MAX_NUMBER_FIELDS = None
