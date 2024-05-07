from django.apps import AppConfig


class HeadquartersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'headquarters'
    verbose_name = 'Штабы'

    def ready(self):
        import headquarters.signal_handlers
