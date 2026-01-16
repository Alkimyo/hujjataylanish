from django.apps import AppConfig
from django.db.models.signals import post_migrate


class DocumentsConfig(AppConfig):
    name = 'documents'

    def ready(self):
        from documents.seed import seed_demo_data

        def _seed(sender, **kwargs):
            seed_demo_data()

        post_migrate.connect(
            _seed,
            sender=self,
            dispatch_uid="documents.seed_demo_data",
        )
