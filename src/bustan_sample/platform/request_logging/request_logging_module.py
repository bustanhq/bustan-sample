from bustan import APP_INTERCEPTOR, ClassProvider, Module

from .request_logging_interceptor import RequestLoggingInterceptor


# APP_INTERCEPTOR applies the interceptor to all routes of the application.
# Import this module once, in the root module.
@Module(
    providers=[ClassProvider(provide=APP_INTERCEPTOR, use_class=RequestLoggingInterceptor)],
)
class RequestLoggingModule:
    pass
