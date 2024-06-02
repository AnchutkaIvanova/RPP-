from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram import types, Dispatcher, Bot
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.filters import Command
# Класс, который предоставляет точный арифметический тип для работы с числами с фиксированной точностью
from decimal import Decimal

import os
import psycopg2
import asyncio
import logging
# Встроенный модуль Python, который предоставляет доступ к некоторым
# переменным и функциям, взаимодействующим с интерпретатором Python
import sys

# Настройки бота

# Получение токена из переменных окружения
bot_token = os.getenv('API_TOKEN_BOT')

# Создание бота с токеном
bot = Bot(token=bot_token)

storage = MemoryStorage()  # Создает экземпляр класса MemoryStorage для хранения состояний машины состояний в памяти
dp = Dispatcher(bot=bot, storage=storage)  # Создает экземпляр класса Dispatcher с переданными экземплярами Bot и MemoryStorage

# Подключение к базе данных PostgreSQL
conn = psycopg2.connect(
    host="127.0.0.1",
    database="postgres1",
    user="postgres",
    password="postgres"
)

cur = conn.cursor()  # Создает курсор для выполнения SQL-запросов к базе данных.

cur.execute(
    "CREATE TABLE IF NOT EXISTS currencies ("
    "id SERIAL PRIMARY KEY,"
    "currency_name VARCHAR(50) NOT NULL,"
    "rate FLOAT NOT NULL)"
)

cur.execute(
    "CREATE TABLE IF NOT EXISTS admins ("
    "id SERIAL PRIMARY KEY,"
    "chat_id VARCHAR NOT NULL)"
)

conn.commit()  # Фиксирует изменения в базе данных


# Состояния для машины состояний
class ManageCurrency(StatesGroup):
    waiting_for_currency_name = State()  # Определение состояния для хранения названия валюты и курса к рублю
    waiting_for_currency_rate = State()
    waiting_for_currency_name_delete = State()
    waiting_for_currency_name_change = State()
    waiting_for_currency_rate_change = State()
    waiting_for_currency_name_convert = State()
    waiting_for_currency_rate_convert = State()


async def is_user_admin(user_id: int) -> bool:  # Функция проверяет, является ли пользователь с указанным идентификатором администратором
    # user_id: int означает, что функция принимает один аргумент user_id целочисленного типа
    # -> bool указывает, что функция возвращает логическое значение (True или False)
    cur.execute("SELECT * FROM admins WHERE chat_id = %s", (str(user_id),))  # Выполняет SQL-запрос к таблице admins в базе данных, где chat_id равен user_id
    return bool(cur.fetchone())  # Возвращает логическое значение (True или False), указывающее, был ли найден результат
    # Метод fetchone() объекта cur извлекает одну строку из результата запроса


# Добавление администратора в таблицу admins
async def add_admin(chat_id: int):  # Определяет асинхронную функцию add_admin,
    # которая добавляет администратора с указанным идентификатором чата в таблицу admins
    cur.execute("INSERT INTO admins (chat_id) VALUES (%s) RETURNING id", (str(chat_id),))
    conn.commit()  # Фиксирует изменения в базе данных


# Хэндлер для команды /manage_currency
@dp.message(Command('manage_currency'))
async def manage_currency_command(message: types.Message):
    if await is_user_admin(message.from_user.id):  # Проверка, является ли пользователь администратором
        # Создание объекта markup класса ReplyKeyboardMarkup, который используется для создания настраиваемой клавиатуры
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=3, keyboard=[])
        button1 = types.KeyboardButton(text="Добавить валюту")
        button2 = types.KeyboardButton(text="Удалить валюту")
        button3 = types.KeyboardButton(text="Изменить курс валюты")
        markup.keyboard.append([button1, button2, button3])  # Добавление кнопок на клавиатуру
        await message.answer("Выберите действие", reply_markup=markup)
    else:
        await message.answer("Нет доступа к команде")


# Хэндлер для нажатия на кнопку "Добавить валюту"
@dp.message(lambda message: message.text == "Добавить валюту")  # Лямбда-функция, которая проверяет, совпадает ли текст полученного сообщения с текстом
async def add_currency_command(message: types.Message, state: FSMContext):
    await message.answer("Введите название валюты:")
    await state.set_state(ManageCurrency.waiting_for_currency_name)  # Установка текущего состояния машины состояний в ManageCurrency.waiting_for_currency_name


# Хэндлер для обработки ввода пользователем названия валюты
@dp.message(ManageCurrency.waiting_for_currency_name)  # Текущее состояние машины состояний равно ManageCurrency.waiting_for_currency_name
async def process_currency_name(message: types.Message, state: FSMContext):
    data = await state.get_data()  # Получение данных из текущего состояния машины состояний

    cur.execute("SELECT * FROM currencies WHERE currency_name = %s", (message.text,))  # Выполнение SQL-запроса к базе данных для проверки существования валюты с указанным названием
    if cur.fetchone():  # Проверка наличия результатов запроса
        await message.answer(f"Валюта {message.text} уже существует.")
        await state.set_state(None)  # Сброс текущего состояния машины состояний
    else:
        await state.update_data(currency_name=message.text)  # Обновляет данные в текущем состоянии машины состояний, добавляя в них введенное пользователем название валюты
        await state.set_state(ManageCurrency.waiting_for_currency_rate)  # Устанавливает новое состояние машины состояний, которое ожидает ввода пользователем курса валюты
        await message.answer(f'Введите курс валюты {message.text} к рублю:')  # Отправляет сообщение пользователю с запросом ввода курса валюты к рублю


# Хэндлер для обработки ввода пользователем курса к рублю
@dp.message(ManageCurrency.waiting_for_currency_rate)
async def process_currency_rate(message: types.Message, state: FSMContext):
    data = await state.get_data()  # Получение данных из текущего состояния машины состояни
    currency_name = data.get('currency_name')  # Извлечение названия валюты из данных текущего состояния
    currency_rate = float(message.text)  # Преобразование текста сообщения пользователя в число с плавающей точкой и присвоение его переменной currency_rate

    cur.execute("INSERT INTO currencies (currency_name, rate) VALUES (%s, %s)", (currency_name, currency_rate))
    # Выполнение SQL-запроса на добавление новой валюты с указанным названием и курсом в таблицу currencies базы данных
    conn.commit()  # Фиксация изменений в базе данных
    await message.answer(f"Валюта {currency_name} с курсом {currency_rate} успешно добавлена!")
    await state.set_state(None)  # Сброс текущего состояния машины состояний


# Хэндлер для нажатия на кнопку "Удалить валюту"
@dp.message(lambda message: message.text == "Удалить валюту")  # Лямбда-функция, которая проверяет, совпадает ли текст полученного сообщения с текстом "Удалить валюту"
async def delete_currency_command(message: types.Message, state: FSMContext):
    await message.answer("Введите название валюты, которую хотите удалить:")
    await state.set_state(ManageCurrency.waiting_for_currency_name_delete)  # Установка текущего состояния машины состояний


# Обработчик для удаления существующей валюты
@dp.message(ManageCurrency.waiting_for_currency_name_delete)
async def process_delete_currency_name(message: types.Message, state: FSMContext):
    currency_name = message.text  # Присвоение переменной currency_name значения текста сообщения пользователя

    cur.execute("DELETE FROM currencies WHERE currency_name = %s", (currency_name,))  # Выполнение SQL-запроса на удаление валюты с указанным названием из таблицы currencies базы данных
    conn.commit()  # Фиксация изменений в базе данных

    await message.answer(f"Валюта {currency_name} успешно удалена.")
    await state.set_state(None)  # Сброс текущего состояния машины состояний


# Хэндлер для кнопки "Изменить курс валюты"
@dp.message(lambda message: message.text == "Изменить курс валюты")  # Лямбда-функция, которая проверяет, совпадает ли текст полученного сообщения с текстом
async def change_currency_rate_command(message: types.Message, state: FSMContext):
    # Определение асинхронной функции change_currency_rate_command, которая принимает два аргумента: message типа types.Message и state типа FSMContext
    await message.answer("Введите название валюты:")
    await state.set_state(ManageCurrency.waiting_for_currency_name_change)  # Установка текущего состояния машины состояний


# Хэндлер для обработки выбранной валюты для обновления курса
@dp.message(ManageCurrency.waiting_for_currency_name_change)
async def process_currency_name_change(message: types.Message, state: FSMContext):
    data = await state.get_data()  # Получение данных из текущего состояния машины состояний
    currency_name = data.get('currency_name')  # Извлечение названия валюты из данных текущего состояния

    cur.execute("SELECT * FROM currencies WHERE currency_name = %s", (message.text,))
    # Выполнение SQL-запроса на поиск валюты с указанным названием в таблице currencies базы данных
    currency_data = cur.fetchone()  # Извлечение данных о валюте из результата запроса.

    if not currency_data:  # Проверка наличия данных о валюте
        await message.answer(f"Валюты {message.text} не существует. Попробуйте снова.")
        await state.set_state(None)  # Сброс текущего состояния машины состояний
    else:
        await state.update_data(currency_name=message.text)  # Обновление данных в текущем состоянии машины состояний с указанием нового названия валюты
        await state.set_state(ManageCurrency.waiting_for_currency_rate_change)  # Установка текущего состояния машины состояний в ManageCurrency.waiting_for_currency_rate_change
        await message.answer(f'Введите новый курс для валюты {message.text} к рублю:')


# Хэндлер для обработки ввода нового курса валюты к рублю
@dp.message(ManageCurrency.waiting_for_currency_rate_change)
async def process_currency_rate_change(message: types.Message, state: FSMContext):
    data = await state.get_data()  # Получение данных из текущего состояния машины состояний
    currency_name = data.get('currency_name')  # Извлечение названия валюты из данных текущего состояния
    new_rate = float(message.text)  # Преобразование текста сообщения пользователя в число с плавающей точкой и присвоение его переменной new_rate

    # Обновление курса валюты в базе данных
    cur.execute("UPDATE currencies SET rate = %s WHERE currency_name = %s", (new_rate, currency_name))
    # Выполнение SQL-запроса на обновление курса валюты с указанным названием в таблице currencies базы данных
    conn.commit()  # Фиксация изменений в базе данных

    await message.answer(f"Курс валюты {currency_name} успешно изменен на {new_rate}.")
    await state.set_state(None)  # Сброс текущего состояния машины состояний


# Хэндлер для команды /get_currencies
@dp.message(Command('get_currencies'))
# Определение асинхронной функции get_currencies_command, которая принимает один аргумент message типа types.Message
async def get_currencies_command(message: types.Message):
    cur.execute("SELECT * FROM currencies")  # Выполнение SQL-запроса на получение всех данных из таблицы currencies базы данных
    currencies = cur.fetchall()  # Извлечение всех данных о валютах из результата запроса

    if not currencies:  # Проверка наличия данных о валютах
        await message.answer("Нет сохраненных валют")
    else:
        for currency in currencies:  # Цикл по всем валютам
            await message.answer(f"{currency[1]}: {currency[2]} руб.")


# Хэндлер для команды /start
@dp.message(Command('start'))
async def start_command(message: types.Message):
    # Добавление администратора в таблицу admins при старте бота
    if not await is_user_admin(1094679246):
        await add_admin(1094679246)  # Проверка, является ли пользователь с идентификатором 910772816 администратором
        # Если нет, то выполняется добавление его в таблицу admins базы данных с помощью функции add_admin

    if await is_user_admin(message.from_user.id):  # Проверка, является ли текущий пользователь администратором
        button1 = types.KeyboardButton(text="/start")
        button2 = types.KeyboardButton(text="/manage_currency")
        button3 = types.KeyboardButton(text="/get_currencies")
        button4 = types.KeyboardButton(text="/convert")
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=4, keyboard=[[button1, button2, button3, button4]])
        # Создание настраиваемой клавиатуры с кнопками, расположенными в 4 столбца
        await message.answer("Выберите команду из доступных:\n"
                    "/manage_currency - открыть панель администратора\n"
                    "/get_currencies - посмотреть список валют\n"
                    "/convert - конвертировать валюту", reply_markup=markup)  # Отправка сообщения пользователю с информацией о доступных командах и настраиваемой клавиатурой
    else:
        button1 = types.KeyboardButton(text="/start")
        button2 = types.KeyboardButton(text="/get_currencies")
        button3 = types.KeyboardButton(text="/convert")
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=3, keyboard=[[button1, button2, button3]])
        await message.answer("Выберите команду из доступных:\n"
                             " /get_currencies - посмотреть список валют\n"
                             " /convert - конвертировать валюту", reply_markup=markup)  # Отправка сообщения пользователю с информацией о доступных командах и настраиваемой клавиатурой


# Хэндлер для команды /convert
@dp.message(Command('convert'))  # Декоратор, который регистрирует функцию convert_command в качестве хэндлера для команды "/convert"
async def convert_command(message: types.Message, state: FSMContext):
    # Определение асинхронной функции convert_command, которая принимает два аргумента: message типа types.Message и state типа FSMContext
    await message.answer("Введите название валюты:")
    await state.set_state(ManageCurrency.waiting_for_currency_name_convert)  # Установка текущего состояния машины состояний


# Обработчик для ввода названия валюты для конвертации
@dp.message(ManageCurrency.waiting_for_currency_name_convert)
async def process_currency_name_convert(message: types.Message, state: FSMContext):
    currency_name = message.text  # Присвоение переменной currency_name значения текста сообщения пользователя

    await state.update_data(currency_name=currency_name)  # Обновление данных в текущем состоянии машины состояний с указанием названия валюты
    await state.set_state(ManageCurrency.waiting_for_currency_rate_convert)  # Установка текущего состояния машины состояний
    await message.answer("Введите сумму для конвертации:")


# Обработчик для ввода суммы для конвертации
@dp.message(ManageCurrency.waiting_for_currency_rate_convert)
async def process_currency_rate_convert(message: types.Message, state: FSMContext):
    data = await state.get_data()  # Получение данных из текущего состояния машины состояний
    currency_name = data.get('currency_name')  # Извлечение названия валюты из данных текущего состояния
    conversion_rate = float(message.text)  # Преобразование текста сообщения пользователя в число с плавающей точкой и присвоение его переменной conversion_rate

    cur.execute("SELECT rate FROM currencies WHERE currency_name = %s", (currency_name,))
    # Выполнение SQL-запроса на получение курса валюты с указанным названием из таблицы currencies базы данных
    rate = cur.fetchone() # Извлечение курса валюты из результата запроса

    if rate:  # Проверка наличия курса валюты
        rate_value = Decimal(rate[0]).quantize(Decimal('0.01'))  # Преобразование курса валюты из типа Decimal в тип float с точностью до двух знаков после запятой.
        converted_amount = conversion_rate * float(rate_value)  # Расчет суммы в рублях
        await message.answer(f"{conversion_rate} {currency_name} = {converted_amount} рублей.")  # Отправка сообщения пользователю с результатом конвертации
    else:
        await message.answer(f"Ошибка: Валюта {currency_name} не найдена.")

    await state.set_state(None)  # Сброс текущего состояния машины состояний


# Запуск бота
async def main() -> None:  # Определение асинхронной функции main, которая будет выполняться при запуске приложения
    try:
        await dp.start_polling(bot)  # Запуск бота с использованием метода start_polling диспетчера dp
        # Этот метод запускает цикл опроса серверов Telegram на предмет новых сообщений и обновлений
        # При использовании polling  бот регулярно отправляет запросы к серверам Telegram, чтобы проверить наличие новых событий
    finally:
        conn.close()  # Закрытие соединения с базой данных. Это необходимо для освобождения ресурсов и предотвращения утечек памяти

if __name__ == "__main__":  # Проверка, что этот файл запускается напрямую
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)  # Вывод сообщений с уровнем INFO или выше в консоль
    asyncio.run(main())  # Запуск асинхронной программы