from django.apps import AppConfig


class ColumbusConfig(AppConfig):
    name = "pyedf"
    verbose_name = "Columbus Workflow Engine"

    def ready(self):
        pass
