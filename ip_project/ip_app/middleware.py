import logging, time
from django.http import JsonResponse
from django.core.cache import cache
from django.utils.deprecation import MiddlewareMixin


logger = logging.getLogger('request_logger')
file_handler = logging.FileHandler('requests.log')
logger.setLevel(logging.INFO)
logger.addHandler(file_handler)


class LoggingMiddleware(MiddlewareMixin):
    def process_request(self, request):
        ip = request.META.get('REMOTE_ADDR')
        now = time.strftime('%Y-%m-%d %H:%M:%S')
        logger.info(f'{now} - {ip} - {request.path}')


class RateLimitMiddleware(MiddlewareMixin):
    def process_request(self, request):
        ip = request.META.get('REMOTE_ADDR')
        user = request.user if request.user.is_authenticated else None

        role_limits = {
            'gold': 10,
            'silver': 5,
            'bronze': 2,
            'unauthenticated': 1
        }

        role = user.role if user else 'unauthenticated'
        limit = role_limits.get(role, 1)

        cache_key = f'rate-limit:{ip}'
        req_count = cache.get(cache_key)

        if req_count is None:
            # First request: initialize with 1 and set expiry
            cache.set(cache_key, 1, timeout=60)
        else:
            if req_count >= limit:
                return JsonResponse({'error': f'Rate limit exceeded for {role} user'}, status=429)
            cache.incr(cache_key)
