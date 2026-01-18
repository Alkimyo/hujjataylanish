from django.conf import settings
from django.core.mail import send_mail
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Send a test email using текущий SMTP sozlamalari."

    def add_arguments(self, parser):
        parser.add_argument("to_email", type=str, help="Qabul qiluvchi email manzili")

    def handle(self, *args, **options):
        to_email = options["to_email"]
        if not settings.EMAIL_HOST_USER or not settings.EMAIL_HOST_PASSWORD:
            raise CommandError("EMAIL_HOST_USER yoki EMAIL_HOST_PASSWORD sozlanmagan.")

        subject = "UniDoc test email"
        message = "Bu UniDoc SMTP sozlamalarini tekshirish uchun test xabari."
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL or settings.EMAIL_HOST_USER,
            recipient_list=[to_email],
            fail_silently=False,
        )
        self.stdout.write(self.style.SUCCESS(f"Test email yuborildi: {to_email}"))
