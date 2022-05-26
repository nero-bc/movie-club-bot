import sys
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from django.contrib.auth.models import Permission
from web.models import *


cols = ['imdb', 'watched', 'cage', 'rock', 'david', 'jacobjan', 'helena',
        'saskia']


def p(val):
    if val == 'TRUE':
        return True
    elif val == 'FALSE':
        return False
    else:
        return val

cage = Buff.objects.get(short='cage')
rock = Buff.objects.get(short='rock')
# print(cage, rock)

# Testing
# david = User.objects.get(username='195671723')
# jacobjan = User.objects.get(username='admin')
# helena = User.objects.get(username='hxr')
# saskia = User.objects.get(username='saskia')

# Prod
david = User.objects.get(username='5374276216')
jacobjan = User.objects.get(username='824932139')
helena = User.objects.get(username='195671723')
saskia = User.objects.get(username='15244978')



class Command(BaseCommand):
    help = "Import a google sheets table"

    def handle(self, *args, **options):
        for line in sys.stdin.readlines()[1:]:
            unparsed = line.strip().split('\t')
            data = dict(zip(cols, [p(x) for x in unparsed]))
            m = MovieSuggestion.from_imdb(data['imdb'])
            m.watched = data['watched']
            if data['cage']:
                m.buffs.add(cage)
            if data['rock']:
                m.buffs.add(rock)

            if data['david']:
                m.expressed_interest.add(david)
            if data['jacobjan']:
                m.expressed_interest.add(jacobjan)
            if data['helena']:
                m.expressed_interest.add(helena)
            if data['saskia']:
                m.expressed_interest.add(saskia)

            m.save()
            print(m)
