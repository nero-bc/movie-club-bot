# Generated by Django 4.0.4 on 2022-12-07 18:56

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('web', '0012_remove_moviesuggestion_expressed_interest_interest'),
    ]

    operations = [
        migrations.RenameField(
            model_name='moviesuggestion',
            old_name='watched',
            new_name='status',
        ),
        migrations.RenameField(
            model_name='moviesuggestion',
            old_name='watched_date',
            new_name='status_changed_date',
        ),
    ]
