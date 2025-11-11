import time

from django.utils.deprecation import MiddlewareMixin


class RequestLoggerMiddleware(MiddlewareMixin):
    def process_request(self, request):
        if request.path.startswith("/__debug__/"):
            return
        request.start_time = time.time()
        print(f"Incoming request: {request.method} {request.path}")

    def process_response(self, request, response):
        duration = time.time() - getattr(request, "start_time", time.time())
        print(f"Outgoing response: {response.status_code} | Time : {duration:.2f}s")
        return response
