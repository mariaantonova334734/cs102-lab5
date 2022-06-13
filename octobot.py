import json
import re
from datetime import datetime, timedelta

import gspread
import pandas as pd
import telebot
import validators

bot = telebot.TeleBot("5479099574:AAFX9pkEcS7naTC-kJiF8WMaAXGcxWC8DbE")

subject_dict = (
    {}
)  # словарь для хранения полльзовательской информации из разных чатов, ключ = chat.id, а значение - выбранный предмет

deadline_dict = (
    {}
)  # словарь для хранения полльзовательской информации из разных чатов, ключ = chat.id, а значение - номер дедлайна


def convert_date(date: str = "01/01/00"):
    """Конвертируем дату из строки в datetime"""
    try:
        return datetime.strptime(date, "%d/%m/%y")
    except ValueError:
        return False


def connect_table(message):
    """Подключаемся к Google-таблице"""
    url = message.text
    sheet_id_regex = re.compile(r"/d/(.*)/edit#")  # регулярные выражение
    mo = sheet_id_regex.search(url)
    if mo is None:  # если неправильна введена ссылка на таблицу
        info = bot.send_message(
            message.chat.id, "ID таблицы не обнаружен, введите ссылку корректно"
        )
        bot.register_next_step_handler(info, connect_table)
        return

    sheet_id = mo.group(1)

    # https://docs.google.com/spreadsheets/d/19Tvh5UNadVtmdstId1p5OX3oiCP3-5F1a_xnlMnHTy8/edit#gid=0
    # sheet_id = "19Tvh5UNadVtmdstId1p5OX3oiCP3-5F1a_xnlMnHTy8" # Нужно извлечь id страницы из ссылки на Google-таблицу
    try:
        with open("tables.json") as json_file:
            tables = json.load(json_file)
        title = len(tables) + 1
        tables[title] = {"url": url, "id": sheet_id}
    except FileNotFoundError:
        tables = {0: {"url": url, "id": sheet_id}}
    with open("tables.json", "w") as json_file:
        json.dump(tables, json_file)
    bot.send_message(message.chat.id, "Таблица подключена!")


def access_current_sheet():
    """Обращаемся к Google-таблице"""
    with open("tables.json") as json_file:
        tables = json.load(json_file)

    sheet_id = tables[max(tables)]["id"]
    gc = gspread.service_account(filename="credentials.json")
    sh = gc.open_by_key(sheet_id)
    worksheet = sh.sheet1
    # Преобразуем Google-таблицу в таблицу pandas

    df = pd.DataFrame(worksheet.get_all_records())
    return worksheet, tables[max(tables)]["url"], df


def choose_action(message):
    """Обрабатываем действия верхнего уровня"""
    if message.text == "Подключить Google-таблицу":
        info = bot.send_message(
            message.chat.id, "Введите ссылку на таблицу", reply_markup=None
        )
        bot.register_next_step_handler(info, connect_table)
        return
    elif message.text == "Редактировать предметы":
        start_markup = telebot.types.ReplyKeyboardMarkup(
            resize_keyboard=True, one_time_keyboard=True
        )
        start_markup.row("Внести новый предмет")
        start_markup.row("Редактировать предмет")
        start_markup.row("Удалить предмет")
        start_markup.row("Удалить ВСЕ")
        info = bot.send_message(
            message.chat.id,
            "Вы хотите внести новый предмет или редактировать текущий?",
            reply_markup=start_markup,
        )
        bot.register_next_step_handler(info, choose_subject_action)
        return

    elif message.text == "Редактировать дедлайн":
        start_markup = telebot.types.ReplyKeyboardMarkup(
            resize_keyboard=True, one_time_keyboard=True
        )
        worksheet, url, df = access_current_sheet()
        for i in df.values:
            subject_name = i[0]
            start_markup.row(subject_name)

        info = bot.send_message(
            message.chat.id,
            "Выберите предмет для редактирования дедлайна",
            reply_markup=start_markup,
        )
        # делаем меню для предметов, чтобы выбрать чей дедлайн отредактировать
        bot.register_next_step_handler(info, choose_subject)
        return

    elif message.text == "Посмотреть дедлайны на этой неделе":
        worksheet, url, df = access_current_sheet()
        date_today = datetime.today()
        nedel = date_today + timedelta(days=7)
        deadl = ""
        for strok in range(
            2, len(worksheet.col_values(1)) + 1
        ):  # проходимся по номерам строк предметов
            for current_d in worksheet.row_values(strok)[2:]:  # проходимся по ряду
                date_of_deadline = convert_date(current_d)
                if date_of_deadline != False:
                    if nedel >= date_of_deadline >= date_today:
                        deadl += (
                            worksheet.cell(strok, 1).value + " : " + current_d + "\n"
                        )  # предмет +дата дедалайна

        info = bot.send_message(message.chat.id, deadl)
        start(message)
        return
    else:
        info = bot.send_message(
            message.chat.id, "Выберите вариант из предложенных в меню"
        )
        bot.register_next_step_handler(info, choose_action)
        return


def choose_subject_action(message):
    """Выбираем действие в разделе Редактировать предметы"""

    if message.text == "Внести новый предмет":
        info = bot.send_message(
            message.chat.id, "Введите название нового предмета", reply_markup=None
        )
        bot.register_next_step_handler(info, add_new_subject)
        return

    elif message.text == "Редактировать предмет":
        start_markup = telebot.types.ReplyKeyboardMarkup(
            resize_keyboard=True, one_time_keyboard=True
        )
        worksheet, url, df = access_current_sheet()
        for i in df.values:
            subject_name = i[0]
            start_markup.row(subject_name)

        info = bot.send_message(
            message.chat.id, "Выберите редактируемый предмет", reply_markup=start_markup
        )

        # делаем меню для предметов, чтобы выбрать какой отредактировать

        bot.register_next_step_handler(info, update_subject)
        return

    elif message.text == "Удалить предмет":

        start_markup = telebot.types.ReplyKeyboardMarkup(
            resize_keyboard=True, one_time_keyboard=True
        )
        worksheet, url, df = access_current_sheet()
        for i in df.values:
            subject_name = i[0]
            start_markup.row(subject_name)

        info = bot.send_message(
            message.chat.id,
            "Выберите название предмета, который вы хотите удалить",
            reply_markup=start_markup,
        )

        # делаем меню для предметов, чтобы выбрать какой удалить

        bot.register_next_step_handler(info, delete_subject)
        return

    elif message.text == "Удалить ВСЕ":
        choose_removal_option(message)
        return

    else:
        info = bot.send_message(
            message.chat.id, "Выберите вариант из предложенных в меню"
        )
        bot.register_next_step_handler(info, choose_subject_action)
        return


def choose_deadline_action(message):
    """Выбираем действие в разделе Редактировать дедлайн"""
    if message.text == "Удалить дедлайн":
        info = bot.send_message(
            message.chat.id,
            "Введите номер дедлайна, который  вы хотите удалить",
            reply_markup=None,
        )
        bot.register_next_step_handler(info, delete_deadline)
        return
    elif message.text == "Обновить дедлайн":
        info = bot.send_message(
            message.chat.id,
            "Введите номер дедлайна, который хотите отредактировать",
            reply_markup=None,
        )
        bot.register_next_step_handler(info, update_subject_deadline)
        return
    elif message.text == "Добавить дедлайн":
        info = bot.send_message(
            message.chat.id,
            "Введите дату нового дедлайна в формате 01/01/00 (ДД/ММ/ГГ)",
            reply_markup=None,
        )
        bot.register_next_step_handler(info, add_new_deadline)
        return
    else:
        info = bot.send_message(
            message.chat.id, "Выберите вариант из предложенных в меню"
        )
        bot.register_next_step_handler(info, choose_deadline_action)
        return


def choose_removal_option(message):
    """Уточняем, точно ли надо удалить все"""
    info = bot.send_message(
        message.chat.id,
        "Введите да, если вы точно хотите удалить все",
        reply_markup=None,
    )
    bot.register_next_step_handler(info, clear_subject_list)
    return


def choose_subject(message):
    """Выбирали предмет, у которого хотим отредактировать дедлайн, и теперь выбираем, что хотим сделать с дедлайном"""
    subject_dict[message.chat.id] = message.text
    start_markup = telebot.types.ReplyKeyboardMarkup(
        resize_keyboard=True, one_time_keyboard=True
    )
    start_markup.row("Добавить дедлайн")
    start_markup.row("Обновить дедлайн")
    start_markup.row("Удалить дедлайн")
    info = bot.send_message(
        message.chat.id, "Выберите действие для дедлайна", reply_markup=start_markup
    )
    bot.register_next_step_handler(info, choose_deadline_action)
    return


def update_subject_deadline(message):
    """Обновляем дедлайн"""

    number = message.text  # номер дедлайна
    try:

        chislo = int(number)
        if chislo < 1:
            info = bot.send_message(
                message.chat.id,
                "Число должно быть больше нуля. Введите число еще раз",
                reply_markup=None,
            )
            bot.register_next_step_handler(info, update_subject_deadline)
            return

    except:
        info = bot.send_message(
            message.chat.id,
            "Это не целое число. Введите целое число",
            reply_markup=None,
        )
        bot.register_next_step_handler(info, update_subject_deadline)
        return

    deadline_dict[message.chat.id] = number

    info = bot.send_message(
        message.chat.id,
        "Введите новую дату дедлайна в формате 01/01/00 (ДД/ММ/ГГ)",
        reply_markup=None,
    )
    bot.register_next_step_handler(info, add_new_deadline)
    return


def add_new_subject(message):
    """Вносим новое название предмета в Google-таблицу"""

    new_subject_name = message.text
    worksheet, _, _ = access_current_sheet()
    subject_is_found, cell_row = find_subject_row(new_subject_name)

    if subject_is_found:  # если нашли такой же предмет
        info = bot.send_message(
            message.chat.id,
            "Вы ввели название существующего предмета. Введите название нового предмета",
            reply_markup=None,
        )
        bot.register_next_step_handler(info, add_new_subject)
        return
    else:
        worksheet.update_cell(cell_row, 1, new_subject_name)
        subject_dict[message.chat.id] = new_subject_name
        info = bot.send_message(
            message.chat.id,
            "Предмет добавлен в таблицу\nВведите ссылку предмета на баллы",
            reply_markup=None,
        )
        bot.register_next_step_handler(info, add_new_subject_url)
        return


def add_new_subject_url(message):
    """Вносим новую ссылку на таблицу предмета в Google-таблицу"""
    new_subject_url = message.text

    if not validators.url(new_subject_url):
        info = bot.send_message(
            message.chat.id,
            "Неверная ссылка. Введите ссылку еще раз",
            reply_markup=None,
        )
        bot.register_next_step_handler(info, add_new_subject_url)
        return

    current_subj = subject_dict[message.chat.id]

    worksheet, _, _ = access_current_sheet()

    subject_is_found, cell_row = find_subject_row(current_subj)

    if subject_is_found:  # если нашли такой же предмет
        worksheet.update_cell(
            cell_row, 2, new_subject_url
        )  # добавляем (заменяем url) предмета в таблице
        bot.send_message(message.chat.id, "Предмет отредактирован, ссылка добавлена")
        start(message)
        return
    else:
        bot.send_message(message.chat.id, "Ошибка. Предмет не найден")
        start(message)
        return


def add_new_deadline(message):
    """Добавляем информацию о новом дедлайне предмета в таблицу"""

    date = convert_date(message.text)

    if date == False:
        info = bot.send_message(
            message.chat.id,
            "Введен неправильный формат даты. Введите заново",
            reply_markup=None,
        )
        bot.register_next_step_handler(info, add_new_deadline)
        return

    current_date = datetime.today()
    if date < current_date:
        info = bot.send_message(
            message.chat.id,
            "Дата дедлайна уже прошла, введите новую дату",
            reply_markup=None,
        )
        bot.register_next_step_handler(info, add_new_deadline)
        return
    if date > current_date.replace(year=current_date.year + 1):
        info = bot.send_message(
            message.chat.id,
            "Дата дедлайна слишком далеко, учебный год уже закончится. Введите новую дату",
            reply_markup=None,
        )
        bot.register_next_step_handler(info, add_new_deadline)
        return

    try:

        current_num_of_deadline = deadline_dict[message.chat.id]
    except:
        current_num_of_deadline = None
    current_subj = subject_dict[message.chat.id]

    worksheet, _, _ = access_current_sheet()

    subject_is_found, cell_row = find_subject_row(current_subj)

    cell_col = 3  # проходим клетку ссылки (сдвигаемся вправо)
    cell_val = worksheet.cell(cell_row, cell_col).value  # клетка с первым дедлайном

    # ищем нужный дедлайн (находим колонку с нужным дедлайном)
    if current_num_of_deadline is None:  # если добавляем новый дедлайн

        while cell_val is not None:
            cell_col += 1
            cell_val = worksheet.cell(
                cell_row, cell_col
            ).value  # чтобы менялся значение cell_val

        # если вышли из цикла, значит дошли до пустого дедлайна. Записываем новый
        worksheet.update_cell(cell_row, cell_col, message.text)
        info = bot.send_message(
            message.chat.id,
            "Дедлайн добавлен\nНомер дедлайна " + worksheet.cell(1, cell_col).value,
        )
        start(message)
        return

    else:  # если нужно изменить существующий дедлайн

        cell_val = worksheet.cell(1, cell_col).value  # чтобы менялся значение cell_val

        while cell_val != current_num_of_deadline:
            cell_col += 1
            cell_val = worksheet.cell(
                1, cell_col
            ).value  # чтобы менялся значение cell_val

        # если вышли из цикла, значит дошли до нужного дедлайна. Записываем новую дату
        worksheet.update_cell(cell_row, cell_col, message.text)

        deadline_dict[message.chat.id] = None  # обнуляем переменную

        bot.send_message(
            message.chat.id,
            "Дедлайн исправлен\nНомер дедлайна " + worksheet.cell(1, cell_col).value,
        )

        start(message)
        return


def update_subject(message):
    """Обновляем информацию о предмете в Google-таблице"""
    subject_name = message.text

    worksheet, _, _ = access_current_sheet()
    subject_is_found, cell_row = find_subject_row(subject_name)

    if subject_is_found:
        subject_dict[
            message.chat.id
        ] = subject_name  # записываем id пользователя(кто использует бот) и предмет
        info = bot.send_message(
            message.chat.id, "Введите новое имя предмета", reply_markup=None
        )
        bot.register_next_step_handler(info, edit_subject_name)
        return

    else:
        # мы можем отредактировать только предмет, который уже есть в таблице
        # а для новых предметов существует функционал добавление предметов
        info = bot.send_message(
            message.chat.id,
            "Вы ввели название несуществующего предмета\nВыберите предмет из меню",
        )
        bot.register_next_step_handler(info, update_subject)
        return


def edit_subject_name(message):
    """Добавляем новый предмет и ссылку при редактировании предмета в Google-таблице"""
    new_subj = message.text
    current_subj = subject_dict[message.chat.id]
    worksheet, _, _ = access_current_sheet()

    subject_is_found, cell_row = find_subject_row(current_subj)
    if subject_is_found:
        worksheet.update_cell(
            cell_row, 1, new_subj
        )  # добавляем (заменяем название) предмета в таблице
        subject_dict[message.chat.id] = new_subj
        info = bot.send_message(
            message.chat.id,
            "Предмет отредактирован\nВведите новую ссылку на предмет",
            reply_markup=None,
        )
        bot.register_next_step_handler(info, add_new_subject_url)
        return


def delete_subject(message):
    """Удаляем предмет в Google-таблице"""
    del_subject_name = message.text

    worksheet, _, _ = access_current_sheet()
    subject_is_found, cell_row = find_subject_row(del_subject_name)

    if subject_is_found:
        worksheet.delete_row(cell_row)
        bot.send_message(message.chat.id, "Предмет удален")
        start(message)
        return
    else:
        bot.send_message(message.chat.id, "Предмет не найден")
        start(message)


def delete_deadline(message):
    """Удаляем дедлайн предмета в Google-таблице"""
    current_num_of_deadline = message.text  # номер дедлайна

    try:

        chislo = int(current_num_of_deadline)
        if chislo < 1:
            info = bot.send_message(
                message.chat.id,
                "Число должно быть больше нуля. Введите число еще раз",
                reply_markup=None,
            )
            bot.register_next_step_handler(info, update_subject_deadline)
            return

    except:
        info = bot.send_message(
            message.chat.id,
            "Это не целое число. Введите целое число",
            reply_markup=None,
        )
        bot.register_next_step_handler(info, update_subject_deadline)
        return

    current_subj = subject_dict[message.chat.id]

    worksheet, _, _ = access_current_sheet()

    subject_is_found, cell_row = find_subject_row(current_subj)

    cell_col = 3  # проходим клетку ссылки (сдвигаемся вправо)
    # cell_val = worksheet.cell(cell_row, cell_col).value  # клетка  с первым дедлайном

    if subject_is_found:

        cell_val = worksheet.cell(1, cell_col).value  # переходим на номера дедлайнов

        while cell_val != current_num_of_deadline:
            cell_col += 1
            cell_val = worksheet.cell(
                1, cell_col
            ).value  # чтобы менялся значение cell_val

        # удаляем дедлайн
        worksheet.update_cell(cell_row, cell_col, "")

        deadline_dict[message.chat.id] = None  # обнуляем переменную

        bot.send_message(message.chat.id, "Дедлайн удален")

        start(message)
        return


def clear_subject_list(message):
    """Удаляем все из Google-таблицы"""
    if message.text == "да":
        bot.send_message(message.chat.id, "Начинаем удаление таблицы")
    else:
        bot.send_message(message.chat.id, "Отменяем удаление таблицы")
        start(message)
        return

    worksheet, _, _ = access_current_sheet()

    cell_row = 2
    cell_col = 1
    cell_val = worksheet.cell(cell_row, cell_col).value

    while cell_val is not None:
        worksheet.delete_row(cell_row)
        cell_val = worksheet.cell(cell_row, cell_col).value

    bot.send_message(message.chat.id, "Удаление таблицы завершено")
    start(message)
    return


def find_subject_row(subject_name):
    """Находим строку предмета в таблице"""

    worksheet, _, _ = access_current_sheet()

    cell_row = 1
    cell_col = 1
    cell_val = worksheet.cell(cell_row, cell_col).value
    while cell_val is not None:
        if cell_val.upper() == subject_name.upper():
            return True, cell_row  # нащли предмет
        cell_row = cell_row + 1
        cell_val = worksheet.cell(cell_row, cell_col).value
    return False, cell_row  # не нашли предмет


def vedomosti_of_subjects(message):
    markup = telebot.types.InlineKeyboardMarkup()
    worksheet, url, df = access_current_sheet()
    for i in df.index:
        predm = telebot.types.InlineKeyboardButton(
            df.loc[i, "subject"], url=df.loc[i, "link"]
        )
        markup.add(predm)
    bot.send_message(message.chat.id, "Ведомости по предметам:", reply_markup=markup)


@bot.message_handler(commands=["start"])
def start(message):
    if message.text == "/start":
        vedomosti_of_subjects(message)
    start_markup = telebot.types.ReplyKeyboardMarkup(
        resize_keyboard=True, one_time_keyboard=True
    )
    try:
        with open("tables.json") as json_file:
            tables = json.load(json_file)

    except:  # если файла json нет
        start_markup.row("Подключить Google-таблицу")
    start_markup.row("Посмотреть дедлайны на этой неделе")
    start_markup.row("Редактировать дедлайн")
    start_markup.row("Редактировать предметы")
    info = bot.send_message(
        message.chat.id, "Что хотите сделать?", reply_markup=start_markup
    )
    bot.register_next_step_handler(
        info, choose_action
    )  # ждёт сообщение пользователя и потом вызывает указанную функцию с аргументом message


bot.infinity_polling()
