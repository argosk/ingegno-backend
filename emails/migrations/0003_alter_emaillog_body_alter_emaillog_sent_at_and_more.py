# Generated by Django 4.2 on 2025-04-01 08:06

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('emails', '0002_alter_emailopentracking_unique_together'),
    ]

    operations = [
        migrations.AlterField(
            model_name='emaillog',
            name='body',
            field=models.TextField(blank=True),
        ),
        migrations.AlterField(
            model_name='emaillog',
            name='sent_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='emaillog',
            name='status',
            field=models.CharField(choices=[('sent', 'Sent'), ('pending', 'Pending'), ('opened', 'Opened'), ('clicked', 'Clicked'), ('replied', 'Replied'), ('bounced', 'Bounced')], default='pending', max_length=50),
        ),
    ]
