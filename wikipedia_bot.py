import telebot, wikipedia, re

bot = telebot.TeleBot('5263359261:AAHtYhEXRRwhBHbFe92CUDF8rizPsOH75no') #токен

wikipedia.set_lang("ru")
#Очищаем полученный текст, чтобы выводилось только определение слова
def get_wiki(s):
    try:
        ny = wikipedia.page(s)
        #Первая 1000 символов
        wikitext = ny.content[:1000]
        # Разделяем по точкам
        wikimas = wikitext.split('.')
        # Отбрасываем все после последней точки
        wikimas = wikimas[:-1]
        # Создаем пустую переменную для текста
        wikitext2 = ''
        # Проходимся по строкам, где нет знаков «равно» (то есть все, кроме заголовков)
        for x in wikimas:
            if not ('==' in x):
                if (len((x.strip())) > 3):
                    wikitext2 = wikitext2 + x + '.'
            else:
                break
        # при помощи регулярных выражений убираем разметку
        wikitext2 = re.sub('\([^()]*\)', '', wikitext2)
        wikitext2 = re.sub('\([^()]*\)', '', wikitext2)
        wikitext2 = re.sub('\{[^\{\}]*\}', '', wikitext2)
        return wikitext2
    except Exception as e:
        return 'В энциклопедии нет информации об этом'

#Функция старта
@bot.message_handler(commands=["start"])
def start(m, res=False):
    bot.send_message(m.chat.id, 'Отправьте мне любое слово, и я найду его значение на Wikipedia')

#Получает сообщение от пользователя
@bot.message_handler(content_types=["text"])
def handle_text(message):
    bot.send_message(message.chat.id, get_wiki(message.text))

#запуск бота
bot.polling(none_stop=True,interval = 0)
