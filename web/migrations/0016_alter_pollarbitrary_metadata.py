# Generated by Django 4.0.4 on 2022-12-07 19:26

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('web', '0015_pollarbitrary'),
    ]

    operations = [
        migrations.AlterField(
            model_name='pollarbitrary',
            name='metadata',
            field=models.TextField(blank=True, null=True),
        ),
    ]
