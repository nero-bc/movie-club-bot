import telebot
import re
import time
import os

bot = telebot.TeleBot(os.environ['TELOXIDE_TOKEN'])
imdb_link = re.compile("imdb.com/title/(tt[0-9]*)/?")

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, "Howdy, how are you doing?")

@bot.message_handler(commands=['countdown'])
def countdown(message):
    for i in [5, 4, 3, 2, 1, 'Go! 🎉']:
        bot.send_message(message.chat.id, str(i))
        time.sleep(1)


@bot.message_handler(func=lambda message: True)
def echo_all(message):
    for m in imdb_link.findall(message.text):
        bot.send_message(message.chat.id, f"Found an IMDB link: {m}")

bot.infinity_polling()
