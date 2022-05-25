from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
import traceback
from django.contrib.auth.models import Permission
from django.db.utils import ProgrammingError
import uuid

from web.models import MovieSuggestion

import isodate
from bs4 import BeautifulSoup
import datetime
import json
import os
import re
import requests
import telebot
import time

bot = telebot.TeleBot(os.environ['TELOXIDE_TOKEN'])
imdb_link = re.compile("imdb.com/title/(tt[0-9]*)/?")
MOVIE_VIEW = Permission.objects.get(name='Can view movie suggestion')
MOVIE_ADD = Permission.objects.get(name='Can add movie suggestion')
MOVIE_UPDATE = Permission.objects.get(name='Can change movie suggestion')

class Command(BaseCommand):
    help = "(Long Running) Telegram Bot"


    def get_ld_json(self, url: str) -> dict:
        parser = "html.parser"
        req = requests.get(url)
        soup = BeautifulSoup(req.text, parser)
        return json.loads("".join(soup.find("script", {"type":"application/ld+json"}).contents))

    def locate(self, message):
        r = requests.get('https://ipinfo.io/json').json()
        org = r['org']
        ip = r['ip']
        if 'GIT_REV' in os.environ:
            url = f"https://github.com/hexylena/emc-movie-club-bot/commit/{os.environ['GIT_REV']}"
        else:
            url = f"https://github.com/hexylena/emc-movie-club-bot/"

        bot.reply_to(message, f"{org} | {ip} | {url} | {message.chat.type}")

    def countdown(self, chat_id, message_parts):
        if len(message_parts) == 2:
            try:
                length = int(message_parts[1])
                if length > 10:
                    length = 10
                elif length < 1:
                    length = 1
            except:
                length = 5
        else:
            length = 5

        times = ['Go! 🎉'] + list(range(1, length + 1))
        for i in times[::-1]:
            bot.send_message(chat_id, str(i))
            time.sleep(1)

    def find_user(self, username):
        try:
            return User.objects.get(username=username)
        except User.DoesNotExist:
            user = User.objects.create_user(username, "", str(uuid.uuid4()))
            # Make our users staff so they can access the interface.
            user.is_staff = True
            # Add permissions
            user.user_permissions.add(MOVIE_VIEW)
            user.user_permissions.add(MOVIE_ADD)
            user.user_permissions.add(MOVIE_UPDATE)
            user.save()
            return user

    def change_password(self, message):
        # Only private chats are permitted
        if message.chat.type != 'private':
            return

        # It must be the correct user (I hope.)
        user = self.find_user(message.from_user.username)

        # Update their password
        newpassword = str(uuid.uuid4())
        user.set_password(newpassword)
        user.save()

        # Send them the password
        bot.reply_to(message, f"Your new password is: {newpassword}. Go change it at https://movie-club-bot.app.galaxians.org/admin/password_change/")


    def process_imdb_links(self, message):
        new_count = 0
        for m in imdb_link.findall(message.text):
            bot.send_message(message.chat.id, f"Received {m}")
            try:
                movie = MovieSuggestion.objects.get(imdb_id=m)
                bot.send_message(message.chat.id, f"{m} known.")
            except MovieSuggestion.DoesNotExist:
                if new_count > 0:
                    time.sleep(1)

                # Obtain user
                user = self.find_user(message.from_user.username)

                # Process details
                movie_details = self.get_ld_json(f"https://www.imdb.com/title/{m}/")
                bot.send_message(message.chat.id, f"{m} looks like a new movie, added it to the database.\n\n**{movie_details['name']}**\n\n{movie_details['description']}\n\n{' '.join(movie_details['genre'])}")

                movie = MovieSuggestion.objects.create(
                    imdb_id=m,
                    title=movie_details['name'],
                    year=int(movie_details['datePublished'].split('-')[0]),
                    rating=movie_details['aggregateRating']['ratingValue'],
                    ratings=movie_details['aggregateRating']['ratingCount'],
                    runtime=isodate.parse_duration(movie_details['duration']).seconds / 60,
                    watched=False,
                    cage_factor=False,
                    rock_factor=False,
                    suggested_by=user,
                    # expressed_interest=[],
                )
                movie.save()
                bot.send_message(message.chat.id, f"{m} looks like a new movie, thanks for the suggestion {user.username}.")
                new_count += 1


    def command_dispatch(self, message):
        if message.text.startswith('/start') or message.text.startswith('/help'):
            # Do something with the message
            bot.reply_to(message, 'Howdy, how ya doin\n\n' + '\n'.join([
                '/debug Show some debug info',
                '/passwd Change your password',
                '/countdown [number] Start a countdown',
                '[imdb link] - add to the database',
            ]))
        elif message.text.startswith('/debug'):
            self.locate(message)
        elif message.text.startswith('/passwd'):
            self.change_password(message)
        elif message.text.startswith('/countdown'):
            self.countdown(message.chat.id, message.text.split())
        else:
            self.process_imdb_links(message)

    def handle(self, *args, **options):
        def handle_messages(messages):
            for message in messages:
                # Skip non-text messages
                if message.text is None:
                    continue

                try:
                    self.command_dispatch(message)
                except Exception as e:
                    error_id = str(uuid.uuid4())
                    print(e)
                    print(error_id)
                    traceback.print_exc()
                    bot.send_message(message.chat.id, f"⚠️ oopsie whoopsie something went fucky wucky. @hexylena fix it. {error_id}")

        bot.set_update_listener(handle_messages)
        bot.infinity_polling()
