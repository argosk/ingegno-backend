# Generated by Django 4.2 on 2025-04-04 08:43

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('leads', '0008_alter_lead_status'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='lead',
            name='name',
        ),
        migrations.AddField(
            model_name='lead',
            name='first_name',
            field=models.CharField(blank=True, max_length=50, null=True),
        ),
        migrations.AddField(
            model_name='lead',
            name='last_name',
            field=models.CharField(blank=True, max_length=50, null=True),
        ),
        migrations.AddField(
            model_name='lead',
            name='website',
            field=models.URLField(blank=True, null=True),
        ),
    ]
