from django.core.management.base import BaseCommand
from django.utils import timezone
from documents.services.approval_workflow import ApprovalWorkflowService

class Command(BaseCommand):
    help = 'Auto-approve and deadline notification system'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--mode',
            type=str,
            choices=['auto_approve', 'deadline_check', 'escalate', 'all'],
            default='all',
            help='Choose which task to run'
        )
    
    def handle(self, *args, **options):
        mode = options['mode']
        now = timezone.now()
        
        self.stdout.write(f"Running approval workflow tasks at {now}")
        
        if mode in ['auto_approve', 'all']:
            self.stdout.write("1. Checking for overdue documents...")
            result = ApprovalWorkflowService.auto_approve_overdue_documents()
            
            if result['approved_steps'] > 0:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"✓ Auto-approved {result['approved_steps']} steps"
                    )
                )
            else:
                self.stdout.write("✓ No overdue documents found")
        
        if mode in ['deadline_check', 'all']:
            self.stdout.write("2. Checking upcoming deadlines...")
            result = ApprovalWorkflowService.check_and_notify_upcoming_deadlines()
            
            if result['notified_24h'] > 0 or result['notified_2h'] > 0:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"✓ Sent notifications: 24h={result['notified_24h']}, "
                        f"2h={result['notified_2h']}"
                    )
                )
            else:
                self.stdout.write("✓ No deadline notifications needed")
        
        if mode in ['escalate', 'all']:
            self.stdout.write("3. Escalating to managers...")
            result = ApprovalWorkflowService.escalate_overdue_documents()
            
            if result.get('escalated_count', 0) > 0:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"✓ Escalated {result['escalated_count']} documents"
                    )
                )
            else:
                self.stdout.write("✓ No documents to escalate")
        
        self.stdout.write(self.style.SUCCESS("All tasks completed successfully!"))