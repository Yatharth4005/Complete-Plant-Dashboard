# portal/middleware.py
from django.utils.deprecation import MiddlewareMixin

class StaticCacheMiddleware(MiddlewareMixin):
    """
    Middleware to inject aggressive caching headers for static files in development/production,
    improving mobile app WebView page transition speed by preventing redundant downloads.
    """
    def process_response(self, request, response):
        if request.path.startswith('/static/'):
            # Tell browsers and mobile WebViews to cache static assets for 1 year
            response['Cache-Control'] = 'public, max-age=31536000, immutable'
        return response
