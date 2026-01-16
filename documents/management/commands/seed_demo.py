from django.core.management.base import BaseCommand

from documents.seed import seed_demo_data


class Command(BaseCommand):
    help = "Seed demo data: universities, faculties, departments, programs, groups, users"

    def handle(self, *args, **options):
        seed_demo_data()
        self.stdout.write(self.style.SUCCESS("Demo data created or updated."))
