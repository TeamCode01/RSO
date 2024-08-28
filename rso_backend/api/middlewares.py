from copy import deepcopy
from requestlogs.middleware import RequestLogsMiddleware as BaseRequestLogsMiddleware, get_requestlog_entry, SETTINGS
from io import BufferedReader, BufferedRandom


class CustomRequestLogsMiddleware(BaseRequestLogsMiddleware):
    def __call__(self, request):
        response = self.get_response(request)

        if request.method.upper() in tuple(m.upper() for m in SETTINGS['METHODS']):
            try:
                self.clean_request_data(request)
                get_requestlog_entry(request).finalize(response)
            except Exception as e:
                print(f"Error during request log finalization: {e}")
                pass

        return response

    def clean_request_data(self, request):
        """
        Этот метод удаляет несериализуемые объекты (например, файлы и потоки) из данных запроса.
        """
        try:
            if hasattr(request, 'data'):
                request.data = self._clean_data(request.data)
        except Exception as e:
            print(f"Error cleaning request data: {e}")
            pass

    def _clean_data(self, data):
        """
        Рекурсивно очищаем данные от объектов, которые не могут быть сериализованы.
        """
        try:
            if isinstance(data, dict):
                cleaned_data = {}
                for key, value in data.items():
                    try:
                        cleaned_data[key] = deepcopy(value)
                    except (TypeError, ValueError):
                        print(f"Skipping non-serializable object in key '{key}'")
                        cleaned_data[key] = None
                return cleaned_data

            elif isinstance(data, list):
                cleaned_list = []
                for index, item in enumerate(data):
                    try:
                        cleaned_list.append(deepcopy(item))
                    except (TypeError, ValueError):
                        print(f"Skipping non-serializable object in list at index {index}")
                        cleaned_list.append(None)
                return cleaned_list

            return data
        except Exception as e:
            print(f"Error during data cleaning: {e}")
            return None
