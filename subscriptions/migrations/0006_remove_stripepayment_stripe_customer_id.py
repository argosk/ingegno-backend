# Generated by Django 4.2 on 2024-06-27 08:22

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('subscriptions', '0005_stripepayment'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='stripepayment',
            name='stripe_customer_id',
        ),
    ]
