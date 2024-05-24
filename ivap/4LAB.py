from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.utils import executor

import os
import logging

# Настраиваем уровень логирования
# INFO - Уровень информации, используется для записи общей информации о системе или выполнении программы.
logging.basicConfig(level=logging.INFO)
# Получаем токен бота из переменной окружения
bot_token = os.getenv('API_BOT_TOKEN')
# Создаем экземпляр и присваеваем токен (сам бот)
bot = Bot(token=bot_token)
# Dispatcher обработка и маршрутизация входящих сообщений
# MemoryStorage класс, предоставляющий хранилище для состояний бота
dp = Dispatcher(bot, storage=MemoryStorage())
# Создание пустого списка, для дальнейшего заполнения валютой и курсом
currency_dict = {}
# SaveCurrencyState подкласс StatesGroup
class SaveCurrencyState(StatesGroup):
    # Состояния в нашем боте
    currency_name = State()
    currency_rate = State()

    currency_name2 = State()
    currency_rate2 = State()
# Обработчик команды /start (декоратор)
# types.Message - Входящее сообщение от пользователя
@dp.message_handler(commands=['start'])
async def process_start_name(message: types.Message):
    # await позволяет ассихронно отправлять сообщения, не блокируя выполнение других задач
    # (выполнение программы будет приостановлено до тех пор, пока не будет получен ответ на это сообщение)
    # reply - для ответа на конкретное сообщение пользователя и продолжения диалога
    await message.reply("Привет, я самый крутой бот в телеграме!\n"
                        "У меня есть три команды:\n"
                        "/save_currency - Сохранение вашей валюты и курса\n"
                        "/list_currencies - Просмотр списока записаных вами валют и курсов\n"
                        "/convert - Расчёт вашей валюты на рубли")

@dp.message_handler(commands=['save_currency'])
async def save_currency_command(message: types.Message):
    # .answer() -  для отправки самостоятельных ответов или уведомлений
    await message.answer("Введите название валюты:")
    # Переход к состоянию
    await SaveCurrencyState.currency_name.set()
# state - Указываем какое это состояние (Для перехода в него)
@dp.message_handler(state=SaveCurrencyState.currency_name)
# FSM - конечный автомат (Управление состояниями бота и обрабатывать входящие сообщения в зависимости от
# текущего состояния)
async def save_currency_name(message: types.Message, state: FSMContext):
    # создаем асинхронный контекстный менеджер с прокси-объектом для state
    async with state.proxy() as data:
        #
        data['currency_name'] = message.text
    await message.answer(f"Введите курс валюты {message.text} к рублю:")
    await SaveCurrencyState.currency_rate.set()

@dp.message_handler(state=SaveCurrencyState.currency_rate)
async def save_currency_rate(message: types.Message, state: FSMContext):
    # Обработка исключений
    try:
        currency_rate = float(message.text)
        async with state.proxy() as data:
            data['currency_rate'] = currency_rate
            currency_dict[data['currency_name']] = currency_rate
        await message.answer(f"Курс валюты {data['currency_name']} успешно сохранен.")
    except ValueError:
        await message.answer("Некорректный формат курса. Пожалуйста, введите число.")
    finally:
        await state.finish()

@dp.message_handler(commands=['list_currencies'])
async def list_currencies_command(message: types.Message):
    if currency_dict:
        currencies_list = "\n".join([f"{currency}: {rate}" for currency, rate in currency_dict.items()])
        await message.answer("Список сохраненных валют и их курсов к рублю:\n" + currencies_list)
    else:
        await message.answer("Список сохраненных валют пуст.")


@dp.message_handler(commands=['convert'])
async def convert_currency_command(message: types.Message):
    await message.answer("Введите название валюты для конвертации:")
    await SaveCurrencyState.currency_name2.set()

@dp.message_handler(state=SaveCurrencyState.currency_name2)
async def convert_currency_name(message: types.Message, state: FSMContext):
    currency_name = message.text
    # Проверка на наличие в списке указанной валюты
    if currency_name in currency_dict:
        async with state.proxy() as data:
            data['currency_name'] = currency_name
        await message.answer(f"Введите сумму в {currency_name}:")
        await SaveCurrencyState.currency_rate2.set()
    else:
        await message.answer(f"Валюта {currency_name} не найдена в списке сохраненных.")

@dp.message_handler(state=SaveCurrencyState.currency_rate2)
async def convert_currency_rate(message: types.Message, state: FSMContext):
    try:
        amount = float(message.text)
        async with state.proxy() as data:
            rate = currency_dict[data['currency_name']]
            converted_amount = amount * rate
        await message.answer(f"{amount} {data['currency_name']} равно {converted_amount} рублей.")
    except ValueError:
        await message.answer("Некорректный формат суммы. Пожалуйста, введите число.")
    finally:
        await state.finish()


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)