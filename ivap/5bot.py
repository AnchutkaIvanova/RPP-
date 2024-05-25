from aiogram.dispatcher import FSMContext  # Импорт класса для работы с FSM (finite state machine)
from aiogram.contrib.fsm_storage.memory import MemoryStorage  # Импорт класса для хранения состояний FSM в памяти
from aiogram.dispatcher.filters.state import State, StatesGroup  # Импорт классов для определения состояний FSM и группы состояний
from aiogram.types import Message  # Импорт класса Message для работы с сообщениями
from aiogram import Bot, Dispatcher, types  # Импорт классов для работы с ботом и диспетчером
from aiogram.contrib.middlewares.logging import LoggingMiddleware  # Импорт middleware для логирования
from aiogram.utils import executor  # Импорт функции executor для запуска бота
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
import logging  # Импорт модуля логирования
import os  # Импорт модуля для работы с переменными окружения
import asyncpg


# Получение API токена бота из переменных окружения
bot_token = os.getenv('API_TOKEN_BOT')

# Создание экземпляра бота с использованием API токена
bot = Bot(token=bot_token)
# Инициализация диспетчера с указанием хранилища в памяти
dp = Dispatcher(bot, storage=MemoryStorage())

# Обработчик команды /admin_id для добавления в бд меня как администратора
@dp.message_handler(commands=['admin_id'])
async def show_user_id(message: types.Message):
    user_id = message.from_user.id#Здесь извлекается user_id пользователя, отправившего сообщение,
    # с помощью атрибута id объекта from_user сообщения. from_user содержит информацию о пользователе, отправившем сообщение.
    await message.reply(f"Ваш user_id: {user_id}")

# Функция для проверки администраторских прав пользователя
async def is_admin(user_id):
    conn = await asyncpg.connect(database='postgres1', user='postgres', password='postgres', host='127.0.0.1', port=5432)
    #В этой строке устанавливается подключение к базе данных PostgreSQL.
    # asyncpg.connect() возвращает объект подключения к базе данных, который позволяет взаимодействовать с базой данных.
    try:
        query = "SELECT 1 FROM admins WHERE chat_id = $1"# SQL-запрос для проверки администраторских прав
        result = await conn.fetchrow(query, str(user_id))
        if result:
            return True#Если результат запроса существует (не является None), то функция возвращает True,
            # что означает, что пользователь с данным user_id является администратором. В противном случае возвращается False.
        else:
            return False
    finally:
        await conn.close()


# Объявление класса Form, который содержит состояния FSM для информации о пользователе и конвертации валют
class Form(StatesGroup):
    currency_name = State()  # Определение состояния для хранения названия валюты
    currency_rate = State()  # Определение состояния для хранения курса валюты к рублю
    convert_currency_name = State()  # Определение состояния для хранения названия валюты для конвертации
    convert_currency_amount = State()  # Определение состояния для хранения суммы для конвертации
    delete_currency_name = State()  # Определение состояния для удаления названия валюты
    change_currency_name = State()  # Определение состояния для изменения названия валюты
    new_currency_rate = State()  # Определение состояния для нового курса валюты

# Обработчик команды /manage_currency для управления валютами
@dp.message_handler(commands=['manage_currency'])
async def manage_currency_command(message: types.Message):
    user_id = message.from_user.id#Здесь извлекается user_id пользователя, отправившего сообщение,
    # с помощью атрибута id объекта from_user сообщения.
    if not await is_admin(user_id):
        await message.reply("Нет доступа к команде.")
    else:
        keyboard = ReplyKeyboardMarkup(row_width=3, resize_keyboard=True)
        #Создается экземпляр ReplyKeyboardMarkup с параметрами row_width=3 (количество кнопок в ряду)
        # и resize_keyboard=True (автоматическое изменение размера клавиатуры на экране устройства).
        buttons = [
            KeyboardButton("Добавить валюту"),
            KeyboardButton("Удалить валюту"),
            KeyboardButton("Изменить курс валюты")
        ]
        keyboard.add(*buttons)#Добавление созданных кнопок в клавиатуру keyboard.
        await message.reply("Выберите действие:", reply_markup=keyboard)

# Обработчик кнопки "Добавить валюту"
@dp.message_handler(lambda message: message.text == "Добавить валюту")
async def add_currency_step1(message: types.Message): #Она отправляет ответное сообщение пользователю
    # с просьбой ввести название валюты и устанавливает состояние FSM в currency_name.
    await message.reply("Введите название валюты:")
    await Form.currency_name.set()

# Обработчик ввода названия валюты
@dp.message_handler(state=Form.currency_name)#Функция add_currency_step2 будет вызываться после ввода пользователем названия валюты.
async def add_currency_step2(message: types.Message, state: FSMContext):
    currency_name = message.text

    # Проверяем, что валюта уже существует
    if await is_currency_exists(currency_name):
        await message.reply("Данная валюта уже существует.")
        await state.finish()
        return

    await state.update_data(currency_name=currency_name)
    await message.reply("Введите курс к рублю:")
    await Form.currency_rate.set()

# Обработчик ввода курса валюты
@dp.message_handler(state=Form.currency_rate)#декоратор указывает, что функция add_currency_step3 будет вызываться,
# если пользователь находится в состоянии Form.currency_rate,
# что предполагает, что пользователь уже ввел название валюты и сейчас вводит курс этой валюты к рублю.
async def add_currency_step3(message: types.Message, state: FSMContext):
    currency_rate = float(message.text)#Получаем введенный пользователем курс валюты и преобразуем его в числовой формат.
    user_data = await state.get_data()#Получаем данные, которые были сохранены в состоянии FSM ранее.
    # В данном случае, мы извлекаем из данных название валюты.
    currency_name = user_data['currency_name']

    # Сохраняем валюту в базу данных
    await save_currency_to_db(currency_name, currency_rate)#Здесь вызывается функция save_currency_to_db,
    # которая сохраняет информацию о новой валюте (названии и курсе) в базу данных.

    await message.reply(f"Валюта {currency_name} успешно добавлена с курсом {currency_rate}")

    await state.finish()

# Функция для проверки наличия валюты в базе данных
async def is_currency_exists(currency_name):
    conn = await asyncpg.connect(database='postgres1', user='postgres', password='postgres', host='127.0.0.1', port=5432)
    try:
        query = "SELECT currency_name FROM currencies WHERE currency_name = $1"#Формируется SQL-запрос для выборки из таблицы currencies
        # только поля currency_name, где значение совпадает с переданным аргументом currency_name.
        result = await conn.fetch(query, currency_name)#Запрос выполняется с использованием метода fetch(),
        # который возвращает данные (если есть) из базы данных, соответствующие запросу.
        return bool(result)#Результат запроса преобразуется в булевое значение (True или False) с помощью функции bool().
        # Если результат не пустой, то возвращается True, что указывает на то, что валюта с таким именем существует в базе данных.
    finally:
        await conn.close()

# Функция для сохранения валюты в базу данных
async def save_currency_to_db(currency_name, currency_rate):
    conn = await asyncpg.connect(database='postgres1', user='postgres', password='postgres', host='127.0.0.1', port=5432)
    try:
        query = "INSERT INTO currencies (currency_name, rate) VALUES ($1, $2)"
        await conn.execute(query, currency_name, currency_rate)
    finally:
        await conn.close()


# Обработчик кнопки "Удалить валюту"
@dp.message_handler(lambda message: message.text == "Удалить валюту")
async def delete_currency_step1(message: types.Message):
    await message.reply("Введите название валюты, которую вы хотите удалить:")
    await Form.delete_currency_name.set()

# Обработчик ввода названия валюты для удаления
@dp.message_handler(state=Form.delete_currency_name)#Этот декоратор указывает, что функция delete_currency_step2
# будет вызываться после ввода пользователем названия валюты для удаления,
# так как пользователь находится в состоянии Form.delete_currency_name.
async def delete_currency_step2(message: types.Message, state: FSMContext):
    currency_name = message.text

    # Проверяем, что валюта существует в базе данных
    if await is_currency_exists(currency_name):
        # Удаляем валюту из базы данных
        await delete_currency_from_db(currency_name)
        await message.reply(f"Валюта {currency_name} успешно удалена.")
    else:
        await message.reply(f"Валюта {currency_name} не найдена в базе данных.")

    await state.finish()

# Функция для удаления валюты из базы данных
async def delete_currency_from_db(currency_name):
    conn = await asyncpg.connect(database='postgres1', user='postgres', password='postgres', host='127.0.0.1', port=5432)
    try:
        query = "DELETE FROM currencies WHERE currency_name = $1"#Формируется SQL-запрос,
        # который удаляет запись из таблицы currencies, где название валюты соответствует значению, переданному аргументом currency_name.
        await conn.execute(query, currency_name)#Выполняется SQL-запрос на удаление записи с указанным названием валюты из базы данных.
    finally:
        await conn.close()

# Функция для проверки наличия валюты в базе данных
async def is_currency_exists(currency_name):
    conn = await asyncpg.connect(database='postgres1', user='postgres', password='postgres', host='127.0.0.1', port=5432)
    try:
        query = "SELECT currency_name FROM currencies WHERE currency_name = $1"
        result = await conn.fetch(query, currency_name)#Запрос выполняется с использованием метода fetch(),
        # который возвращает данные (если есть) из базы данных, соответствующие запросу.
        return bool(result)#Результат запроса преобразуется в булевое значение (True или False) с помощью функции bool().
        # Если результат не пустой, то возвращается True, что указывает на то, что валюта с таким именем существует в базе данных.
    finally:
        await conn.close()

# Обработчик кнопки "Изменить курс валюты"
@dp.message_handler(lambda message: message.text == "Изменить курс валюты")
async def change_currency_step1(message: types.Message):
    await message.reply("Введите название валюты, курс которой вы хотите изменить:")
    await Form.change_currency_name.set()

# Обработчик ввода названия валюты для изменения курса
@dp.message_handler(state=Form.change_currency_name)#Функция change_currency_step2 будет вызываться после ввода пользователем названия валюты.
async def change_currency_step2(message: types.Message, state: FSMContext):
    currency_name = message.text

    # Проверяем, что валюта существует в базе данных
    if await is_currency_exists(currency_name):
        await state.update_data(currency_name=currency_name)
        await message.reply("Введите новый курс к рублю:")
        await Form.new_currency_rate.set()#Если валюта существует, данные о названии валюты обновляются в состоянии FSM,
        # пользователю отправляется запрос на ввод нового курса валюты к рублю, и состояние FSM переходит в new_currency_rate.
    else:
        await message.reply(f"Валюта {currency_name} не найдена в базе данных.")
        await state.finish()

# Обработчик ввода нового курса валюты
@dp.message_handler(state=Form.new_currency_rate)#функция change_currency_step3 будет вызываться,
# если пользователь находится в состоянии Form.new_currency_rate, что означает, что пользователь уже ввел новый курс валюты.
async def change_currency_step3(message: types.Message, state: FSMContext):
    new_currency_rate = float(message.text)#Получаем и преобразуем введенный пользователем новый курс валюты в числовой формат.
    user_data = await state.get_data()
    currency_name = user_data['currency_name']

    # Обновляем курс валюты в базе данных
    await update_currency_rate_in_db(currency_name, new_currency_rate)

    await message.reply(f"Курс валюты {currency_name} успешно изменен на {new_currency_rate}.")

    await state.finish()

# Функция для обновления курса валюты в базе данных
async def update_currency_rate_in_db(currency_name, new_currency_rate):
    conn = await asyncpg.connect(database='postgres1', user='postgres', password='postgres', host='127.0.0.1', port=5432)
    try:
        query = "UPDATE currencies SET rate = $1 WHERE currency_name = $2"
        await conn.execute(query, new_currency_rate, currency_name)#Выполняется SQL-запрос на обновление курса валюты в базе данных.
        # Первый параметр $1 в запросе заменяется на новый курс, а второй параметр $2 - на название валюты.
    finally:
        await conn.close()


# Обработчик команды /get_currencies для вывода всех сохраненных валют с курсом к рублю
@dp.message_handler(commands=['get_currencies'])
async def get_currencies_command(message: types.Message):
    conn = await asyncpg.connect(database='postgres1', user='postgres', password='postgres', host='127.0.0.1', port=5432)
    try:
        query = "SELECT currency_name, rate FROM currencies"#Формируется SQL-запрос для выбора названий валют и их курса из таблицы currencies.
        currencies = await conn.fetch(query)#Выполняется запрос к базе данных, и результаты выборки сохраняются в переменной currencies.

        if currencies:#Это условие проверяет, есть ли какие-либо результаты (валюты) в переменной currencies, полученные из базы данных.
            response = "Сохраненные валюты с курсом к рублю:\n"
            for currency in currencies:# Для каждой валюты добавляется строка в ответ, содержащая название валюты и ее курс к рублю.
                response += f"{currency['currency_name']}: {currency['rate']}\n"
        else:
            response = "Нет сохраненных валют."

        await message.reply(response)

    finally:
        await conn.close()


# Обработчик команды /start для начала работы с ботом
@dp.message_handler(commands=['start'])
async def process_start_command(message: Message):
    user_id = message.from_user.id#Получение id пользователя, отправившего сообщение,
    # из объекта from_user сообщения.Получение id пользователя, отправившего сообщение, из объекта from_user сообщения.
    commands_markup = ReplyKeyboardMarkup(resize_keyboard=True, selective=True)#Создание экземпляра ReplyKeyboardMarkup для отображения кнопок пользователю.

    if await is_admin(user_id):
        commands_markup.add(
            KeyboardButton("/start"),
            KeyboardButton("/manage_currency"),
            KeyboardButton("/get_currencies"),
            KeyboardButton("/convert")
        )
    else:
        commands_markup.add(
            KeyboardButton("/start"),
            KeyboardButton("/get_currencies"),
            KeyboardButton("/convert")
        )

    await message.reply("Выберите команду из доступных:", reply_markup=commands_markup)

# Обработчик команды /convert для начала процесса конвертации валюты
@dp.message_handler(commands=['convert'])
async def convert_currency_command(message: types.Message):
    await Form.convert_currency_name.set()  # Установка текущего состояния на ввод названия валюты для конвертации
    await message.reply("Введите название валюты, которую вы хотите конвертировать в рубли:")

# Обработка введенного названия валюты для конвертации
@dp.message_handler(state=Form.convert_currency_name)#Этот декоратор указывает,
# что функция process_convert_currency_name будет вызываться после ввода пользователем названия валюты для конвертации.
async def process_convert_currency_name(message: types.Message, state: FSMContext):
    async with state.proxy() as data:#Этот блок позволяет получить доступ к временным данным (proxy) текущего состояния
        # FSM для удобства чтения и записи информации.
        data['convert_currency_name'] = message.text#В этой строке кода введенное пользователем название валюты сохраняется
        # в переменную convert_currency_name, с помощью которой данных FSM передается название валюты для последующего
        # использования в процессе конвертации.

    await Form.convert_currency_amount.set()  # Установка состояния для ввода суммы для конвертации
    await message.reply("Теперь введите сумму в выбранной валюте для конвертации в рубли:")

# Обработка введенной суммы для конвертации
@dp.message_handler(state=Form.convert_currency_amount)#что функция process_convert_currency_amount
# будет вызвана после ввода пользователем суммы для конвертации, находясь в состоянии Form.convert_currency_amount
async def process_convert_currency_amount(message: types.Message, state: FSMContext):
    async with state.proxy() as data:#Блок позволяет получить доступ к временным данным (proxy)
        # текущего состояния FSM для удобства чтения и записи информации.
        convert_currency_name = data['convert_currency_name']#Извлекается из состояния FSM
        # ранее сохраненное пользовательское название валюты для конвертации.
        convert_currency_amount = float(message.text)#Полученная от пользователя сумма для конвертации преобразуется в числовой тип (float).

        # Получаем курс выбранной валюты из базы данных
        currency_rate = await get_currency_rate(convert_currency_name)

        if currency_rate is not None:
            converted_amount = convert_currency_amount * currency_rate
            await message.reply(f"{convert_currency_amount} {convert_currency_name} равно {converted_amount} рублей.")
        else:
            await message.reply(f"Извините, курс для валюты {convert_currency_name} не найден в базе данных.")

        await state.finish()

# Функция для получения курса валюты из базы данных
async def get_currency_rate(currency_name):
    conn = await asyncpg.connect(database='postgres1', user='postgres', password='postgres', host='127.0.0.1', port=5432)
    try:
        query = "SELECT rate FROM currencies WHERE currency_name = $1"# Формируется SQL-запрос,
        # который выбирает значение курса из таблицы currencies для указанной валюты.
        rate = await conn.fetchval(query, currency_name)#Запрос выполняется с использованием метода fetchval(),
        # который возвращает единственное значение из запроса. Здесь получаем курс валюты currency_name.
        return rate#Возвращается полученное значение курса валюты. Если курс был найден в базе данных, то он будет возвращен из функции.
    finally:
        await conn.close()

# Точка входа в приложение, запуск обработки сообщений
if __name__ == '__main__':#Эта конструкция проверяет, что скрипт был запущен как основной программой, а не импортирован как модуль.
    # Таким образом, все, что находится внутри этого блока, будет выполнено при запуске скрипта напрямую.

    # Инициализация системы логирования с уровнем INFO
    logging.basicConfig(level=logging.INFO)#Эта строка устанавливает конфигурацию для системы логирования.
    # Уровень логгирования установлен на INFO, что означает, что будут записываться логи информационного уровня и более критических

    # Подключение системы логирования к диспетчеру бота
    dp.middleware.setup(LoggingMiddleware())#Этот код добавляет middleware (промежуточное программное обеспечение)
    # LoggingMiddleware() к диспетчеру dp вашего бота. Это позволяет логировать различные события и действия,
    # происходящие при обработке сообщений ботом.

    # Запуск обработки входящих сообщений бота
    executor.start_polling(dp, skip_updates=True)#Этот код запускает процесс получения новых входящих сообщений
    # и запускает обработчики сообщений. executor.start_polling(dp) запускает процесс "прослушивания" сообщений,
    # а параметр skip_updates=True означает, что бот пропускает уже полученные обновления, избегая их повторной обработки при перезапуске.
    #При использовании polling  бот регулярно отправляет запросы к серверам Telegram, чтобы проверить наличие новых событий

