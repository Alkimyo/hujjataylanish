from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("documents", "0003_jobrun_auditlog"),
    ]

    operations = [
        migrations.CreateModel(
            name="RequestLog",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("method", models.CharField(max_length=10)),
                ("path", models.TextField()),
                ("query_string", models.TextField(blank=True)),
                ("status_code", models.IntegerField()),
                ("ip_address", models.GenericIPAddressField(blank=True, null=True)),
                ("user_agent", models.TextField(blank=True)),
                ("referrer", models.TextField(blank=True)),
                ("duration_ms", models.IntegerField(blank=True, null=True)),
                ("request_body", models.JSONField(blank=True, null=True)),
                ("request_bytes", models.IntegerField(blank=True, null=True)),
                ("response_bytes", models.IntegerField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("user", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to="documents.user")),
            ],
            options={
                "db_table": "request_logs",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="requestlog",
            index=models.Index(fields=["created_at"], name="request_lo_created_7e6d27_idx"),
        ),
        migrations.AddIndex(
            model_name="requestlog",
            index=models.Index(fields=["status_code"], name="request_lo_status__d6f1dd_idx"),
        ),
        migrations.AddIndex(
            model_name="requestlog",
            index=models.Index(fields=["method"], name="request_lo_method_1c97a9_idx"),
        ),
        migrations.AddIndex(
            model_name="requestlog",
            index=models.Index(fields=["path"], name="request_lo_path_c1ad35_idx"),
        ),
    ]
