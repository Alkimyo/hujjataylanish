from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('documents', '0006_rename_request_lo_created_7e6d27_idx_request_log_created_4f2782_idx_and_more'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='Document',
            new_name='Hujjat',
        ),
    ]
