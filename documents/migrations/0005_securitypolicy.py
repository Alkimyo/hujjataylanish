from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("documents", "0004_requestlog"),
    ]

    operations = [
        migrations.CreateModel(
            name="SecurityPolicy",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("rate_limit_per_minute", models.IntegerField(default=30)),
                ("burst", models.IntegerField(default=15)),
                ("findtime_seconds", models.IntegerField(default=120)),
                ("maxretry", models.IntegerField(default=3)),
                ("bantime_seconds", models.IntegerField(default=-1)),
                ("whitelist", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "db_table": "security_policies",
                "verbose_name": "Security Policy",
                "verbose_name_plural": "Security Policies",
            },
        ),
    ]
