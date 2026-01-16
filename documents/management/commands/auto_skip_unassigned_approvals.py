from django.core.management.base import BaseCommand
from django.db.models import F

from documents import models
from documents.services import ApprovalWorkflowService


class Command(BaseCommand):
    help = "Auto-skip unassigned approval steps for pending documents."

    def handle(self, *args, **options):
        pending_steps = models.ApprovalStep.objects.filter(
            status='pending',
            approver__isnull=True,
            document__status='pending_approval',
            step_order=F('document__current_step'),
        ).select_related('document')

        documents = {step.document for step in pending_steps}
        updated = 0

        for document in documents:
            if ApprovalWorkflowService._skip_unassigned_steps(document):
                updated += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Processed {len(documents)} document(s), updated {updated}."
            )
        )
