from aiogram.types import ParseMode, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher.filters import Text
from aiogram import Bot, Dispatcher, types
from aiogram.dispatcher import FSMContext
import aiogram.utils.markdown as md
from aiogram.utils import executor
from PIL import Image
import logging
import sqlite3
import io
import os
import re

# создаем переменные, таблицы, подключаемся к бд
bot = Bot(token='5741355813:AAEC_Yeyv5sSYAS4faurDcznjCStMqGJNEM')
logging.basicConfig(level=logging.INFO)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)
conn = sqlite3.connect(
    'baza.db', check_same_thread=False)  # подключение к бд

# Создаем таблицу в базе данных
cursor = conn.cursor()
cursor.execute("""CREATE TABLE IF NOT EXISTS users 
                (ID INTEGER PRIMARY KEY, 
                user_id INTEGER, 
                username TEXT, 
                name TEXT, 
                age INTEGER, 
                gender TEXT,
                photo TEXT, 
                city TEXT, 
                nomer_telephona INTEGER)""")


res = cursor.execute('SELECT * FROM users')

cursor.execute("""CREATE TABLE IF NOT EXISTS interes 
                (id INTEGER PRIMARY KEY,
                interesName TEXT)""")


# Записываем в статы
class Form(StatesGroup):
    name = State()  # будет представленно в хранилище как Form:name
    age = State()  # Form:age
    gender = State()  # Form:gender
    photo = State()  # Form:photo
    city = State()  # Form:city
    nomer_telephona = State()  # Form:nomer_telephona
    interes = State()  # Form:interests


cursor.execute('SELECT interesNAME FROM interes')
interests = []
for row in cursor:
    interests.append(row)
    print(interests)

# проверка на кирилицу


def isCirylic(text: str):
    for char in text:
        if re.search(r'[а-яА-ЯёЁ]', char) is None:
            return False
    return True

# обработчик команды старт


@dp.message_handler(commands='start')
async def cmd_start(message: types.Message):
    await Form.name.set()
    await message.reply("Привет! Как звать тебя? Ответ принимается кирилицей в следующем формате ФИО")


# обработка и запрос имени пользователя
@dp.message_handler(lambda message: not isCirylic(message.text), state=Form.name)
async def process_name(message: types.Message, state: FSMContext):

    async with state.proxy() as data:
        data['name'] = message.text

    await Form.next()
    await state.update_data(name=str(message.text))
    await message.reply("Укажите свой возраст?")


# Проверка и запрос возраста
@dp.message_handler(lambda message: not message.text.isdigit(), state=Form.age)
async def process_age_invalid(message: types.Message, state: FSMContext):
    return await message.reply("Возраст должен быть числом.\Укажите ваш возраст повротно. (только цифры)")

# обработчик возраста


@dp.message_handler(lambda message: message.text.isdigit(), state=Form.age)
async def process_age(message: types.Message, state: FSMContext):
    # Обновление состояния и данных
    await Form.next()
    await state.update_data(age=int(message.text))
    # Создание и настройка клавиатуры гендера
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, selective=True)
    markup.add("Мужчина", "Женщина")
    markup.add("Другое")

    await message.reply("Укажите свой пол?", reply_markup=markup)

# хендлер для обработки и взаимодействий кнопок с гендером


@dp.message_handler(lambda message: message.text in ["Мужчина", "Женщина", "Другое"], state=Form.gender)
async def process_gender(message: types.Message, state: FSMContext):
    await Form.next()
    await state.update_data(gender=str(message.text))
    await message.reply("Теперь фото")

# обработчик запроса гендера


@dp.message_handler(lambda message: message.text not in ["Мужчина", "Женщина", "Другое"], state=Form.gender)
async def process_gender_invalid(message: types.Message, state: FSMContext):
    return await message.reply("Вы указали неверную информацию. Укажите ваш пол с клавиатуры.")

# хендлер для обработки фотки пользователя


@dp.message_handler(content_types=types.ContentType.PHOTO, state=Form.photo)
async def process_photo(message: types.Message, state: FSMContext):
    await Form.next()
    # загрузка фотки из телеги
    await message.photo[-1].download('user.jpg')
    # конвертация фотки в массив байтов
    byte_img_IO = io.BytesIO()
    byte_img = Image.open('user.jpg')
    byte_img.save(byte_img_IO, "PNG")
    byte_img_IO.seek(0)
    with open('user.jpg', 'rb') as f:
        byte_img = byte_img_IO.read()
    os.remove('user.jpg')
    await state.update_data(photo=byte_img)
    await message.reply("Введите город проживания")

# хэндлер для города


@dp.message_handler(lambda message: isCirylic(message.text), state=Form.city)
async def process_city(message: types.Message, state: FSMContext):
    await Form.next()
    # создание кнопки с номером телефона
    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True)
    markup.add(InlineKeyboardButton(
        'Поделится номером телефона', request_contact=True))
    # сохранение города в FSMContext
    await state.update_data(city=str(message.text))
    await message.reply("Ваш номер телефона?", reply_markup=markup)

# обработчик запроса города


@dp.message_handler(lambda message: not isCirylic(message.text), state=Form.city)
async def process_city_invalid(message: types.Message):
    return await message.reply("Введенная вами информация неверна. Введите информацию коректно.")

# хендлер для номера телефона пользователя


@dp.message_handler(content_types=types.ContentType.CONTACT, state=Form.nomer_telephona)
async def process_nomer_telephona(message: types.Message, state: FSMContext):
    await Form.next()
    # удаляем кнопку телефона
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
# загрузка и создание кнопок из бд
    for element in interests:
        markup.add(element[0])
    # сохранение номера в FSMContext
    await state.update_data(nomer_telephona=str(message.contact.phone_number))
    await message.reply("Выберите свои увличения: ", reply_markup=markup)

# последний хэндлер в цепочке; обрабатывает interes


@dp.message_handler(state=Form.interes)
async def process_interes(message: types.message, state: FSMContext):
    async with state.proxy() as data:
        data['interes'] = str(message.text)

    # конвертация байтов из FSMContext в фото и вывод
    byte_img = data['photo']
    data_bytes_IO = io.BytesIO(byte_img)
    img = Image.open(data_bytes_IO)
    img.save('user_output.jpg')
    photo = open('user_output.jpg', "rb")

    # загрузка данных из стейтов в переменные
    username = str(message.chat.username)
    user_id = int(message.from_user.id)
    name = str(data['name'])
    age = int(data['age'])
    gender = str(data['gender'])
    city = str(data['city'])
    nomer_telephona = str(data['nomer_telephona'])
    interes = data['interes']

    # загрузка данных юзера в БД
    query = ("""INSERT INTO users(user_id, username, name, age, gender, nomer_telephona, city, photo) VALUES(?,?,?,?,?,?,?,?)""")
    cursor.execute(query, (user_id, username, name,
                   age, gender, nomer_telephona, city, byte_img))
    conn.commit()
    # отправляем фото, закрываем стрим который читает файл c фото, удаляем сохраненное фото
    await bot.send_photo(chat_id=message.chat.id, photo=photo)
    photo.close()
    os.remove('user_output.jpg')

# Отправляем сообщение с данными, которые внес юзер
    await bot.send_message(
        message.chat.id,
        md.text(
            md.text('UID Телеграмма: ', md.bold(user_id)),
            md.text('Юзернейм: ', md.bold(username)),
            md.text('ФИО: ', md.bold(name)),
            md.text('Возраст: ', md.bold(age)),
            md.text('Пол: ', md.bold(gender)),
            md.text('Номер телефона: ', md.bold(nomer_telephona)),
            md.text('Город: ', md.bold(city)),
            md.text('Интересы: ', md.bold(interes)),
            sep='\n',
        ),
        parse_mode=ParseMode.MARKDOWN, reply_markup=types.ReplyKeyboardRemove())
# # # заканчиваем обработку и закрываем FSM
    await state.finish()

    conn.close()

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
