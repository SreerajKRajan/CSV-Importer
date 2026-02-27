"""
Middleware to allow embedding the app in GoHighLevel (app.gohighlevel.com) iframes.
"""


class AllowGHLFrameMiddleware:
    """Set CSP frame-ancestors so the app can be embedded in GHL contact sidebar."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if hasattr(response, "headers"):
            response["Content-Security-Policy"] = "frame-ancestors 'self' https://app.gohighlevel.com"
        return response
