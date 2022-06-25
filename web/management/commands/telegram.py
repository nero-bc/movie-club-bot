from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from django.utils import timezone
import traceback
from django.contrib.auth.models import Permission
from django.db.utils import ProgrammingError
import uuid

from web.models import *

import isodate
from bs4 import BeautifulSoup
import datetime
import json
import os
import re
import requests
import telebot
import openai
import time

bot = telebot.TeleBot(os.environ['TELOXIDE_TOKEN'])
openai.api_key = os.getenv("OPENAI_API_KEY")
imdb_link = re.compile("imdb.com/title/(tt[0-9]*)/?")
MOVIE_VIEW = Permission.objects.get(name='Can view movie suggestion')
MOVIE_ADD = Permission.objects.get(name='Can add movie suggestion')
MOVIE_UPDATE = Permission.objects.get(name='Can change movie suggestion')

from telebot.custom_filters import TextFilter, TextMatchFilter, IsReplyFilter
from telebot import TeleBot, types


# Poll Handling
def handle_user_response(response):
    user_id = response.user.id
    option_ids = response.option_ids
    poll_id = response.poll_id
    user = find_user(response.user)

    poll = Poll.objects.get(poll_id=poll_id)
    film = poll.film

    if poll.poll_type == 'rate':
        critic_rating = option_ids[0]

        print(user_id, poll_id, option_ids, poll)
        try:
            cr = CriticRating.objects.get(user=user, film=film)
            cr.score = critic_rating
            cr.save()
        except CriticRating.DoesNotExist:
            cr = CriticRating.objects.create(
                user=user,
                film=film,
                score=critic_rating,
            )
            cr.save()
    elif poll.poll_type == 'interest':
        # Only care if they're interested
        if option_ids[0] != 0:
            return

        film.expressed_interest.add(user)
        film.save()


bot.poll_answer_handler(func=lambda call: True)(handle_user_response)



def find_user(passed_user):
    try:
        ret = User.objects.get(username=passed_user.id)
    except User.DoesNotExist:
        user = User.objects.create_user(passed_user.id, "", str(uuid.uuid4()))
        # Make our users staff so they can access the interface.
        user.is_staff = True
        # Add permissions
        user.user_permissions.add(MOVIE_VIEW)
        user.user_permissions.add(MOVIE_ADD)
        user.user_permissions.add(MOVIE_UPDATE)
        user.save()
        ret = user

    if passed_user:
        ret.first_name = getattr(passed_user, 'first_name', '') or ""
        ret.last_name = getattr(passed_user, 'last_name', '') or ""
        ret.save()

    return ret



class Command(BaseCommand):
    help = "(Long Running) Telegram Bot"


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

    def change_password(self, message):
        # Only private chats are permitted
        if message.chat.type != 'private':
            return

        # It must be the correct user (I hope.)
        user = find_user(message.from_user)

        # Update their password
        newpassword = str(uuid.uuid4())
        user.set_password(newpassword)
        user.save()

        # Send them the password
        bot.reply_to(message, f"Username: {user.username}\npassword: {newpassword}\n\n Go change it at https://movie-club-bot.app.galaxians.org/admin/password_change/")


    def suggest(self, message):
        unwatched = sorted(MovieSuggestion.objects.filter(watched=False), key=lambda x: -x.get_score)[0:3]
        msg = "Top 3 films to watch:\n\n"
        for film in unwatched:
            msg += f"{film.title} ({film.year})\n"
            msg += f"  ⭐️{film.rating}\n"
            msg += f"  ⏰{film.runtime}\n"
            msg += f"  📕{film.genre}\n\n"

        bot.send_message(message.chat.id, msg)


    def process_imdb_links(self, message):
        new_count = 0
        for m in imdb_link.findall(message.text):
            # bot.send_message(message.chat.id, f"Received {m}")
            try:
                movie = MovieSuggestion.objects.get(imdb_id=m)
                bot.send_message(message.chat.id, f"{m} known.")
            except MovieSuggestion.DoesNotExist:
                if new_count > 0:
                    time.sleep(1)

                # Obtain user
                user = find_user(message.from_user)

                # Process details
                movie = MovieSuggestion.from_imdb(m)
                movie_details = json.loads(movie.meta)

                bot.send_message(message.chat.id, f"{m} looks like a new movie, added it to the database. Thanks for the suggestion {user}!\n\n**{movie}**\n\n{movie_details['description']}\n\n{' '.join(movie_details['genre'])}")

                movie.suggested_by = user
                movie.save()
                new_count += 1
                self.send_interest_poll(message, movie)

    def is_gpt3(self, text):
        if text.startswith('/davinci'):
            return ('text-davinci-002', '/davinci')
        elif text.startswith('/babbage'):
            return ('text-babbage-001', '/babbage')
        elif text.startswith('/curie'):
            return ('text-curie-001', '/curie')
        elif text.startswith('/ada'):
            return ('text-ada-001', '/ada')
        else:
            return False

    def command_dispatch(self, message):
        if message.chat.id != -627602564:
            print(message)

        if message.text.startswith('/start') or message.text.startswith('/help'):
            # Do something with the message
            bot.reply_to(message, 'Howdy, how ya doin\n\n' + '\n'.join([
                '/debug - Show some debug info',
                '/passwd - Change your password (DM only.)',
                '/countdown [number] - Start a countdown',
                '/rate tt<id> - Ask group to rate the film',
                '/suggest - Make suggestions for what to watch',
                '[imdb link] - add to the database',
                '# GPT-3 Specific',
                '/ada <text>',
                '/babbage <text>',
                '/curie <text>',
                '/davinci <text>',
            ]))
        elif message.text.startswith('/debug'):
            self.locate(message)
        elif message.text.startswith('/passwd'):
            self.change_password(message)
        elif message.text.startswith('/countdown'):
            self.countdown(message.chat.id, message.text.split())
        elif message.text.startswith('/rate'):
            self.send_rate_poll(message)
        elif message.text.startswith('/suggest'):
            self.suggest(message)
        elif self.is_gpt3(message.text):
            model, short = self.is_gpt3(message.text)

            response = openai.Completion.create(
                model=model,
                prompt=message.text[len(short) + 1:],
                temperature=0.7,
                max_tokens=512,
                top_p=1,
                frequency_penalty=0,
                presence_penalty=0
            )
            gpt3 = response.to_dict()['choices'][0].text
            bot.reply_to(message, gpt3.strip())
        elif message.text.startswith('/'):
            bot.send_message(message.chat.id, "You talkin' to me? Well I don't understand ya, try again.")
        else:
            self.process_imdb_links(message)

    def send_interest_poll(self, message, film):
        question = f'Do you wanna see {film}?'
        options = ['💯', 'meh']

        r = bot.send_poll(message.chat.id, question=question, options=options, is_anonymous=False)
        p = Poll.objects.create(
            poll_id=r.poll.id,
            film=film,
            question=question,
            options='__'.join(options),
            poll_type="interest"
        )
        p.save()
    def send_rate_poll(self, message: types.Message):
        parts = message.text.split()
        if len(parts) != 2:
            bot.send_message(message.chat.id, "Error, use /rate tt<id>")
            return

        try:
            film = MovieSuggestion.objects.get(imdb_id=parts[1])
        except:
            bot.send_message(message.chat.id, "Unknown film")
            return

        film.watched = True
        film.watched_date = timezone.now()
        film.save()

        question = f'What did you think of {film}? Give it a rating.'
        options = ['0', '⭐️', '⭐️⭐️', '⭐️⭐️⭐️', '⭐️⭐️⭐️⭐️', '⭐️⭐️⭐️⭐️⭐️']

        r = bot.send_poll(message.chat.id, question=question, options=options, is_anonymous=False)

        p = Poll.objects.create(
            poll_id=r.poll.id,
            film=film,
            question=question,
            options='__'.join(options),
            poll_type="rate"
        )

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
