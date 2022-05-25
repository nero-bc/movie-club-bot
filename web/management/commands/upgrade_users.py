from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from django.contrib.auth.models import Permission


class Command(BaseCommand):
    help = "Update existing user permissions"

    def handle(self, *args, **options):
        for user in User.objects.all():
            for permission in ('view', 'add', 'change'):
                for table in ('movie suggestion', 'buff', 'critic rating'):
                    user.user_permissions.add(Permission.objects.get(name=f"Can {permission} {table}"))

            user.save()
