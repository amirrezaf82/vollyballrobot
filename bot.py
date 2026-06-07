import telebot
from telebot import types
import json
import os
import re
import threading
from flask import Flask

# ============= تنظیمات اولیه =============
TOKEN = "8900728767:AAG9Gq4nDE0gI9p6D9wxWfBw2IGRqvuNt38"
ADMIN_PASSWORD = "123412345"
DATA_FILE = "volleyball_data.json"

# ایجاد اپلیکیشن Flask برای health check
app = Flask(__name__)

bot = telebot.TeleBot(TOKEN)

# دیکشنری برای ذخیره اطلاعات موقت
temp_new_game = {}
temp_admin_action = {}
temp_edit_game = {}

# ============= مدیریت فایل اطلاعات =============
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {
        'users': {},
        'games': [],
        'next_game_id': 1
    }

def save_data(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ============= ساخت منوی اصلی =============
def main_menu_markup():
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    btn1 = types.KeyboardButton("🏐 رزرو بازی جدید")
    btn2 = types.KeyboardButton("📋 بازی‌های رزرو شده من")
    btn3 = types.KeyboardButton("📅 مشاهده تمام بازی‌ها")
    btn4 = types.KeyboardButton("👑 پنل مدیر")
    markup.add(btn1, btn2, btn3, btn4)
    return markup

def back_button():
    markup = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
    markup.add(types.KeyboardButton("🔙 بازگشت به منوی اصلی"))
    return markup

def admin_menu_markup():
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    btn1 = types.KeyboardButton("➕ ایجاد بازی جدید")
    btn2 = types.KeyboardButton("🎮 مدیریت بازی‌ها")
    btn3 = types.KeyboardButton("✏️ مدیریت بازیکنان")
    btn4 = types.KeyboardButton("📊 گزارش کامل بازی‌ها")
    btn5 = types.KeyboardButton("🔙 بازگشت به منوی اصلی")
    markup.add(btn1, btn2, btn3, btn4, btn5)
    return markup

def manage_players_menu():
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("➕ اضافه کردن بازیکن به بازی", callback_data="admin_add_player"),
        types.InlineKeyboardButton("❌ حذف بازیکن از بازی", callback_data="admin_remove_player"),
        types.InlineKeyboardButton("🔙 بازگشت", callback_data="admin_back_to_menu")
    )
    return markup

def manage_games_menu():
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("✏️ ویرایش بازی", callback_data="admin_edit_game"),
        types.InlineKeyboardButton("🗑️ حذف بازی", callback_data="admin_delete_game"),
        types.InlineKeyboardButton("🔙 بازگشت", callback_data="admin_back_to_menu")
    )
    return markup

# ============= دستور start =============
@bot.message_handler(commands=['start'])
def start(message):
    user_id = str(message.from_user.id)
    data = load_data()
    
    if user_id not in data['users']:
        msg = bot.reply_to(message, 
            "🏐 به ربات هماهنگی والیبال خوش آمدی!\n\n"
            "لطفاً نام و نام خانوادگی خود را وارد کنید:",
            reply_markup=types.ReplyKeyboardRemove())
        bot.register_next_step_handler(msg, save_user_name)
    else:
        bot.reply_to(message, 
            f"سلام {data['users'][user_id]['name']}!\n"
            "به ربات هماهنگی والیبال خوش آمدی.\n"
            "لطفاً یکی از گزینه‌های زیر را انتخاب کن:",
            reply_markup=main_menu_markup())

def save_user_name(message):
    user_id = str(message.from_user.id)
    user_name = message.text.strip()
    
    data = load_data()
    data['users'][user_id] = {
        'name': user_name,
        'username': message.from_user.username
    }
    save_data(data)
    
    bot.reply_to(message,
        f"✅ نام شما {user_name} ذخیره شد!\n"
        "به منوی اصلی خوش آمدید:",
        reply_markup=main_menu_markup())

@bot.message_handler(func=lambda message: message.text == "🔙 بازگشت به منوی اصلی")
def back_to_main(message):
    bot.reply_to(message, "به منوی اصلی بازگشتید:", reply_markup=main_menu_markup())

# ============= گزینه 1: رزرو بازی جدید =============
@bot.message_handler(func=lambda message: message.text == "🏐 رزرو بازی جدید")
def show_available_games(message):
    data = load_data()
    
    if not data['games']:
        bot.reply_to(message, "❌ هیچ بازی فعالی وجود ندارد.\nبا مدیر تماس بگیرید.", reply_markup=back_button())
        return
    
    for game in data['games']:
        players_count = len(game['players'])
        available = game['capacity'] - players_count
        
        markup = types.InlineKeyboardMarkup()
        if available > 0:
            btn = types.InlineKeyboardButton(f"🎯 رزرو این بازی (ظرفیت خالی: {available})", callback_data=f"reserve_{game['id']}")
            markup.add(btn)
        
        game_text = (
            f"🎮 **بازی شماره {game['id']}**\n"
            f"📅 تاریخ: {game['date']}\n"
            f"⏰ ساعت: {game['time']}\n"
            f"📍 مکان: {game['location']}\n"
            f"👥 تعداد عضو شده: {players_count} نفر\n"
            f"✅ ظرفیت خالی: {available} نفر\n"
            f"💰 هزینه: {game['cost_per_person']:,} تومان"
        )
        
        bot.send_message(message.chat.id, game_text, parse_mode='Markdown', reply_markup=markup if available > 0 else None)
    
    bot.send_message(message.chat.id, "برای رزرو، روی دکمه زیر بازی مورد نظر کلیک کن:", reply_markup=back_button())

@bot.callback_query_handler(func=lambda call: call.data.startswith('reserve_'))
def reserve_game(call):
    game_id = int(call.data.split('_')[1])
    user_id = str(call.from_user.id)
    
    data = load_data()
    
    target_game = None
    for game in data['games']:
        if game['id'] == game_id:
            target_game = game
            break
    
    if not target_game:
        bot.answer_callback_query(call.id, "❌ این بازی دیگر وجود ندارد!")
        return
    
    if len(target_game['players']) >= target_game['capacity']:
        bot.answer_callback_query(call.id, "❌ ظرفیت این بازی پر شده است!")
        return
    
    if user_id in target_game['players']:
        bot.answer_callback_query(call.id, "⚠️ شما قبلاً برای این بازی ثبت نام کرده‌اید!")
        return
    
    user_name = data['users'][user_id]['name']
    
    if 'temp_reserve' not in data:
        data['temp_reserve'] = {}
    data['temp_reserve'][user_id] = {'game_id': game_id}
    save_data(data)
    
    bot.send_message(call.message.chat.id,
        f"🏧 **اطلاعات واریز**\n\n"
        f"{user_name} عزیز، لطفاً مبلغ {target_game['cost_per_person']:,} تومان را به شماره کارت زیر واریز کنید:\n\n"
        f"`6037-9975-1234-5678`\n\n"
        f"سپس **یک عکس از فیش واریزی** را برای من ارسال کنید.\n\n"
        f"⚠️ توجه: فقط بعد از ارسال عکس، رزرو شما ثبت می‌شود.",
        parse_mode='Markdown')
    
    bot.register_next_step_handler(call.message, process_payment)

def process_payment(message):
    user_id = str(message.from_user.id)
    data = load_data()
    
    temp = data.get('temp_reserve', {})
    if user_id not in temp:
        bot.reply_to(message, "❌ مشکلی پیش آمد! لطفاً دوباره از منوی اصلی اقدام کن.", reply_markup=main_menu_markup())
        return
    
    game_id = temp[user_id]['game_id']
    
    if message.photo:
        photo_id = message.photo[-1].file_id
        
        target_game = None
        for game in data['games']:
            if game['id'] == game_id:
                target_game = game
                break
        
        if target_game and user_id not in target_game['players']:
            target_game['players'].append(user_id)
            
            if 'payment_proofs' not in target_game:
                target_game['payment_proofs'] = {}
            target_game['payment_proofs'][user_id] = photo_id
            
            del data['temp_reserve'][user_id]
            save_data(data)
            
            user_name = data['users'][user_id]['name']
            bot.reply_to(message,
                f"✅ {user_name} عزیز، رزرو شما با موفقیت ثبت شد!\n"
                f"بازی شماره {game_id} - تاریخ {target_game['date']}",
                reply_markup=main_menu_markup())
        else:
            bot.reply_to(message, "❌ مشکلی پیش آمد!", reply_markup=main_menu_markup())
    else:
        bot.reply_to(message, "❌ لطفاً یک عکس از فیش واریزی ارسال کنید.", reply_markup=back_button())
        bot.register_next_step_handler(message, process_payment)

# ============= گزینه 2: بازی‌های رزرو شده من =============
@bot.message_handler(func=lambda message: message.text == "📋 بازی‌های رزرو شده من")
def my_reservations(message):
    user_id = str(message.from_user.id)
    data = load_data()
    
    user_games = []
    for game in data['games']:
        if user_id in game['players']:
            user_games.append(game)
    
    if not user_games:
        bot.reply_to(message, "📭 شما هنوز در هیچ بازی‌ای ثبت نام نکرده‌اید.", reply_markup=back_button())
        return
    
    for game in user_games:
        game_text = (
            f"🎮 **بازی شماره {game['id']}**\n"
            f"📅 تاریخ: {game['date']}\n"
            f"⏰ ساعت: {game['time']}\n"
            f"📍 مکان: {game['location']}\n"
            f"💰 مبلغ پرداختی: {game['cost_per_person']:,} تومان"
        )
        bot.send_message(message.chat.id, game_text, parse_mode='Markdown')
    
    bot.send_message(message.chat.id, "این بازی‌ها توسط شما رزرو شده‌اند.", reply_markup=back_button())

# ============= گزینه 3: مشاهده تمام بازی‌ها =============
@bot.message_handler(func=lambda message: message.text == "📅 مشاهده تمام بازی‌ها")
def view_all_games(message):
    data = load_data()
    
    if not data['games']:
        bot.reply_to(message, "📭 هیچ بازی فعالی وجود ندارد.", reply_markup=back_button())
        return
    
    for game in data['games']:
        players_count = len(game['players'])
        available = game['capacity'] - players_count
        
        game_text = (
            f"🎮 **بازی شماره {game['id']}**\n"
            f"📅 تاریخ: {game['date']}\n"
            f"⏰ ساعت: {game['time']}\n"
            f"📍 مکان: {game['location']}\n"
            f"👥 تعداد حاضرین: {players_count} نفر\n"
            f"✅ ظرفیت خالی: {available} نفر\n"
            f"💰 هزینه هر نفر: {game['cost_per_person']:,} تومان"
        )
        bot.send_message(message.chat.id, game_text, parse_mode='Markdown')
    
    bot.send_message(message.chat.id, "لیست کامل بازی‌ها:", reply_markup=back_button())

# ============= گزینه 4: پنل مدیر =============
@bot.message_handler(func=lambda message: message.text == "👑 پنل مدیر")
def admin_panel(message):
    msg = bot.reply_to(message, "🔐 لطفاً رمز عبور مدیر را وارد کنید:", reply_markup=types.ReplyKeyboardRemove())
    bot.register_next_step_handler(msg, check_admin_password)

def check_admin_password(message):
    if message.text == ADMIN_PASSWORD:
        bot.reply_to(message, "👑 به پنل مدیریت خوش آمدید.", reply_markup=admin_menu_markup())
    else:
        bot.reply_to(message, "❌ رمز عبور اشتباه است!", reply_markup=main_menu_markup())

# ============= ایجاد بازی جدید مرحله به مرحله =============
@bot.message_handler(func=lambda message: message.text == "➕ ایجاد بازی جدید")
def start_create_game(message):
    user_id = message.from_user.id
    temp_new_game[user_id] = {}
    
    msg = bot.reply_to(message, 
        "📅 **مرحله 1 از 5:**\n\nلطفاً **تاریخ برگزاری بازی** را وارد کنید.\nمثال: 1403/04/20",
        parse_mode='Markdown')
    bot.register_next_step_handler(msg, get_game_date)

def get_game_date(message):
    user_id = message.from_user.id
    temp_new_game[user_id]['date'] = message.text.strip()
    
    msg = bot.reply_to(message, "⏰ **مرحله 2 از 5:**\n\nلطفاً **ساعت برگزاری بازی** را وارد کنید.\nمثال: 19:00", parse_mode='Markdown')
    bot.register_next_step_handler(msg, get_game_time)

def get_game_time(message):
    user_id = message.from_user.id
    temp_new_game[user_id]['time'] = message.text.strip()
    
    msg = bot.reply_to(message, "📍 **مرحله 3 از 5:**\n\nلطفاً **مکان برگزاری بازی** را وارد کنید.\nمثال: سالن الغدیر", parse_mode='Markdown')
    bot.register_next_step_handler(msg, get_game_location)

def get_game_location(message):
    user_id = message.from_user.id
    temp_new_game[user_id]['location'] = message.text.strip()
    
    msg = bot.reply_to(message, "👥 **مرحله 4 از 5:**\n\nلطفاً **ظرفیت بازی** (تعداد نفرات) را وارد کنید.\nمثال: 12", parse_mode='Markdown')
    bot.register_next_step_handler(msg, get_game_capacity)

def get_game_capacity(message):
    user_id = message.from_user.id
    
    try:
        numbers = re.findall(r'\d+', message.text.strip())
        if numbers:
            capacity = int(numbers[0])
        else:
            capacity = int(message.text.strip())
    except:
        bot.reply_to(message, "❌ لطفاً یک عدد معتبر وارد کنید. مثال: 12")
        msg = bot.reply_to(message, "ظرفیت بازی را وارد کنید:")
        bot.register_next_step_handler(msg, get_game_capacity)
        return
    
    temp_new_game[user_id]['capacity'] = capacity
    
    msg = bot.reply_to(message, "💰 **مرحله 5 از 5:**\n\nلطفاً **هزینه هر نفر** را وارد کنید.\nمثال: 50000", parse_mode='Markdown')
    bot.register_next_step_handler(msg, get_game_cost)

def get_game_cost(message):
    user_id = message.from_user.id
    
    try:
        numbers = re.findall(r'\d+', message.text.strip())
        if numbers:
            cost = int(numbers[0])
        else:
            cost = int(message.text.strip())
    except:
        bot.reply_to(message, "❌ لطفاً یک عدد معتبر وارد کنید. مثال: 50000")
        msg = bot.reply_to(message, "هزینه هر نفر را وارد کنید:")
        bot.register_next_step_handler(msg, get_game_cost)
        return
    
    temp_new_game[user_id]['cost_per_person'] = cost
    
    data = load_data()
    
    new_game = {
        'id': data['next_game_id'],
        'date': temp_new_game[user_id]['date'],
        'time': temp_new_game[user_id]['time'],
        'location': temp_new_game[user_id]['location'],
        'capacity': temp_new_game[user_id]['capacity'],
        'cost_per_person': temp_new_game[user_id]['cost_per_person'],
        'players': [],
        'payment_proofs': {}
    }
    
    data['games'].append(new_game)
    data['next_game_id'] += 1
    save_data(data)
    
    summary = (
        f"✅ **بازی جدید ساخته شد!**\n\n"
        f"🎮 شماره: {new_game['id']}\n"
        f"📅 تاریخ: {new_game['date']}\n"
        f"⏰ ساعت: {new_game['time']}\n"
        f"📍 مکان: {new_game['location']}\n"
        f"👥 ظرفیت: {new_game['capacity']} نفر\n"
        f"💰 هزینه هر نفر: {new_game['cost_per_person']:,} تومان"
    )
    
    del temp_new_game[user_id]
    bot.reply_to(message, summary, parse_mode='Markdown', reply_markup=admin_menu_markup())

# ============= مدیریت بازی‌ها =============
@bot.message_handler(func=lambda message: message.text == "🎮 مدیریت بازی‌ها")
def manage_games(message):
    data = load_data()
    
    if not data['games']:
        bot.reply_to(message, "❌ هیچ بازی فعالی وجود ندارد!", reply_markup=admin_menu_markup())
        return
    
    bot.send_message(message.chat.id, 
        "🎮 **مدیریت بازی‌ها**\n\n"
        "لطفاً یکی از گزینه‌های زیر را انتخاب کنید:",
        parse_mode='Markdown',
        reply_markup=manage_games_menu())

@bot.callback_query_handler(func=lambda call: call.data == "admin_edit_game")
def edit_game_start(call):
    data = load_data()
    
    games_list = "🎮 **لیست بازی‌ها:**\n\n"
    for game in data['games']:
        games_list += f"شماره {game['id']}: {game['date']} - {game['location']} (ظرفیت: {len(game['players'])}/{game['capacity']})\n"
    
    msg = bot.send_message(call.message.chat.id, 
        f"{games_list}\n\n"
        "لطفاً **شماره بازی** مورد نظر برای ویرایش را وارد کنید:",
        parse_mode='Markdown')
    bot.register_next_step_handler(msg, select_game_to_edit)

def select_game_to_edit(message):
    try:
        game_id = int(message.text.strip())
        data = load_data()
        
        target_game = None
        for game in data['games']:
            if game['id'] == game_id:
                target_game = game
                break
        
        if not target_game:
            bot.reply_to(message, "❌ بازی پیدا نشد!", reply_markup=admin_menu_markup())
            return
        
        temp_edit_game[message.from_user.id] = {'game_id': game_id}
        
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("📅 ویرایش تاریخ", callback_data="edit_date"),
            types.InlineKeyboardButton("⏰ ویرایش ساعت", callback_data="edit_time"),
            types.InlineKeyboardButton("📍 ویرایش مکان", callback_data="edit_location"),
            types.InlineKeyboardButton("👥 ویرایش ظرفیت", callback_data="edit_capacity"),
            types.InlineKeyboardButton("💰 ویرایش هزینه", callback_data="edit_cost"),
            types.InlineKeyboardButton("🔙 انصراف", callback_data="admin_back_to_menu")
        )
        
        current_info = (
            f"🎮 **بازی شماره {game_id}**\n"
            f"📅 تاریخ: {target_game['date']}\n"
            f"⏰ ساعت: {target_game['time']}\n"
            f"📍 مکان: {target_game['location']}\n"
            f"👥 ظرفیت: {target_game['capacity']} نفر\n"
            f"💰 هزینه هر نفر: {target_game['cost_per_person']:,} تومان\n\n"
            f"کدام بخش را می‌خواهید ویرایش کنید؟"
        )
        
        bot.send_message(message.chat.id, current_info, parse_mode='Markdown', reply_markup=markup)
        
    except:
        bot.reply_to(message, "❌ شماره بازی معتبر وارد کنید!", reply_markup=admin_menu_markup())

@bot.callback_query_handler(func=lambda call: call.data in ['edit_date', 'edit_time', 'edit_location', 'edit_capacity', 'edit_cost'])
def edit_game_field(call):
    user_id = call.from_user.id
    
    if user_id not in temp_edit_game:
        bot.answer_callback_query(call.id, "❌ خطا! لطفاً دوباره تلاش کنید.")
        return
    
    temp_edit_game[user_id]['field'] = call.data
    
    field_names = {
        'edit_date': 'تاریخ جدید',
        'edit_time': 'ساعت جدید',
        'edit_location': 'مکان جدید',
        'edit_capacity': 'ظرفیت جدید (عدد)',
        'edit_cost': 'هزینه جدید هر نفر (عدد)'
    }
    
    msg = bot.send_message(call.message.chat.id, 
        f"✏️ لطفاً **{field_names[call.data]}** را وارد کنید:\n\n"
        f"(برای انصراف /cancel را بفرستید)")
    bot.register_next_step_handler(msg, save_edited_field)

def save_edited_field(message):
    if message.text == '/cancel':
        bot.reply_to(message, "❌ ویرایش لغو شد.", reply_markup=admin_menu_markup())
        if message.from_user.id in temp_edit_game:
            del temp_edit_game[message.from_user.id]
        return
    
    user_id = message.from_user.id
    
    if user_id not in temp_edit_game:
        bot.reply_to(message, "❌ خطا! لطفاً دوباره تلاش کنید.", reply_markup=admin_menu_markup())
        return
    
    game_id = temp_edit_game[user_id]['game_id']
    field = temp_edit_game[user_id]['field']
    
    data = load_data()
    
    target_game = None
    for game in data['games']:
        if game['id'] == game_id:
            target_game = game
            break
    
    if not target_game:
        bot.reply_to(message, "❌ بازی پیدا نشد!", reply_markup=admin_menu_markup())
        return
    
    new_value = message.text.strip()
    
    if field == 'edit_capacity':
        try:
            numbers = re.findall(r'\d+', new_value)
            new_value = int(numbers[0]) if numbers else int(new_value)
            target_game['capacity'] = new_value
            save_data(data)
            bot.reply_to(message, f"✅ ظرفیت بازی با موفقیت به {new_value} نفر تغییر یافت!", reply_markup=admin_menu_markup())
        except:
            bot.reply_to(message, "❌ لطفاً یک عدد معتبر وارد کنید!", reply_markup=admin_menu_markup())
            return
    
    elif field == 'edit_cost':
        try:
            numbers = re.findall(r'\d+', new_value)
            new_value = int(numbers[0]) if numbers else int(new_value)
            target_game['cost_per_person'] = new_value
            save_data(data)
            bot.reply_to(message, f"✅ هزینه هر نفر با موفقیت به {new_value:,} تومان تغییر یافت!", reply_markup=admin_menu_markup())
        except:
            bot.reply_to(message, "❌ لطفاً یک عدد معتبر وارد کنید!", reply_markup=admin_menu_markup())
            return
    
    elif field == 'edit_date':
        target_game['date'] = new_value
        save_data(data)
        bot.reply_to(message, f"✅ تاریخ بازی با موفقیت به {new_value} تغییر یافت!", reply_markup=admin_menu_markup())
    
    elif field == 'edit_time':
        target_game['time'] = new_value
        save_data(data)
        bot.reply_to(message, f"✅ ساعت بازی با موفقیت به {new_value} تغییر یافت!", reply_markup=admin_menu_markup())
    
    elif field == 'edit_location':
        target_game['location'] = new_value
        save_data(data)
        bot.reply_to(message, f"✅ مکان بازی با موفقیت به {new_value} تغییر یافت!", reply_markup=admin_menu_markup())
    
    if user_id in temp_edit_game:
        del temp_edit_game[user_id]

@bot.callback_query_handler(func=lambda call: call.data == "admin_delete_game")
def delete_game_start(call):
    data = load_data()
    
    games_list = "🎮 **لیست بازی‌ها:**\n\n"
    for game in data['games']:
        games_list += f"شماره {game['id']}: {game['date']} - {game['location']} (تعداد بازیکنان: {len(game['players'])})\n"
    
    msg = bot.send_message(call.message.chat.id, 
        f"{games_list}\n\n"
        "⚠️ **هشدار! این عمل غیرقابل بازگشت است.**\n\n"
        "لطفاً **شماره بازی** مورد نظر برای حذف را وارد کنید:\n"
        "(برای انصراف /cancel را بفرستید)",
        parse_mode='Markdown')
    bot.register_next_step_handler(msg, confirm_delete_game)

def confirm_delete_game(message):
    if message.text == '/cancel':
        bot.reply_to(message, "❌ حذف بازی لغو شد.", reply_markup=admin_menu_markup())
        return
    
    try:
        game_id = int(message.text.strip())
        data = load_data()
        
        target_game = None
        game_index = None
        for i, game in enumerate(data['games']):
            if game['id'] == game_id:
                target_game = game
                game_index = i
                break
        
        if not target_game:
            bot.reply_to(message, "❌ بازی پیدا نشد!", reply_markup=admin_menu_markup())
            return
        
        confirm_msg = (
            f"⚠️ **آیا از حذف این بازی اطمینان دارید؟**\n\n"
            f"🎮 بازی شماره {target_game['id']}\n"
            f"📅 تاریخ: {target_game['date']}\n"
            f"⏰ ساعت: {target_game['time']}\n"
            f"📍 مکان: {target_game['location']}\n"
            f"👥 تعداد بازیکنان ثبت‌نام کرده: {len(target_game['players'])} نفر\n\n"
            f"با حذف این بازی، تمام اطلاعات آن پاک خواهد شد.\n\n"
            f"برای تایید نهایی، عبارت **تایید** را وارد کنید:"
        )
        
        temp_admin_action[message.from_user.id] = {'delete_game_id': game_id, 'index': game_index}
        msg = bot.reply_to(message, confirm_msg, parse_mode='Markdown')
        bot.register_next_step_handler(msg, final_delete_game)
        
    except:
        bot.reply_to(message, "❌ شماره بازی معتبر وارد کنید!", reply_markup=admin_menu_markup())

def final_delete_game(message):
    if message.text.strip() == 'تایید':
        user_id = message.from_user.id
        
        if user_id not in temp_admin_action or 'delete_game_id' not in temp_admin_action[user_id]:
            bot.reply_to(message, "❌ خطا! لطفاً دوباره تلاش کنید.", reply_markup=admin_menu_markup())
            return
        
        game_id = temp_admin_action[user_id]['delete_game_id']
        game_index = temp_admin_action[user_id]['index']
        
        data = load_data()
        
        if game_index < len(data['games']):
            deleted_game = data['games'].pop(game_index)
            save_data(data)
            
            bot.reply_to(message, 
                f"✅ بازی شماره {game_id} با موفقیت حذف شد!\n"
                f"📅 تاریخ: {deleted_game['date']} - {deleted_game['location']}",
                reply_markup=admin_menu_markup())
        else:
            bot.reply_to(message, "❌ خطا در حذف بازی!", reply_markup=admin_menu_markup())
        
        del temp_admin_action[user_id]
    else:
        bot.reply_to(message, "❌ حذف بازی لغو شد. برای تایید باید دقیقاً «تایید» را وارد کنید.", reply_markup=admin_menu_markup())

# ============= مدیریت بازیکنان =============
@bot.message_handler(func=lambda message: message.text == "✏️ مدیریت بازیکنان")
def manage_players(message):
    bot.send_message(message.chat.id, 
        "🎮 **مدیریت بازیکنان**\n\n"
        "لطفاً یکی از گزینه‌های زیر را انتخاب کنید:",
        parse_mode='Markdown',
        reply_markup=manage_players_menu())

@bot.callback_query_handler(func=lambda call: call.data == "admin_add_player")
def add_player_start(call):
    temp_admin_action[call.from_user.id] = {'action': 'add'}
    
    data = load_data()
    if not data['games']:
        bot.send_message(call.message.chat.id, "❌ هیچ بازی فعالی وجود ندارد!", reply_markup=admin_menu_markup())
        return
    
    games_list = "🎮 **لیست بازی‌ها:**\n\n"
    for game in data['games']:
        games_list += f"شماره {game['id']}: {game['date']} - {game['location']}\n"
    
    msg = bot.send_message(call.message.chat.id, 
        f"{games_list}\n\n"
        "لطفاً **شماره بازی** مورد نظر را وارد کنید:",
        parse_mode='Markdown')
    bot.register_next_step_handler(msg, get_game_for_add)

def get_game_for_add(message):
    try:
        game_id = int(message.text.strip())
        temp_admin_action[message.from_user.id]['game_id'] = game_id
        
        msg = bot.reply_to(message, 
            "لطفاً **شناسه عددی کاربر** (User ID) را وارد کنید.\n\n"
            "⚠️ کاربر می‌تواند User ID خود را با دستور /id در ربات دریافت کند.\n\n"
            "مثال: 123456789")
        bot.register_next_step_handler(msg, get_user_id_for_add)
    except:
        bot.reply_to(message, "❌ شماره بازی معتبر وارد کنید!", reply_markup=admin_menu_markup())

def get_user_id_for_add(message):
    try:
        user_id = str(message.text.strip())
        game_id = temp_admin_action[message.from_user.id]['game_id']
        
        data = load_data()
        
        target_game = None
        for game in data['games']:
            if game['id'] == game_id:
                target_game = game
                break
        
        if not target_game:
            bot.reply_to(message, "❌ بازی پیدا نشد!", reply_markup=admin_menu_markup())
            return
        
        if user_id in target_game['players']:
            bot.reply_to(message, "⚠️ این کاربر قبلاً در بازی ثبت نام کرده است!", reply_markup=admin_menu_markup())
            return
        
        if len(target_game['players']) >= target_game['capacity']:
            bot.reply_to(message, "❌ ظرفیت بازی پر شده است!", reply_markup=admin_menu_markup())
            return
        
        user_name = "کاربر ناشناس"
        if user_id in data['users']:
            user_name = data['users'][user_id]['name']
        
        target_game['players'].append(user_id)
        save_data(data)
        
        bot.reply_to(message, 
            f"✅ کاربر {user_name} با موفقیت به بازی شماره {game_id} اضافه شد!",
            reply_markup=admin_menu_markup())
        
        del temp_admin_action[message.from_user.id]
        
    except:
        bot.reply_to(message, "❌ خطا! لطفاً شناسه کاربری معتبر وارد کنید.", reply_markup=admin_menu_markup())

@bot.callback_query_handler(func=lambda call: call.data == "admin_remove_player")
def remove_player_start(call):
    temp_admin_action[call.from_user.id] = {'action': 'remove'}
    
    data = load_data()
    if not data['games']:
        bot.send_message(call.message.chat.id, "❌ هیچ بازی فعالی وجود ندارد!", reply_markup=admin_menu_markup())
        return
    
    games_list = "🎮 **لیست بازی‌ها:**\n\n"
    for game in data['games']:
        games_list += f"شماره {game['id']}: {game['date']} - {game['location']}\n"
    
    msg = bot.send_message(call.message.chat.id, 
        f"{games_list}\n\n"
        "لطفاً **شماره بازی** مورد نظر را وارد کنید:",
        parse_mode='Markdown')
    bot.register_next_step_handler(msg, get_game_for_remove)

def get_game_for_remove(message):
    try:
        game_id = int(message.text.strip())
        temp_admin_action[message.from_user.id]['game_id'] = game_id
        
        data = load_data()
        
        target_game = None
        for game in data['games']:
            if game['id'] == game_id:
                target_game = game
                break
        
        if not target_game:
            bot.reply_to(message, "❌ بازی پیدا نشد!", reply_markup=admin_menu_markup())
            return
        
        if not target_game['players']:
            bot.reply_to(message, "❌ این بازی بازیکنی ندارد!", reply_markup=admin_menu_markup())
            return
        
        players_list = "👥 **لیست بازیکنان این بازی:**\n\n"
        for i, pid in enumerate(target_game['players'], 1):
            pid_str = str(pid)
            name = data['users'].get(pid_str, {}).get('name', 'نامشخص')
            players_list += f"{i}. {name} (ID: {pid})\n"
        
        msg = bot.reply_to(message, 
            f"{players_list}\n\n"
            "لطفاً **شناسه عددی کاربر** (User ID) مورد نظر برای حذف را وارد کنید:")
        bot.register_next_step_handler(msg, get_user_id_for_remove)
        
    except:
        bot.reply_to(message, "❌ شماره بازی معتبر وارد کنید!", reply_markup=admin_menu_markup())

def get_user_id_for_remove(message):
    try:
        user_id = str(message.text.strip())
        game_id = temp_admin_action[message.from_user.id]['game_id']
        
        data = load_data()
        
        target_game = None
        for game in data['games']:
            if game['id'] == game_id:
                target_game = game
                break
        
        if not target_game:
            bot.reply_to(message, "❌ بازی پیدا نشد!", reply_markup=admin_menu_markup())
            return
        
        if user_id not in target_game['players']:
            bot.reply_to(message, "❌ این کاربر در این بازی ثبت نام نکرده است!", reply_markup=admin_menu_markup())
            return
        
        user_name = data['users'].get(user_id, {}).get('name', 'کاربر ناشناس')
        
        target_game['players'].remove(user_id)
        
        if 'payment_proofs' in target_game and user_id in target_game['payment_proofs']:
            del target_game['payment_proofs'][user_id]
        
        save_data(data)
        
        bot.reply_to(message, 
            f"✅ کاربر {user_name} با موفقیت از بازی شماره {game_id} حذف شد!",
            reply_markup=admin_menu_markup())
        
        del temp_admin_action[message.from_user.id]
        
    except:
        bot.reply_to(message, "❌ خطا! لطفاً شناسه کاربری معتبر وارد کنید.", reply_markup=admin_menu_markup())

@bot.callback_query_handler(func=lambda call: call.data == "admin_back_to_menu")
def admin_back_to_menu(call):
    bot.send_message(call.message.chat.id, "به منوی مدیریت بازگشتید:", reply_markup=admin_menu_markup())

# ============= گزارش کامل بازی‌ها =============
@bot.message_handler(func=lambda message: message.text == "📊 گزارش کامل بازی‌ها")
def full_report(message):
    data = load_data()
    
    if not data['games']:
        bot.reply_to(message, "هیچ بازی‌ای وجود ندارد.", reply_markup=admin_menu_markup())
        return
    
    for game in data['games']:
        players_count = len(game['players'])
        available = game['capacity'] - players_count
        
        report = (
            f"🎮 **بازی شماره {game['id']}**\n"
            f"📅 تاریخ: {game['date']}\n"
            f"⏰ ساعت: {game['time']}\n"
            f"📍 مکان: {game['location']}\n"
            f"👥 ظرفیت کل: {game['capacity']} نفر\n"
            f"✅ تعداد حاضرین: {players_count} نفر\n"
            f"🔵 ظرفیت خالی: {available} نفر\n"
            f"💰 هزینه هر نفر: {game['cost_per_person']:,} تومان\n"
            f"💵 جمع دریافتی: {players_count * game['cost_per_person']:,} تومان\n\n"
            f"**📋 لیست اعضای ثبت‌نام کرده:**\n"
        )
        
        if game['players']:
            for i, player_id in enumerate(game['players'], 1):
                player_id = str(player_id)
                user_info = data['users'].get(player_id, {})
                name = user_info.get('name', 'نامشخص')
                username = user_info.get('username', 'ندارد')
                report += f"{i}. {name} (@{username}) - ID: {player_id}\n"
                
                if 'payment_proofs' in game and player_id in game['payment_proofs']:
                    try:
                        bot.send_photo(message.chat.id, game['payment_proofs'][player_id], 
                                     caption=f"📸 فیش واریزی {name}")
                    except:
                        report += f"   ⚠️ عکس فیش قابل نمایش نیست\n"
        else:
            report += "❌ هیچ کسی ثبت نام نکرده است.\n"
        
        report += "\n" + "-" * 40
        bot.send_message(message.chat.id, report, parse_mode='Markdown')
    
    bot.send_message(message.chat.id, "پایان گزارش.", reply_markup=admin_menu_markup())

# ============= دستور دریافت User ID =============
@bot.message_handler(commands=['id'])
def get_user_id(message):
    user_id = message.from_user.id
    bot.reply_to(message, f"🆔 شناسه کاربری شما:\n`{user_id}`\n\nاین عدد را برای مدیر ارسال کنید.", parse_mode='Markdown')

# ============= مسیر Health Check برای Render =============
@app.route('/')
def health_check():
    return "🤖 Volleyball Bot is running!", 200

@app.route('/health')
def health():
    return "OK", 200

# ============= تابع اجرای ربات در یک ترد جداگانه =============
def run_bot():
    """ربات رو در یک ترد جداگانه اجرا می‌کنه"""
    print("🤖 Starting bot polling...")
    bot.infinity_polling(timeout=10, long_polling_timeout=5)

# ============= اجرای اصلی =============
if __name__ == "__main__":
    # ربات رو در یک ترد جداگانه اجرا کن
    bot_thread = threading.Thread(target=run_bot)
    bot_thread.start()
    
    # سرور Flask رو شروع کن (برای health check)
    port = int(os.environ.get("PORT", 5000))
    print(f"🚀 Starting Flask server on port {port}...")
    app.run(host="0.0.0.0", port=port)
