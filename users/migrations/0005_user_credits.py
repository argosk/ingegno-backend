# Generated by Django 4.2 on 2025-01-23 11:04

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0004_remove_user_subscription'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='credits',
            field=models.PositiveIntegerField(default=0),
        ),
    ]
