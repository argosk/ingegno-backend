# Generated by Django 4.2 on 2025-03-12 13:40

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('emails', '0007_alter_emailreplytracking_unique_together'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='emaillog',
            name='response_received',
        ),
    ]
