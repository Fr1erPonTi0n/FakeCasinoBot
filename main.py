import configparser, logging, time
import dbwork
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command

# Чтение конфигурационного файла
config = configparser.ConfigParser()
config.read('config.ini')

# Получение токена из конфига
API_TOKEN = config['Telegram']['API_TOKEN']
COOLDOWN_TIME_CASINO = int(config['Telegram']['COOLDOWN_TIME_CASINO'])
COOLDOWN_TIME_FREE_MONEY = int(config['Telegram']['COOLDOWN_TIME_FREE_MONEY'])

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Словарь для хранения времени последнего вызова команды
user_cooldowns = {}

# Инициализация бота и диспетчера
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# Списки для объявления команд
CASINO_COMMANDS = {'каз', 'КАЗ', 'Каз', 'кази', 'КАЗИ', 'Кази', 'казин', 'КАЗИН', 'Казин', 'казино', 'КАЗИНО', 'Казино'}

# Белый список для чатов и пользователей
WHITE_LIST_CHATS = list(map(int, config['Telegram']['WHITE_LIST_CHATS'].split(', ')))
WHITE_LIST_USERS = list(map(int, config['Telegram']['WHITE_LIST_USERS'].split(', ')))

# Функция для проверки, находится ли чат в белом списке
def is_chat_allowed(chat_id: int, user_id: int = None) -> bool | None:
    # Проверяем, находится ли чат в белом списке
    if chat_id in WHITE_LIST_CHATS:
        return True
    # Проверяем, находится ли пользователь в белом списке
    if user_id and user_id in WHITE_LIST_USERS:
        return True

# Обработчик команды /help
@dp.message(Command("help"))
async def on_help(message: types.Message):
    if not is_chat_allowed(message.chat.id, message.from_user.id):
        return
    help_text = (
        "📄 Какие команды есть у бота?\n\n"
        "- /start : Для начала работы этого бота\n"
        "- /help : Инструкция по командам\n"
        "- /stats : Выводит вашу статистику\n"
        "- /top : Выводит топ людей в лудомании\n"
        "- /free : Бесплатные монеты для лудомании\n"
        "- каз <число> : Быть лудоманом на 5 секунд, ставка от 50 денег"
    )
    await message.reply(help_text)

# Обработчик команды /start
@dp.message(Command("start"))
async def on_start(message: types.Message):
    if not is_chat_allowed(message.chat.id, message.from_user.id):
        return
    user_id, user_name = message.from_user.id, message.from_user.full_name
    mention = f'<a href="tg://user?id={user_id}">{user_name}</a>'
    await message.answer(f"🌈 Привет, {mention}!", parse_mode="HTML")
    if dbwork.add_user(user_id):
        await message.answer('✅ Вы успешно зарегистрировались!')
    else:
        await message.answer("❗ Ты уже были зарегистрированы!")

# Обработчик команды /free
@dp.message(Command("free"))
async def on_free(message: types.Message):
    if not is_chat_allowed(message.chat.id, message.from_user.id):
        return
    user_id = message.from_user.id
    if user_id in user_cooldowns and time.time() - user_cooldowns[user_id] < COOLDOWN_TIME_FREE_MONEY:
        remaining_time = int(COOLDOWN_TIME_FREE_MONEY - (time.time() - user_cooldowns[user_id]))
        await message.reply(f"🕑 Подождите {remaining_time} секунд перед следующим пополнением.")
        return
    user_cooldowns[user_id] = time.time()
    mention = f'<a href="tg://user?id={user_id}">{message.from_user.full_name}</a>'
    await message.answer(dbwork.free_money(user_id, mention), parse_mode="HTML")

# Обработчик команды /stats
@dp.message(Command("stats"))
async def on_stats(message: types.Message):
    if not is_chat_allowed(message.chat.id, message.from_user.id):
        return
    user_id = message.from_user.id
    mention = f'<a href="tg://user?id={user_id}">{message.from_user.full_name}</a>'
    stats = dbwork.get_user_stats(user_id)
    if stats:
        await message.answer(
            f"📃 Статистика пользователя {mention}:\n"
            f"💰 Баланс: {stats[0]} монет\n"
            f"🎰 Количество игр: {stats[1]}", parse_mode="HTML")
    else:
        await message.answer(f'❌ {mention} не найден. Зарегистрируйтесь с помощью команды /start.', parse_mode="HTML")

# Обработчик команды /top
@dp.message(Command("top"))
async def on_top(message: types.Message):
    if not is_chat_allowed(message.chat.id, message.from_user.id):
        return
    leaderboard = dbwork.get_leaderboard()
    if not leaderboard:
        await message.answer("❌ Таблица лидеров пуста.")
        return
    leaderboard_message = "🏆 Топ-5 игроков:\n\n"
    for index, telegram_id, count_money, count_game in leaderboard:
        user = await bot.get_chat(telegram_id)
        mention = f'<a href="tg://user?id={telegram_id}">{user.full_name}</a>'
        leaderboard_message += (
            f"{index}. {mention}:\n"
            f"🎮 Игр сыграно: {count_game}\n"
            f"💰 Баланс: {count_money} монет\n\n"
        )
    await message.answer(leaderboard_message, parse_mode="HTML")

# Обработчик команды казино
@dp.message(lambda message: message.text and message.text.split()[0].lower() in CASINO_COMMANDS)
async def on_casino(message: types.Message):
    if not is_chat_allowed(message.chat.id, message.from_user.id):
        return
    user_id = message.from_user.id
    parts = message.text.split()
    if len(parts) < 2:
        await message.reply("❌ Ошибка! Укажите сумму для ставки. Например: каз 100")
        return
    try:
        amount = int(parts[1])
        if amount <= 50:
            await message.reply("❌ Ошибка! Сумма должна быть больше 50.")
            return
    except ValueError:
        await message.reply("❌ Ошибка! Сумма должна быть числом.")
        return
    if user_id in user_cooldowns and time.time() - user_cooldowns[user_id] < COOLDOWN_TIME_CASINO:
        remaining_time = int(COOLDOWN_TIME_CASINO - (time.time() - user_cooldowns[user_id]))
        await message.reply(f"🕑 Подождите {remaining_time} секунд перед следующей ставкой.")
        return
    user_cooldowns[user_id] = time.time()
    mention = f'<a href="tg://user?id={user_id}">{message.from_user.full_name}</a>'
    await message.reply(dbwork.casino(user_id, amount, mention), parse_mode="HTML")

# Запуск бота
if __name__ == '__main__':
    dp.run_polling(bot)
