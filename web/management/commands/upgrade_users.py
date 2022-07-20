from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.contrib.auth.models import Permission
import re
import web.models


class Command(BaseCommand):
    help = "Update existing user permissions"

    def handle(self, *args, **options):
        tables = [x for x in dir(web.models) if x[0] == x[0].upper() and x[0] != '_' and x != 'User']
        fixed = [re.sub(r'([A-Z])', r' \1', x[0].lower() + x[1:]).lower() for x in tables]

        for user in User.objects.all():
            for permission in ('view', 'add', 'change'):
                for table in fixed:
                    user.user_permissions.add(Permission.objects.get(name=f"Can {permission} {table}"))

            user.save()
