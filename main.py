import sqlite3
import os
import datetime
import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton

TOKEN = "*" * Замените на unique bot token from botfather
ADMIN_USER_ID = #  # Замените на свой числовой user_id
bot = telebot.TeleBot(TOKEN)

# Инициализация базы данных
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "data", "survey_data.db")
os.makedirs(os.path.join(BASE_DIR, "data"), exist_ok=True)

conn = sqlite3.connect(DB_PATH, check_same_thread=False)
cursor = conn.cursor()

# Создание таблицы в базе данных
cursor.execute('''
CREATE TABLE IF NOT EXISTS responses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    username TEXT,
    experience TEXT,
    education TEXT,
    motivation TEXT,
    start_time TEXT,
    end_time TEXT,
    analysis TEXT
)
''')
conn.commit()

# Константы состояния
STATE_WAITING_FOR_EXPERIENCE = "waiting_for_experience"
STATE_WAITING_FOR_EDUCATION = "waiting_for_education"
STATE_WAITING_FOR_MOTIVATION = "waiting_for_motivation"

# Словари для отслеживания состояния пользователей
user_states = {}
user_start_time = {}
user_answers = {}  # Отслеживание ответов

# Функции для анализа данных кандидатов
def analyze_experience(experience):
    analysis = []
    if experience is None:
        analysis.append("🔰 Информация о вашем опыте не была предоставлена.")
    elif any(keyword in experience.lower() for keyword in ['нет опыта', 'без опыта', 'новичок']):
        analysis.append("🔰 Это может быть вашим первым шагом в профессиональной карьере. Главное желание развиваться!")
    elif any(keyword in experience.lower() for keyword in ['2-5 лет', 'средний опыт', 'некоторые годы']):
        analysis.append("💼 Отлично! У вас есть опыт, который поможет в новой работе.")
    elif any(keyword in experience.lower() for keyword in ['5+ лет', 'опытный', 'эксперт']):
        analysis.append("🚀 Прекрасно! Вы обладаете богатым опытом, подходящим для более сложных задач.")
    else:
        analysis.append("🤔 Ответ не совсем ясен, но мы всегда готовы понять вас лучше!")
    return analysis

def analyze_education(education):
    analysis = []
    if education is None:
        analysis.append("🎓 Информация о вашем образовании не была предоставлена.")
    elif any(keyword in education.lower() for keyword in ['среднее', 'неоконченное', 'без образования']):
        analysis.append("🎓 На данный момент не хватает образования, но важно стремиться к обучению!")
    elif any(keyword in education.lower() for keyword in ['высшее', 'бакалавр', 'магистр']):
        analysis.append("🎓 Ваш уровень образования дает вам отличные перспективы для карьерного роста.")
    else:
        analysis.append("🧐 Мы не уверены в вашем уровне образования, но уверены, что обучаемся всегда.")
    return analysis

def analyze_motivation(motivation):
    analysis = []
    if motivation is None:
        analysis.append("💭 Информация о вашей мотивации не была предоставлена.")
    elif any(keyword in motivation.lower() for keyword in ['карьера', 'развитие', 'рост']):
        analysis.append("🌱 Вы мотивированы развиваться и расти, что очень ценно для нашей компании!")
    elif any(keyword in motivation.lower() for keyword in ['деньги', 'зарплата']):
        analysis.append("💸 Важно, чтобы ваша мотивация сочеталась с карьерными перспективами.")
    elif any(keyword in motivation.lower() for keyword in ['команда', 'общение']):
        analysis.append("👥 Вы цените команду, и это важное качество для успешной работы в коллективе.")
    else:
        analysis.append("🤔 Мы не совсем уверены в вашей мотивации, давайте уточним!")
    return analysis

def analyze_candidate(experience, education, motivation):
    experience_analysis = analyze_experience(experience)
    education_analysis = analyze_education(education)
    motivation_analysis = analyze_motivation(motivation)

    full_analysis = (
        "🧠 **Анализ кандидата:**\n\n"
        f"**Опыт работы:**\n" + "\n".join(experience_analysis) + "\n\n"
        f"**Образование:**\n" + "\n".join(education_analysis) + "\n\n"
        f"**Мотивация:**\n" + "\n".join(motivation_analysis)
    )
    return full_analysis

def main_menu_keyboard(is_admin):
    markup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False)
    markup.add(KeyboardButton("ℹ️ Информация"))
    markup.add(KeyboardButton("📝 Пройти опрос"))
    if is_admin:
        markup.add(KeyboardButton("📊 Просмотреть ответы"))
        markup.add(KeyboardButton("🗑 Удалить ответ"))
    return markup

@bot.message_handler(commands=["start"])
def handle_start(message):
    username = message.from_user.username or "Unknown"
    is_admin = (message.from_user.id == ADMIN_USER_ID)
    bot.send_message(
        message.chat.id,
        "👋 Добро пожаловать в бота для оценки кандидатов! Пожалуйста, выберите действие.",
        reply_markup=main_menu_keyboard(is_admin)
    )

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    user_id = message.from_user.id
    is_admin = (user_id == ADMIN_USER_ID)

    # Если пользователь выбрал "Информация"
    if message.text == "ℹ️ Информация":
        bot.send_message(
            message.chat.id,
            "Этот бот создан для оценки кандидатов на работу. "
            "Нажмите '📝 Пройти опрос', чтобы начать процесс."
        )
        return

    # Если пользователь выбрал "Пройти опрос"
    if message.text == "📝 Пройти опрос":
        user_states[user_id] = STATE_WAITING_FOR_EXPERIENCE
        user_start_time[user_id] = datetime.datetime.now()
        user_answers[user_id] = {'experience': None, 'education': None, 'motivation': None}
        bot.send_message(user_id, "❓ Вопрос 1: Опыт работы в сфере (например, нет, 2-5 лет, 5+ лет)?")
        return

    state = user_states.get(user_id)

    if state == STATE_WAITING_FOR_EXPERIENCE:
        user_answers[user_id]['experience'] = message.text
        cursor.execute(
            "INSERT INTO responses (user_id, username, experience, start_time) VALUES (?, ?, ?, ?)",
            (user_id, message.from_user.username, message.text, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        )
        conn.commit()
        user_states[user_id] = STATE_WAITING_FOR_EDUCATION
        bot.send_message(user_id, "❓ Вопрос 2: Какое у вас образование (например, среднее, высшее)?")
    elif state == STATE_WAITING_FOR_EDUCATION:
        user_answers[user_id]['education'] = message.text
        cursor.execute(
            "UPDATE responses SET education = ? WHERE user_id = ? AND education IS NULL",
            (message.text, user_id)
        )
        conn.commit()
        user_states[user_id] = STATE_WAITING_FOR_MOTIVATION
        bot.send_message(user_id, "❓ Вопрос 3: Какая ваша мотивация работать здесь? (например, деньги, карьерный рост, обучение)")

    elif state == STATE_WAITING_FOR_MOTIVATION:
        user_answers[user_id]['motivation'] = message.text
        end_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute(
            "UPDATE responses SET motivation = ?, end_time = ? WHERE user_id = ? AND motivation IS NULL",
            (message.text, end_time, user_id)
        )
        conn.commit()

        # Выполнение анализа
        analysis = analyze_candidate(
            user_answers[user_id]['experience'],
            user_answers[user_id]['education'],
            user_answers[user_id]['motivation']
        )

        cursor.execute(
            "UPDATE responses SET analysis = ? WHERE user_id = ?",
            (analysis, user_id)
        )
        conn.commit()

        user_states.pop(user_id, None)
        bot.send_message(user_id, "🎉 Спасибо за участие в опросе! Ваши ответы скоро будут проанализированы.")

    # Функции админа: Просмотр и удаление
    if is_admin:
        if message.text == "📊 Просмотреть ответы":
            cursor.execute("SELECT id, username, experience, education, motivation, start_time, end_time, analysis FROM responses")
            rows = cursor.fetchall()
            if rows:
                response = "📋 Собранные данные:\n"
                for row in rows:
                    response += (
                        f"ID: {row[0]}\n@{row[1]}\nОпыт: {row[2]}\nОбразование: {row[3]}\nМотивация: {row[4]}\n"
                        f"Время: {row[5]} - {row[6]}\nАнализ: {row[7]}\n\n"
                    )
                bot.send_message(user_id, response)
            else:
                bot.send_message(user_id, "💡 Нет данных для отображения.")
            return

        if message.text == "🗑 Удалить ответ":
            cursor.execute("SELECT id, username FROM responses")
            rows = cursor.fetchall()
            if rows:
                response = "📋 Список ID для удаления:\n"
                for row in rows:
                    response += f"ID: {row[0]} — @{row[1]} ⬇️\n"
                response += "Введите ID записи для удаления."
                bot.send_message(user_id, response)
            else:
                bot.send_message(user_id, "💡 Нет записей для удаления.")
            user_states[user_id] = "awaiting_record_id_for_deletion"
            return

    # Удаление записи
    if user_states.get(user_id) == "awaiting_record_id_for_deletion":
        if message.text.isdigit():
            record_id = int(message.text)
            cursor.execute("DELETE FROM responses WHERE id = ?", (record_id,))
            conn.commit()
            bot.send_message(ADMIN_USER_ID, f"Запись с ID {record_id} была удалена. ✅")
        else:
            bot.send_message(user_id, "❌ Ошибка: Пожалуйста, введите правильный ID записи для удаления.")
        user_states[user_id] = None

# Запуск бота
if __name__ == "__main__":
    print("Bot is running...")
    bot.polling(none_stop=True)
