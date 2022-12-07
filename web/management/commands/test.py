from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import Permission

from web.models import *

import os
import re
import telebot
import openai

bot = telebot.TeleBot(os.environ['TELOXIDE_TOKEN'])
openai.api_key = os.getenv("OPENAI_API_KEY")
imdb_link = re.compile("imdb.com/title/(tt[0-9]*)/?")
MOVIE_VIEW = Permission.objects.get(name='Can view movie suggestion')
MOVIE_ADD = Permission.objects.get(name='Can add movie suggestion')
MOVIE_UPDATE = Permission.objects.get(name='Can change movie suggestion')

from telebot.custom_filters import TextFilter, TextMatchFilter, IsReplyFilter
from telebot import TeleBot, types

class Command(BaseCommand):
    help = "Test movie processing"

    def add_arguments(self, parser):
        parser.add_argument('url')

    def handle(self, url, *args, **options):
        movie = MovieSuggestion.from_imdb(url)
