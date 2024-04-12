from django.db.models import Q
from django_filters import rest_framework as filters

from events.models import Event


class EventFilter(filters.FilterSet):
    scale_or_direction = filters.CharFilter(
        method='filter_scale_or_direction', label='Масштаб или направление'
    )
    format_type = filters.CharFilter(
        field_name='format', lookup_expr='icontains', label='Формат'
    )
    direction = filters.CharFilter(
        field_name='direction', lookup_expr='icontains', label='Направление'
    )
    status = filters.CharFilter(
        field_name='status', lookup_expr='icontains', label='Статус'
    )
    scale = filters.CharFilter(
        field_name='scale',
        lookup_expr='icontains',
        label='Масштаб мероприятия'
    )
    active_organizer_user_id = filters.CharFilter(
        field_name = 'author',
        label='Мероприятия, где пользователь организатор'
    )

    class Meta:
        model = Event
        fields = ('format_type', 'direction', 'status', 'scale', 'active_organizer_user_id')

    def filter_scale_or_direction(self, queryset, name, value):
        print(value)
        filter_values = value.split('|')
        print(filter_values)
        q_objects = Q()

        for filter_value in filter_values:
            if '=' in filter_value:
                key, val = filter_value.split('=')
                if key == 'scale' and val:
                    print(val)
                    q_objects |= Q(scale__icontains=val)
                elif key == 'direction' and val:
                    print(val)
                    q_objects |= Q(direction__icontains=val)

        return queryset.filter(q_objects)
    
    def filter_organizer_or_not_closed_accepting_application(self, queryset, name, value):
        print(value)
        filter_values = value.split('|')
        print(filter_values)
        q_objects = Q()

        for filter_value in filter_values:
            if '=' in filter_value:
                key, val = filter_value.split('=')
                if key == 'active_organizer_user_id' and val:
                    print(val)
                    q_objects |= Q(active_organizer_user_id=val)
                    
        return queryset.filter(q_objects)