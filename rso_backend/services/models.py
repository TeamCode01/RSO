from django.db import models


class FrontError(models.Model):
    user = models.ForeignKey(
        to='users.RSOUser',
        on_delete=models.SET_NULL,
        verbose_name='Пользователь',
        related_name='front_errors',
        null=True,
        blank=True
    )
    error_code = models.IntegerField(
        verbose_name='Код ошибки',
    )
    error_description = models.CharField(
        max_length=100,
        verbose_name='Описание ошибки',
        default='',
    )
    url = models.URLField(
        verbose_name='Ссылка, на которой возникла ошибка',
    )
    method = models.CharField(
        max_length=10,
        verbose_name='HTTP метод',
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Время записи ошибки',
    )

    class Meta:
        verbose_name_plural = 'Логи ошибок с фронтенда'
        verbose_name = 'Лог ошибки с фронтенда'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.method} {self.url} - ошибка "{self.error_description}"'


class Blocklist(models.Model):
    ip_addr = models.GenericIPAddressField(
        db_index=True,
        unique=True,
        verbose_name='IP'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Время блокировки'
    )

    class Meta:
        verbose_name = 'Заблокированный IP'
        verbose_name_plural = 'Заблокированные IP'

    def __str__(self):
        return self.ip_addr
