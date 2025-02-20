# Generated by Django 4.2 on 2025-02-20 08:07

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('workflows', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='workflow',
            name='definition',
            field=models.JSONField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='workflow',
            name='description',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='workflow',
            name='status',
            field=models.CharField(choices=[('draft', 'Draft'), ('published', 'Published')], default='draft', max_length=50),
        ),
    ]
