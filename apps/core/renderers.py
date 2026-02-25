from rest_framework.renderers import JSONRenderer


class CustomJSONRenderer(JSONRenderer):
    """Wraps all API responses in a standard envelope."""

    def render(self, data, accepted_media_type=None, renderer_context=None):
        response = renderer_context.get("response") if renderer_context else None

        if response and response.status_code >= 400:
            # Error responses are already formatted by exception handler
            return super().render(data, accepted_media_type, renderer_context)

        wrapped = {
            "success": True,
            "status_code": response.status_code if response else 200,
            "data": data,
        }
        return super().render(wrapped, accepted_media_type, renderer_context)
