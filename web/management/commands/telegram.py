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
                    if len(message.text.split()) == 2:
                        length = int(message.text.split()[1])
                    else:
                        length = 5

                    times = ['Go! 🎉'] + list(range(1, length + 1))
                    for i in times[::-1]:
                        bot.send_message(message.chat.id, str(i))
                        time.sleep(1)
                else:
                    for m in imdb_link.findall(message.text):
                        try:
                            movie = MovieSuggestion.objects.get(imdb_id=m)
                            bot.send_message(message.chat.id, f"{m} known.")
                        except MovieSuggestion.DoesNotExist:
                            print("New movie! Adding it to the database")
                            movie = MovieSuggestion.objects.create(
                                imdb_id=m,
                            )
                            movie.save()
                            bot.send_message(message.chat.id, f"{m} looks like a new movie, added it to the database.")

        bot.set_update_listener(handle_messages)
        bot.infinity_polling()
