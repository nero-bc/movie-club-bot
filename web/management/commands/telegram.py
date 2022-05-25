from django.core.management.base import BaseCommand, CommandError
from django.db.utils import ProgrammingError
import json
import datetime
from web.models import MovieSuggestion
import requests
import telebot
import re
import time
import os

bot = telebot.TeleBot(os.environ['TELOXIDE_TOKEN'])
imdb_link = re.compile("imdb.com/title/(tt[0-9]*)/?")

class Command(BaseCommand):
    help = "(Long Running) Telegram Bot"

    def handle(self, *args, **options):
        def handle_messages(messages):
            for message in messages:
                if message.text.startswith('/start') or message.text.startswith('/help'):
                    # Do something with the message
                    bot.reply_to(message, 'Howdy, how ya doin')
                elif message.text.startswith('/locate'):
                    r = requests.get('https://ipinfo.io/json').json()
                    bot.reply_to(message, r['org'])
                elif message.text.startswith('/countdown'):
                    for i in [5, 4, 3, 2, 1, 'Go! 🎉']:
                        bot.send_message(message.chat.id, str(i))
                        time.sleep(1)
                else:
                    for m in imdb_link.findall(message.text):
                        bot.send_message(message.chat.id, f"Found an IMDB link: {m}")

        bot.set_update_listener(handle_messages)
        bot.infinity_polling()
