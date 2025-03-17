from rest_framework.throttling import AnonRateThrottle, UserRateThrottle

from services.models import Blocklist


def block_ip(ip):
    if not Blocklist.objects.filter(ip_addr=ip).exists():
        Blocklist.objects.create(ip_addr=ip)


class AnonRateThrottleCustom(AnonRateThrottle):

    def allow_request(self, request, view):
        if self.rate is None:
            return True

        self.key = self.get_cache_key(request, view)
        if self.key is None:
            return True

        self.history = self.cache.get(self.key, [])
        self.now = self.timer()

        while self.history and self.history[-1] <= self.now - self.duration:
            self.history.pop()
        if len(self.history) >= self.num_requests:
            return self.throttle_failure(request)
        return self.throttle_success(request)

    def throttle_failure(self, request):
        # Внесение ip в блоклист в случае превышения лимита запросов
        ip = self.get_ident(request)
        block_ip(ip)
        return False

    def throttle_success(self, request):
        # Проверка на блокировку ip и обновление счетчика запросов в кэше
        ip = self.get_ident(request)
        if Blocklist.objects.filter(ip_addr=ip).exists():
            return False
        self.history.insert(0, self.now)
        self.cache.set(self.key, self.history, self.duration)
        print(f'anon ip: {ip}')
        return True


class UserRateThrottleCustom(UserRateThrottle):

    def allow_request(self, request, view):
        if self.rate is None:
            return True

        self.key = self.get_cache_key(request, view)
        if self.key is None:
            return True

        self.history = self.cache.get(self.key, [])
        self.now = self.timer()

        while self.history and self.history[-1] <= self.now - self.duration:
            self.history.pop()
        if len(self.history) >= self.num_requests:
            return self.throttle_failure(request)
        return self.throttle_success(request)

    def throttle_failure(self, request):
        ip = self.get_ident(request)
        block_ip(ip)
        return False

    def throttle_success(self, request):
        ip = self.get_ident(request)
        if Blocklist.objects.filter(ip_addr=ip).exists():
            return False
        self.history.insert(0, self.now)
        self.cache.set(self.key, self.history, self.duration)
        return True
