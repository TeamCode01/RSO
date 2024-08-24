from typing import Dict

from django.contrib import admin
from django.db import models
from rest_framework import serializers


class RModelFactory:
    def __init__(
            self,
            base_r_model,
            base_link_model,
            r_number: int,
            event_names: Dict[int, str]
    ):
        self.r_number = r_number
        self.base_r_model = base_r_model
        self.base_link_model = base_link_model
        self.event_names = event_names
        self.models = {}

    def create_models(self):
        for r_sub_number, value in self.event_names.items():
            self._create_model(r_sub_number, value[0], value[1])

    def _create_model(self, r_sub_number, event_name, is_labour_project):
        model_name = f'RegionalR{self.r_number}{r_sub_number}'
        link_model_name = f'{model_name}Link'

        self.models[model_name] = type(
            model_name,
            (self.base_r_model,),
            {
                '__module__': __name__,
                'is_labour_project': is_labour_project,
                'Meta': type('Meta', (), {
                    'verbose_name': f'Отчет по {self.r_number} показателю - "{event_name}"',
                    'verbose_name_plural': f'Отчеты по {self.r_number} показателю - "{event_name}"'
                })
            }
        )

        self.models[link_model_name] = type(
            link_model_name,
            (self.base_link_model,),
            {
                '__module__': __name__,
                f'regional_r{self.r_number}{r_sub_number}': models.ForeignKey(
                    to=self.models[model_name],
                    on_delete=models.CASCADE,
                    verbose_name='Отчет',
                    related_name='links'
                ),
                'Meta': type('Meta', (), {
                    'verbose_name': f'Ссылка по {self.r_number} показателю - "{event_name}"',
                    'verbose_name_plural': f'Ссылки по {self.r_number} показателю - "{event_name}"'
                })
            }
        )


class RAdminFactory:
    def __init__(
            self,
            models: dict,
            list_display: tuple,
            list_filter: tuple,
            search_fields: tuple,
            readonly_fields: tuple
    ):
        self.models = models
        self.list_display = list_display
        self.list_filter = list_filter
        self.search_fields = search_fields
        self.readonly_fields = readonly_fields
        self.admin_classes = {}

    def create_admin_classes(self):
        for model_name in self.models:
            if not model_name.endswith('Link'):
                self._create_admin_class(model_name)

    def _create_admin_class(self, model_name):
        link_model_name = f'{model_name}Link'

        link_inline_class = type(
            f'{link_model_name}Inline',
            (admin.TabularInline,),
            {
                'model': self.models[link_model_name],
                'extra': 0,
            }
        )

        admin_class = type(
            f'{model_name}Admin',
            (admin.ModelAdmin,),
            {
                'list_display': self.list_display,
                'search_fields': self.search_fields,
                'list_filter': self.list_filter,
                'readonly_fields': self.readonly_fields,
                'inlines': [link_inline_class],
            }
        )

        admin.site.register(self.models[model_name], admin_class)
        self.admin_classes[model_name] = admin_class
        self.admin_classes[f'{link_model_name}Inline'] = link_inline_class


class RSerializerFactory:
    def __init__(
        self,
        models,
        base_r_serializer,
    ):
        self.models = models
        self.base_r_serializer = base_r_serializer
        self.serializers = {}

    def create_serializer_classes(self):
        for model_name in self.models:
            if not model_name.endswith('Link'):
                self._create_serializer_class(model_name)

    def _create_serializer_class(self, model_name):
        link_model_name = f'{model_name}Link'
        link_serializer_class = type(
            f'{link_model_name}LinkSerializer',
            (serializers.ModelSerializer,),
            {
                'Meta': type('Meta', (), {
                    'model': self.models[link_model_name],
                    'fields': '__all__',
                    'read_only_fields': [
                        field.name for field in self.models[link_model_name]._meta.get_fields() if field.name != 'link'
                    ]
                })
            }
        )

        regional_r_field_name = next(
            field.name for field in self.models[link_model_name]._meta.get_fields()
            if field.name.startswith('regional_r') and field.is_relation
        )

        def create_objects(self, created_objects, link_data):
            link_model = self.Meta.link_model
            return link_model.objects.create(
                **{regional_r_field_name: created_objects, **link_data}
            )

        regional_r_serializer_class = type(
            f'{model_name}Serializer',
            (self.base_r_serializer,),
            {
                'links': link_serializer_class(many=True, allow_null=True, required=False),
                'Meta': type('Meta', (), {
                    'link_model': self.models[link_model_name],
                    'model': self.models[model_name],
                    'fields': self.base_r_serializer.Meta.fields,
                    'read_only_fields': self.base_r_serializer.Meta.read_only_fields
                }),
                'create_objects': create_objects
            }
        )

        self.serializers[model_name] = regional_r_serializer_class


class RViewSetFactory:
    def __init__(
            self,
            models,
            serializers,
            base_r_view_set,
            base_r_me_view_set
    ):
        self.models = models
        self.serializers = serializers
        self.base_r_view_set = base_r_view_set
        self.base_r_me_view_set = base_r_me_view_set
        self.r_view_sets = []
        self.r_me_view_sets = []
        self.view_set_names = []
        self.me_view_set_names = []

    def create_view_sets(self):
        for model_name in self.models:
            if not model_name.endswith('Link'):
                self._create_view_set(model_name)

    def _create_view_set(self, model_name):
        view_set_name = f'{model_name}ViewSet'
        me_view_set_name = f'{model_name}MeViewSet'

        view_set = type(
            view_set_name, (self.base_r_view_set,), {
                'queryset': self.models[model_name].objects.all(),
                'serializer_class': self.serializers[model_name],
            }
        )
        me_view_set = type(
            me_view_set_name, (self.base_r_me_view_set,), {
                'model': self.models[model_name],
                'queryset': self.models[model_name].objects.all(),
                'serializer_class': self.serializers[model_name],
            }
        )
        self.r_view_sets.append(view_set)
        self.r_me_view_sets.append(me_view_set)
        self.view_set_names.append(model_name)
        self.me_view_set_names.append(model_name)


def register_factory_view_sets(router, base_path, view_set_names, view_sets):
    """Универсальная функция для регистрации урлов в роутере. Регистрирует вьюсеты, созданные фабрикой.

    :param router: Экземпляр маршрутизатора (DefaultRouter, MeRouter или др.)
    :param base_path: Первая часть пути (например, 'reports/9')
    :param view_set_names: Список имен моделей без постфикса 'ViewSet'
    :param view_sets: Список ViewSet классов для регистрации
    """
    for model_name, view_set in zip(view_set_names, view_sets):
        base_number = model_name.lower().replace('regionalr', '').replace('viewset', '')
        path = f'{base_path}/{base_number[1:]}'
        router.register(path, view_set, basename=model_name.lower())
