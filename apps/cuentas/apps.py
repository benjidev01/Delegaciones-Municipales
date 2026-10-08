from django.apps import AppConfig

class CuentasConfig(AppConfig):
    name = 'apps.cuentas'

    def ready(self):
        from . import signals  # noqa: F401
