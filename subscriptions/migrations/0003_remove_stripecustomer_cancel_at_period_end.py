# Generated by Django 4.2 on 2024-06-26 13:04

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('subscriptions', '0002_stripecustomer_cancel_at_period_end_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='stripecustomer',
            name='cancel_at_period_end',
        ),
    ]
