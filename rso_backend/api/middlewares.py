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
        if hasattr(request, 'data') and isinstance(request.data, dict):
            cleaned_data = {}
            for key, value in request.data.items():
                if isinstance(value, (BufferedReader, BufferedRandom)):
                    continue
                cleaned_data[key] = value

            request.data = cleaned_data
