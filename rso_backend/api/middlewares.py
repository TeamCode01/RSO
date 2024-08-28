from requestlogs.middleware import RequestLogsMiddleware as BaseRequestLogsMiddleware, get_requestlog_entry, SETTINGS
from requestlogs.middleware import RequestIdMiddleware as BaseRequestIdMiddleware
from io import BufferedReader, BufferedRandom


class CustomRequestLogsMiddleware(BaseRequestLogsMiddleware):
    def __call__(self, request):
        response = self.get_response(request)

        if request.method.upper() in tuple(m.upper() for m in SETTINGS['METHODS']):
            self.clean_request_data(request)
            get_requestlog_entry(request).finalize(response)

        return response

    def clean_request_data(self, request):
        """
        Этот метод удаляет несериализуемые объекты (например, файлы и потоки) из данных запроса.
        """
        # Проверяем наличие данных запроса и удаляем несериализуемые объекты
        if hasattr(request, 'data') and isinstance(request.data, dict):
            cleaned_data = {}
            for key, value in request.data.items():
                if isinstance(value, (BufferedReader, BufferedRandom)):
                    continue  # Игнорируем файловые потоки
                cleaned_data[key] = value

            # Заменяем оригинальные данные на очищенные
            request.data = cleaned_data
        elif isinstance(request.POST, QueryDict):
            # Если это form-data, также очищаем файлы
            request.POST = request.POST.copy()
            for key in list(request.POST.keys()):
                if isinstance(request.POST[key], (BufferedReader, BufferedRandom)):
                    del request.POST[key]
