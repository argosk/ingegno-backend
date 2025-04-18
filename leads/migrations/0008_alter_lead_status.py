# Generated by Django 4.2 on 2025-04-03 14:39

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('leads', '0007_alter_lead_workflow_status'),
    ]

    operations = [
        migrations.AlterField(
            model_name='lead',
            name='status',
            field=models.CharField(choices=[('new', 'New'), ('contacted', 'Contacted'), ('converted', 'Converted'), ('bounced', 'Bounced')], default='new', max_length=50),
        ),
    ]
