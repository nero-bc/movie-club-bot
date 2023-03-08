from django.core.management.base import BaseCommand
import time
from django.contrib.auth.models import User
from django.utils import timezone
import traceback
from django.contrib.auth.models import Permission
import uuid

from web.models import CriticRating, Interest, MovieSuggestion, Poll, PollArbitrary, AntiInterest, Event

import datetime
import json
import os
import random
import re
import requests
import telebot
import openai

bot = telebot.TeleBot(os.environ['TELOXIDE_TOKEN'])
openai.api_key = os.getenv("OPENAI_API_KEY")
imdb_link = re.compile("imdb.com/title/(tt[0-9]*)/?")
MOVIE_VIEW = Permission.objects.get(name='Can view movie suggestion')
MOVIE_ADD = Permission.objects.get(name='Can add movie suggestion')
MOVIE_UPDATE = Permission.objects.get(name='Can change movie suggestion')
START_TIME = time.time()
CHATGPT_CONTEXT = 20

# Wake up message
bot.send_message(195671723, "Hey hexy I'm re-deployed")

# Poll Handling
def handle_user_response(response):
    user_id = response.user.id
    option_ids = response.option_ids
    poll_id = response.poll_id
    user = find_user(response.user)

    try:
        poll = Poll.objects.get(poll_id=poll_id)
    except:
        poll = PollArbitrary.objects.get(poll_id=poll_id)

    if poll.poll_type == 'rate':
        film = poll.film
        critic_rating = option_ids[0]

        print(user_id, poll_id, option_ids, poll)
        try:
            cr = CriticRating.objects.get(tennant_id=poll.tennant_id, user=user, film=film)
            cr.score = critic_rating
            cr.save()
        except CriticRating.DoesNotExist:
            cr = CriticRating.objects.create(
                tennant_id=poll.tennant_id,
                user=user,
                film=film,
                score=critic_rating,
            )
            cr.save()
    elif poll.poll_type == 'interest':
        film = poll.film
        # These are numbered 0-4 right?
        print(option_ids)
        interest = 2 - option_ids[0]
        print(interest)

        ci = Interest.objects.create(
            tennant_id=poll.tennant_id,
            user=user,
            film=film,
            score=interest,
        )
        ci.save()
    elif poll.poll_type == 'removal':
        # tt8064418__tt7286966__tt4682266 [1] Helena
        tt_id = poll.options.split('__')[option_ids[0]]
        film = MovieSuggestion.objects.get(tennant_id=poll.tennant_id, imdb_id=tt_id)
        ai = AntiInterest.objects.create(
            tennant_id=poll.tennant_id, 
            poll_id=poll.poll_id,
            user=user,
            film=film,
        )
        ai.save()
        print(poll.options, option_ids, user)


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
    previous_messages = {}

    def locate(self, message):
        r = requests.get('https://ipinfo.io/json').json()
        org = r['org']
        ip = r['ip']
        if 'GIT_REV' in os.environ:
            url = f"https://github.com/hexylena/movie-club-bot/commit/{os.environ['GIT_REV']}"
        else:
            url = "https://github.com/hexylena/movie-club-bot/"

        data = {
            'Org': org,
            'IP': ip,
            'URL': url,
            'Execution Time': datetime.timedelta(seconds=time.process_time()),
            'Uptime': datetime.timedelta(seconds=time.time() - START_TIME),
            'Chat Type': message.chat.type,
            'Chat ID': message.chat.id,
            'Chat sender': message.from_user.id,
        }

        fmt_msg = "\n".join([f"{k}: {v}" for (k, v) in data.items()])
        bot.reply_to(message, fmt_msg)

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
        unwatched = sorted(MovieSuggestion.objects.filter(tennant_id=str(message.chat.id), status=0), key=lambda x: -x.get_score)[0:3]
        msg = "Top 3 films to watch:\n\n"
        for film in unwatched:
            msg += f"{film.title} ({film.year})\n"
            msg += f"  ⭐️{film.rating}\n"
            msg += f"  ⏰{film.runtime}\n"
            msg += f"  🎬{film.imdb_link}\n"
            if len(film.get_buffs) > 0:
                msg += f"  🎟{film.get_buffs}\n"
            msg += f"  📕{film.genre}\n\n"
        bot.send_message(message.chat.id, msg)
        self.chatgpt("Hey nick we're thinking of watching one of those three films. Which do you recommend and why?", message, str(message.chat.id))


    def process_imdb_links(self, message):
        new_count = 0
        for m in imdb_link.findall(message.text):
            # bot.send_message(message.chat.id, f"Received {m}")
            try:
                movie = MovieSuggestion.objects.get(tennant_id=str(message.chat.id), imdb_id=m)
                resp = f"Suggested by {movie.suggested_by} on {movie.added.strftime('%B %m, %Y')}\nVotes: "
                for v in movie.interest_set.all():
                    resp += f"{v.score_e}"

                bot.send_message(message.chat.id, resp)
            except MovieSuggestion.DoesNotExist:
                if new_count > 0:
                    time.sleep(1)

                # Obtain user
                user = find_user(message.from_user)

                # Process details
                movie = MovieSuggestion.from_imdb(tennant_id=str(message.chat.id), imdb_id=m)
                movie_details = json.loads(movie.meta)

                msg = f"{m} looks like a new movie, added it to the database. Thanks for the suggestion {user}!\n\n**{movie}**\n\n{movie_details['description']}\n\n{' '.join(movie_details['genre'])}"

                if 'aggregateRating' in movie_details:
                    rating_count = movie_details.get('aggregateRating', {}).get('ratingCount', 'n/a')
                    rating_value = movie_details.get('aggregateRating', {}).get('ratingValue', 'n/a')
                    msg += f"\n👥{rating_count}⭐️{rating_value}"

                bot.send_message(message.chat.id, msg)

                movie.suggested_by = user
                movie.save()
                new_count += 1
                self.send_interest_poll(message, movie)

    def is_gpt3(self, text):
        if text.startswith('/davinci'):
            return ('text-davinci-003', '/davinci')
        elif text.startswith('/babbage'):
            return ('text-babbage-001', '/babbage')
        elif text.startswith('/curie'):
            return ('text-curie-001', '/curie')
        elif text.startswith('/ada'):
            return ('text-ada-001', '/ada')
        elif text.startswith('/cage'):
            return ('gpt-3.5-turbo', '/cage')
        else:
            return False

    def filter_for_size(self, m):
        # Must keep system
        system = m[0]
        # Must keep user prompt
        user = m[-1]
        # The prompts we want to iterate over
        cullable = m[1:-1]
        culled = []
        # Most recent first
        for i in cullable[::-1]:
            if len(system['content']) + len(user['content']) + sum([len(x['content']) for x in culled]) + len(i['content']) > 4096:
                # Return what's already in there
                return [system] + culled[::-1] + [user]
            # Otherwise append
            culled.append(i)
        return [system] + culled[::-1] + [user]

    def chatgpt(self, query, message, tennant_id):
        messages = [
            {
                "role": "system",
                "content": f"You are Nick Cage, the famous actor. You ARE nick cage, your pronouns are he/him. You love quoting yourself in National Treasure. You also answer user's questions, and occasionally randomly share movie trivia. You never apologize. Never apologise. You swear sometimes. You are somewhat sassy and sarcastic in your responses."}
        ] + self.previous_messages.get(tennant_id, []) + [{"role": "user", "content": query}]

        messages = self.filter_for_size(messages)

        completion = openai.ChatCompletion.create(
          model="gpt-3.5-turbo",
          messages=messages
        )
        msg = completion.to_dict()['choices'][0]['message']
        gpt3_text = msg['content']

        # Setup if empty
        if tennant_id not in self.previous_messages:
            self.previous_messages[tennant_id] = []

        # Add the user's query
        self.add_context({"role": "user", "content": query}, tennant_id)
        # And the system's response
        self.add_context(msg, tennant_id)

        bot.send_message(message.chat.id, gpt3_text)

    def add_context(self, msg, tennant_id):
        self.previous_messages[tennant_id].append(msg)
        if len(self.previous_messages[tennant_id]) > CHATGPT_CONTEXT:
            self.previous_messages[tennant_id] = self.previous_messages[tennant_id][-CHATGPT_CONTEXT:]


    def command_dispatch(self, message):
        tennant_id = str(message.chat.id)
        if message.chat.id != -627602564:
            print(message)

        if message.text.startswith('/start') or message.text.startswith('/help'):
            # Do something with the message
            bot.reply_to(message, 'Howdy, how ya doin\n\n' + '\n'.join([
                '/debug - Show some debug info',
                '/status - Show some status info',
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
        # Ignore me adding /s later
        elif message.text.startswith('/debug'):
            self.log(tennant_id, 'debug')
            self.locate(message)
        elif message.text.startswith('/status'):
            self.log(tennant_id, 'status')
            self.locate(message)
        elif message.text.startswith('/passwd'):
            self.change_password(message)
        elif message.text.startswith('/countdown'):
            self.log(tennant_id, 'countdown', message.text.split())
            self.countdown(message.chat.id, message.text.split())
        elif message.text.startswith('/remove'):
            self.send_removal_poll(message)
        elif message.text.startswith('/remove-confirm'):
            self.finalize_removal_poll(message)
        elif message.text.startswith('/rate'):
            self.send_rate_poll(message)
        elif message.text.startswith('/suggest'):
            self.suggest(message)
        elif message.text.startswith('/update'):
            self.update_imdb_meta(message)
        elif message.text.startswith('/wrapped'):
            self.wrapped(message)
        elif message.text.startswith('/s'):
            return
        elif self.is_gpt3(message.text):
            if len(message.text.strip().split()) < 3:
                bot.reply_to(message, "Prompt too short, please try something longer.")
                return

            model, short = self.is_gpt3(message.text)

            if model == "gpt-3.5-turbo":
                self.chatgpt(
                    message.text[len(short) + 1:],
                    message,
                    tennant_id
                )
            else:
                response = openai.Completion.create(
                    model=model,
                    prompt=message.text[len(short) + 1:],
                    temperature=0.7,
                    max_tokens=512,
                    top_p=1,
                    frequency_penalty=0,
                    presence_penalty=0
                )
                gpt3_text = response.to_dict()['choices'][0].text
                bot.reply_to(message, "Prompt: " + message.text[len(short) + 1:] + gpt3_text)
        elif message.text.startswith('/'):
            bot.send_message(message.chat.id, "You talkin' to me? Well I don't understand ya, try again.")
        else:
            self.process_imdb_links(message)

            # Add all messages to the list of recent messages
            if tennant_id not in self.previous_messages:
                self.previous_messages[tennant_id] = []
            if not message.from_user.is_bot:
                self.add_context({"role": "user", "content": message.from_user.first_name + ": " + message.text}, tennant_id)

            if random.random() < 0.05:
                self.chatgpt(
                    message.text,
                    message,
                    tennant_id
                )


    def send_interest_poll(self, message, film):
        question = f'Do you wanna see {film}?'
        options = ['💯', '🆗', '🤷‍♀️🤷🤷‍♂️ meh', '🤬hatewatch', '🚫veto🙅']

        r = bot.send_poll(message.chat.id, question=question, options=options, is_anonymous=False)
        p = Poll.objects.create(
            tennant_id=str(message.chat.id),
            poll_id=r.poll.id,
            film=film,
            question=question,
            options='__'.join(options),
            poll_type="interest"
        )
        p.save()

    def update_imdb_meta(self, message):
        for m in MovieSuggestion.objects.filter(tennant_id=str(message.chat.id), rating=0):
            m.update_from_imdb()
            bot.send_message(message.chat.id, f"Updating {m} from imdb")

    def finalize_removal_poll(self, message):
        # Get latest removal poll
        p = PollArbitrary.objects.filter(tennant_id=str(message.chat.id)).order_by('-poll_id')[0]
        print(p.poll_id)

    def send_removal_poll(self, message):
        question = 'Pick one of these to DELETE from our watchlist.'
        # Only unwatched
        asdf = MovieSuggestion.objects.filter(status=0)
        # Only movies over 100 days and unwatched are game
        asdf = [x for x in asdf if x.days_since_added > 100]
        # Get the worst TWO.
        options = sorted(asdf, key=lambda x: x.get_score)[0:2]

        option_text = [f"{x.title} ({x.year}), added {x.days_since_added} days ago, rating {x.rating}" for x in options]
        option_nums = [str(x.imdb_id) for x in options]

        r = bot.send_poll(message.chat.id, question=question, options=option_text, is_anonymous=False)
        p = PollArbitrary.objects.create(
            tennant_id=str(message.chat.id),
            poll_id=r.poll.id,
            question=question,
            metadata=message.chat.id,
            options='__'.join(option_nums),
            poll_type="removal"
        )
        p.save()

    def wrapped(self):
        pass

    def log(self, tennant_id, key, value=""):
        Event.objects.create(
            tennant_id=str(tennant_id),
            event_id=key,
            value=value,
        )

    def send_rate_poll(self, message: telebot.types.Message):
        parts = message.text.split()
        if len(parts) != 2:
            bot.send_message(message.chat.id, "Error, use /rate tt<id>")
            return

        try:
            film = MovieSuggestion.objects.get(tennant_id=str(message.chat.id), imdb_id=parts[1])
        except:
            bot.send_message(message.chat.id, "Unknown film")
            return

        film.status = 1
        film.status_changed_date = timezone.now()
        film.save()

        question = f'What did you think of {film}? Give it a rating.'
        options = ['0', '⭐️', '⭐️⭐️', '⭐️⭐️⭐️', '⭐️⭐️⭐️⭐️', '⭐️⭐️⭐️⭐️⭐️']

        r = bot.send_poll(message.chat.id, question=question, options=options, is_anonymous=False)
        Poll.objects.create(
            tennant_id=str(message.chat.id), 
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

                    try:
                        self.add_context({"role": "user", "content": f"An exception occurred: {str(e)}"}, tennant_id)
                    except:
                        pass

        bot.set_update_listener(handle_messages)
        bot.infinity_polling()
