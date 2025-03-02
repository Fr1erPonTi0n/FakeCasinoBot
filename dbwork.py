import sqlite3
import random

# Функция работы с базой данных
def execute_db_query(query, params=(), fetchone=False, fetchall=False, commit=False):
    con = sqlite3.connect('tgbase.db')
    cur = con.cursor()
    cur.execute(query, params)
    result = cur.fetchone() if fetchone else cur.fetchall() if fetchall else None
    if commit:
        con.commit()
    con.close()
    return result

# Функция добавления пользователя в базу данных
def add_user(telegram_id):
    existing_user = execute_db_query("SELECT * FROM base WHERE telegram_id = ?", (telegram_id,), fetchone=True)
    if existing_user:
        return False
    execute_db_query('INSERT INTO base (telegram_id) VALUES (?)', (telegram_id,), commit=True)
    return True

# Функция работы казино
def casino(telegram_id, money, mention):
    user = execute_db_query("SELECT * FROM base WHERE telegram_id = ?", (telegram_id,), fetchone=True)
    if not user:
        return f'❌ {mention} не найден. Зарегистрируйтесь с помощью команды /start.'

    current_money = user[2]
    if current_money < money:
        return f'❌ {mention} у тебя недостаточно средств для игры!'

    result = random.choices(['win', 'lose'], weights=[0.3, 0.7], k=1)[0]
    if result == 'win':
        multiplier = random.uniform(0.1, 1.5)
        winnings = round(int(money * multiplier) / 10) * 10
        new_money = current_money + winnings
        message = f'💸 {mention} выиграл(а)! Ваш выигрыш: {winnings}. Новый баланс: {new_money}.'
    else:
        new_money = current_money - money
        message = f'🗑️ {mention} проиграл(а). Потеряно: {money}. Новый баланс: {new_money}.'

    execute_db_query("UPDATE base SET count_money = ?, count_game = count_game + 1 WHERE telegram_id = ?",
                     (new_money, telegram_id), commit=True)
    return message

# Функция получения денег
def free_money(telegram_id, mention):
    user = execute_db_query("SELECT * FROM base WHERE telegram_id = ?", (telegram_id,), fetchone=True)
    if not user:
        return f'❌ {mention} не найден. Зарегистрируйтесь с помощью команды /start.'

    new_money = user[2] + 500
    execute_db_query("UPDATE base SET count_money = ?, count_game = count_game + 1 WHERE telegram_id = ?",
                     (new_money, telegram_id), commit=True)
    return f"❤️ У {mention} был пополнен баланс!"

# Функция получения статистики пользователя
def get_user_stats(telegram_id):
    user = execute_db_query("SELECT * FROM base WHERE telegram_id = ?", (telegram_id,), fetchone=True)
    return (user[2], user[3]) if user else False

# Функция получения топ-5 пользователей
def get_leaderboard():
    leaders = execute_db_query("""
        SELECT telegram_id, count_money, count_game
        FROM base
        ORDER BY count_game DESC, count_money DESC
        LIMIT 5
    """, fetchall=True)
    return [(index, *leader) for index, leader in enumerate(leaders, start=1)]