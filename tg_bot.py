import telebot
import random
bot = telebot.TeleBot('5375047454:AAFJIXGalo03eHzcwSjwZmLnhRaRVtx8t7o') #токен

#Обрабатываем команду старт
@bot.message_handler(commands=["start"])#обработчик для разных типов сообщений
                                         #(в этом случае готовая команда start, ниже обработчик для текста)
def start(m, res=False):
    bot.send_message(m.chat.id, 'Я на связи. Напиши мне что-нибудь )')

# #Обрабатываем сообщения
# @bot.message_handler(content_types=["text"])
# def handle_text(message):
#     bot.send_message(message.chat.id, 'Вы написали: ' + message.text)



@bot.message_handler(commands=['get_random'])
def send_picture(message):
    kol_kart = int(message.text.split()[1]) #количество картинок
    url = 'https://aws.random.cat/view/'
    i = 0
    while i < kol_kart:
        try:
            bot.send_photo(message.chat.id, url + str(random.randint(1,2000)))
            i+=1
        except:
            print("Картинки с таким номером не существует в базе")

#пример ввода /get_random 3

@bot.message_handler(commands=['get_cat'])
def send_picture2(message):
    id_kart = int(message.text.split()[1]) #id_картинки кота
    url = 'https://aws.random.cat/view/'
    try:
        bot.send_photo(message.chat.id, url + str(id_kart))

    except:
        bot.send_message(message.chat.id, "Картинки с таким номером не существует в базе")
        print("Картинки с таким номером не существует в базе")

#пример ввода /get_cat 10


#запуск бота
bot.polling(none_stop=True,interval = 0)


#bot.polling(none_stop=True,interval = 0)