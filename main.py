import os
import io
import json
import logging
import math
import asyncio
import re
import urllib.request
from threading import Thread
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReactionTypeEmoji
from telegram.constants import ParseMode
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, CommandHandler, filters, ConversationHandler, CallbackQueryHandler
from telegram.error import Forbidden, BadRequest
from PIL import Image, ImageDraw, ImageFont, features
import arabic_reshaper
from bidi.algorithm import get_display

# ================= خادم الويب الوهمي =================
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running perfectly and FAST!"

def run_web():
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

# ================= إعدادات البوت =================
TOKEN = '8276416144:AAHQ19rjAtIHgAa693fG8ib7uvJn01FMEiU'
ADMIN_ID = 720330522

# ================= إعدادات الخط التلقائية =================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FONT_FILE = os.path.join(BASE_DIR, "Tajawal-Bold.ttf")

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

if not os.path.exists(FONT_FILE):
    logging.info("🔍 ملف الخط غير موجود، جاري تحميل خط Tajawal المعتمد...")
    try:
        url = "https://raw.githubusercontent.com/googlefonts/tajawal/main/fonts/ttf/Tajawal-Bold.ttf"
        urllib.request.urlretrieve(url, FONT_FILE)
        logging.info("✅ تم تحميل الخط بنجاح!")
    except Exception as e:
        logging.error(f"❌ فشل تحميل الخط: {e}")

DEV_USERNAME = "@xxbassamxx"
CHANNEL_LINK = "https://t.me/promohunter13" 
ALLOWED_GROUPS = [-1002142197378, -1002793271442]

EXEMPT_BOT_USERNAME = "@Hunterof_bot"
EXEMPT_BOT_ID = 7758344981

USERS_FILE = 'users.json'

ALL_REACTIONS = [
    "👍", "👎", "❤️", "🔥", "🥰", "👏", "😁", "🤔", "🤯", "😱", "🤬", "😢", "🤩", "🤮", "💩", "🙏", "👌", "🕊️", "🤡", "🥱", "🥴", "🌚", "🌭", "💯", "🤣", "⚡️", "🍌", "🏆", "💔", "🤨", "😐", "🍓", "🍾", "💋", "🖕", "😈", "😴", "😭", "🤓", "👻", "👨‍💻", "👀", "🎃", "🎄", "💥", "🫡", "💊"
]

def load_users():
    if not os.path.exists(USERS_FILE): return []
    with open(USERS_FILE, 'r') as f:
        try: return json.load(f)
        except: return []

def save_user(user_id):
    users = load_users()
    if user_id not in users:
        users.append(user_id)
        with open(USERS_FILE, 'w') as f: json.dump(users, f)

def add_secure_watermark(image_bytes):
    try:
        base_image = Image.open(image_bytes).convert("RGBA")
        width, height = base_image.size
        diagonal = int(math.sqrt(width**2 + height**2))
        canvas_size = int(diagonal * 1.5)
        txt_layer = Image.new("RGBA", (canvas_size, canvas_size), (255, 255, 255, 0))
        draw = ImageDraw.Draw(txt_layer)
        text_raw = "صياد العروض"
        
        font_size = int(width / 16)
        if font_size < 24: font_size = 24
        
        if not os.path.exists(FONT_FILE):
            raise FileNotFoundError(f"مسار الخط غير صحيح أو الملف غير موجود.")
            
        try:
            font = ImageFont.truetype(FONT_FILE, font_size)
        except Exception as e:
            logging.error(f"❌ الملف موجود لكن فشل تحميله: {e}")
            raise e

        stroke_width = int(font_size / 12)
        if stroke_width < 1: stroke_width = 1

        if features.check("raqm"):
            text_to_draw = text_raw
            draw_kwargs = {'direction': 'rtl', 'language': 'ar'}
        else:
            reshaped_text = arabic_reshaper.reshape(text_raw)
            text_to_draw = get_display(reshaped_text, base_dir='R')
            draw_kwargs = {}

        text_bbox = draw.textbbox((0, 0), text_to_draw, font=font, stroke_width=stroke_width, **draw_kwargs)
        text_w, text_h = text_bbox[2] - text_bbox[0], text_bbox[3] - text_bbox[1]
        gap_x, gap_y = int(text_w * 2.0), int(text_h * 3.0)
        center_offset = canvas_size // 2
        
        for y in range(-center_offset, canvas_size, gap_y):
            for x in range(-center_offset, canvas_size, gap_x):
                shift = (y // gap_y) % 2 * (gap_x // 2)
                pos = (x + shift, y)
                draw.text(pos, text_to_draw, font=font, fill=(0, 0, 0, 70), stroke_width=stroke_width, stroke_fill=(0, 0, 0, 70), **draw_kwargs)
                draw.text(pos, text_to_draw, font=font, fill=(255, 255, 255, 70), **draw_kwargs)
                
        rotated_layer = txt_layer.rotate(30, resample=Image.BICUBIC, expand=False)
        left, top = (canvas_size - width) // 2, (canvas_size - height) // 2
        final_txt_layer = rotated_layer.crop((left, top, left + width, top + height))
        
        if final_txt_layer.size != base_image.size:
            final_txt_layer = final_txt_layer.resize(base_image.size, Image.Resampling.NEAREST)
            
        watermarked = Image.alpha_composite(base_image, final_txt_layer)
        output = io.BytesIO()
        watermarked.convert("RGB").save(output, format="JPEG", quality=95)
        output.seek(0)
        return output
        
    except Exception as e:
        logging.error(f"Watermark Error: {e}")
        return None

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    save_user(user.id)

    welcome_msg = (
        f"👋 أهلاً بك يا **{user.first_name}** في بوت صياد العروض 🎯\n\n"
        f"✅ **حسابك مفعل ومسجل لدينا.**\n"
        f"👨‍💻 المبرمج: {DEV_USERNAME}"
    )

    keyboard = [
        [InlineKeyboardButton("📢 قناة العروض", url=CHANNEL_LINK)],
        [InlineKeyboardButton("👨‍💻 تواصل مع الإدارة", url=f"https://t.me/{DEV_USERNAME.replace('@', '')}")]
    ]

    await update.message.reply_text(welcome_msg, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users = load_users()
    await update.message.reply_text(f"📊 **إحصائيات البوت:**\n\n👥 عدد المشتركين في البوت: `{len(users)}` مستخدم.", parse_mode=ParseMode.MARKDOWN)

async def bot_added_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg or not msg.new_chat_members: return
    for member in msg.new_chat_members:
        if member.id == context.bot.id:
            if msg.chat_id not in ALLOWED_GROUPS:
                try:
                    await msg.reply_text("⚠️ **عذراً!**\nأنا بوت خاص.\nأستأذنكم بالمغادرة 👋", parse_mode=ParseMode.MARKDOWN)
                    await context.bot.leave_chat(msg.chat_id)
                except: pass
            break

ASK_CHAT_GROUP, LIVE_CHAT_MODE = range(20, 22)

async def start_live_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    groups_text = "\n".join([f"• `{gid}`" for gid in ALLOWED_GROUPS])
    await update.message.reply_text(
        f"🟢 **وضع الدردشة المباشرة**\n\n"
        f"اختر القروب اللي تبي تسولف فيه:\n{groups_text}\n\n"
        f"أرسل الآيدي للبدء:", 
        parse_mode=ParseMode.MARKDOWN
    )
    return ASK_CHAT_GROUP

async def receive_chat_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if text.lstrip('-').isdigit() and int(text) in ALLOWED_GROUPS:
        context.user_data['live_group_id'] = int(text)
        await update.message.reply_text(
            f"✅ **تم الربط بنجاح!**\n\n"
            f"الآن، أي شيء ترسله هنا (نص، صورة، فيديو، ملصق) سيتم إرساله للقروب فوراً.\n\n"
            f"🔴 لإيقاف الدردشة والعودة للوضع الطبيعي، أرسل: `/stop`",
            parse_mode=ParseMode.MARKDOWN
        )
        return LIVE_CHAT_MODE
    else:
        await update.message.reply_text("⚠️ معرف القروب غير صحيح أو غير مسموح به. حاول مجدداً:")
        return ASK_CHAT_GROUP

async def live_chat_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == '/stop':
        await update.message.reply_text("🔴 **تم إيقاف وضع الدردشة المباشرة.**\nعاد البوت لوضعه الطبيعي.", parse_mode=ParseMode.MARKDOWN)
        context.user_data.clear()
        return ConversationHandler.END

    group_id = context.user_data.get('live_group_id')
    try:
        await context.bot.copy_message(
            chat_id=group_id,
            from_chat_id=update.effective_chat.id,
            message_id=update.message.message_id
        )
    except Exception as e:
        await update.message.reply_text(f"❌ حدث خطأ في الإرسال: {e}")

ASK_ID, ASK_MSG, CONFIRM_SEND = range(30, 33)

async def start_send(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("أرسل آيدي الشخص اللي تبي تراسله:")
    return ASK_ID

async def receive_target_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if not text.isdigit() and not text.startswith('-'): 
        await update.message.reply_text("⚠️ الآيدي لازم يكون أرقام بس! جرب مرة ثانية:")
        return ASK_ID

    context.user_data['target_id'] = text
    await update.message.reply_text("✏️ أرسل الرسالة اللي تبيها (تقدر ترسل نص، صورة، أو فيديو):")
    return ASK_MSG

async def receive_target_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['target_msg_id'] = update.message.message_id
    kb = [
        [InlineKeyboardButton("✅ تأكيد وإرسال", callback_data='confirm_yes')],
        [InlineKeyboardButton("❌ إلغاء", callback_data='confirm_no')]
    ]
    await update.message.reply_text(
        f"سيتم إرسال رسالتك إلى الآيدي `{context.user_data['target_id']}`.\n\nتأكيد؟", 
        reply_markup=InlineKeyboardMarkup(kb), 
        parse_mode=ParseMode.MARKDOWN
    )
    return CONFIRM_SEND

async def handle_send_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == 'confirm_yes':
        try:
            await context.bot.copy_message(
                chat_id=context.user_data['target_id'],
                from_chat_id=update.effective_chat.id,
                message_id=context.user_data['target_msg_id']
            )
            await query.edit_message_text("ابشر طال عمرك 🫡\n✅ تم الإرسال للمستخدم بنجاح!")
        except Exception as e: 
            await query.edit_message_text(f"❌ فشل الإرسال (تأكد من الآيدي أو إن المستخدم مب مفعل البوت): {e}")
    else: 
        await query.edit_message_text("❌ تم الإلغاء.")

    context.user_data.clear()
    return ConversationHandler.END

WAITING_FOR_DM_REPLY = 10

async def forward_to_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type == 'private' and update.effective_user.id != ADMIN_ID:
        user = update.effective_user
        msg = update.message
        save_user(user.id)

        info_text = f"📩 **رسالة من الخاص:** {user.first_name}\n🆔 `{user.id}`"

        try:
            forwarded_msg = await context.bot.forward_message(chat_id=ADMIN_ID, from_chat_id=user.id, message_id=msg.message_id)

            kb = [
                [InlineKeyboardButton("💬 الرد على المستخدم", callback_data=f"dm_reply_{user.id}_{msg.message_id}")],
                [InlineKeyboardButton("🗑️ مسح الرسالة", callback_data=f"dm_delete_{user.id}_{msg.message_id}")],
                [InlineKeyboardButton("✅ تم الاطلاع (إخفاء الأزرار)", callback_data=f"dm_ignore")]
            ]
            await context.bot.send_message(chat_id=ADMIN_ID, text=info_text, reply_to_message_id=forwarded_msg.message_id, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN)
        except Exception as e:
            logging.error(f"Error forwarding: {e}")

async def handle_dm_actions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == 'cancel_dm_reply':
        await query.edit_message_text("❌ تم إلغاء الرد.")
        context.user_data.clear()
        return ConversationHandler.END

    if query.data == 'dm_ignore':
        await query.edit_message_text("👁️ تم الاطلاع.")
        return ConversationHandler.END

    data = query.data.split('_')
    if len(data) < 4: return
    action = data[1]
    user_id = int(data[2])
    msg_id = int(data[3])

    if action == 'delete':
        try:
            await context.bot.delete_message(chat_id=user_id, message_id=msg_id)
            await query.edit_message_text(f"✅ تم سحب الرسالة ومسحها من محادثة المستخدم `{user_id}` 🗑️", parse_mode=ParseMode.MARKDOWN)
        except Exception:
            await query.edit_message_text(f"❌ تعذر الحذف (قد تكون الرسالة قديمة لأكثر من 48 ساعة).")
        return ConversationHandler.END

    elif action == 'reply':
        context.user_data['reply_user_id'] = user_id
        context.user_data['reply_msg_id'] = msg_id
        keyboard = [[InlineKeyboardButton("❌ إلغاء", callback_data='cancel_dm_reply')]]
        await query.edit_message_text(f"💬 أرسل الرد الآن (نص، صورة، فيديو) ليتم إرساله للمستخدم `{user_id}`:", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)
        return WAITING_FOR_DM_REPLY

async def send_dm_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = context.user_data.get('reply_user_id')
    reply_msg_id = context.user_data.get('reply_msg_id')

    try:
        await context.bot.copy_message(
            chat_id=user_id,
            from_chat_id=update.effective_chat.id,
            message_id=update.message.message_id,
            reply_to_message_id=reply_msg_id 
        )
        await update.message.reply_text("✅ تم الإرسال للمستخدم بنجاح كإقتباس لرسالته!")
    except Exception:
        await update.message.reply_text(f"❌ حدث خطأ، ربما قام المستخدم بحظر البوت.")

    context.user_data.clear()
    return ConversationHandler.END

ASK_BC_MSG, CONFIRM_BC = range(11, 13)

async def start_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📢 أرسل الرسالة التي تود بثها لجميع المشتركين (نص، صورة، فيديو):")
    return ASK_BC_MSG

async def receive_bc_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['bc_msg_id'] = update.message.message_id
    users = load_users()
    kb = [[InlineKeyboardButton("✅ تأكيد وبدء البث", callback_data='confirm_bc'), InlineKeyboardButton("❌ إلغاء", callback_data='cancel_bc')]]
    await update.message.reply_text(f"الرسالة جاهزة.\nسيتم إرسالها إلى **{len(users)}** مستخدم.\nهل أنت متأكد؟", reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN)
    return CONFIRM_BC

async def handle_bc_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; await query.answer()
    if query.data == 'confirm_bc':
        msg_id = context.user_data.get('bc_msg_id')
        users = load_users()
        await query.edit_message_text(f"⏳ جاري البث لـ {len(users)} مستخدم... الرجاء الانتظار.")

        success, failed = 0, 0
        for uid in users:
            try:
                await context.bot.copy_message(chat_id=uid, from_chat_id=ADMIN_ID, message_id=msg_id)
                success += 1
                await asyncio.sleep(0.05)
            except: failed += 1

        await context.bot.send_message(chat_id=ADMIN_ID, text=f"✅ **انتهى البث!**\n\n🟢 نجاح: {success}\n🔴 فشل (حظروا البوت): {failed}", parse_mode=ParseMode.MARKDOWN)
    else: await query.edit_message_text("❌ تم إلغاء البث.")
    context.user_data.clear(); return ConversationHandler.END

CHOOSING_ACTION, WAITING_FOR_TEXT, CHOOSING_REACTION, WAITING_FOR_EDIT_TEXT = range(4)

def get_reaction_keyboard():
    keyboard, row = [], []
    for index, emoji in enumerate(ALL_REACTIONS):
        row.append(InlineKeyboardButton(emoji, callback_data=f"re_{emoji}"))
        if len(row) == 6:
            keyboard.append(row)
            row = []
    if row: keyboard.append(row)
    keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data='back_to_main')])
    return InlineKeyboardMarkup(keyboard)

def get_main_action_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💬 أرد عليه بكلام", callback_data='reply_text')],
        [InlineKeyboardButton("✏️ تعديل الرسالة", callback_data='edit_msg')],
        [InlineKeyboardButton("🎭 إضافة رياكشن", callback_data='open_reactions')],
        [InlineKeyboardButton("🗑️ حذف الرسالة", callback_data='delete_msg')],
        # تمت إضافة زر السحب السري هنا ⬇️
        [InlineKeyboardButton("📥 سحب ونسخ الرسالة (سري)", callback_data='fetch_msg')],
        [InlineKeyboardButton("❌ إلغاء", callback_data='cancel_action')]
    ])

async def receive_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    link = update.message.text
    match = re.search(r"t\.me/(?:c/)?([^/]+)/(\d+)", link)
    if match:
        chat_part = match.group(1)
        msg_id = int(match.group(2))

        if chat_part.isdigit():
            chat_id = int(f"-100{chat_part}")
        else:
            chat_id = f"@{chat_part}"

        context.user_data['chat_username'] = chat_id
        context.user_data['message_id'] = msg_id

        await update.message.reply_text("وصل الرابط 🎯\nوش تبي البوت يسوي؟", reply_markup=get_main_action_keyboard())
        return CHOOSING_ACTION
    return ConversationHandler.END

async def handle_button_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; await query.answer()
    choice = query.data
    chat_username, message_id = context.user_data.get('chat_username'), context.user_data.get('message_id')

    if choice == 'reply_text':
        await query.edit_message_text("أرسل الكلام اللي تبيه:")
        return WAITING_FOR_TEXT
    elif choice == 'edit_msg':
        await query.edit_message_text("✏️ أرسل النص الجديد للرسالة (أو الكبشن الجديد للصور):")
        return WAITING_FOR_EDIT_TEXT
    elif choice == 'open_reactions':
        await query.edit_message_text("اختر الرياكشن المطلوب: 👇", reply_markup=get_reaction_keyboard())
        return CHOOSING_REACTION
    elif choice == 'delete_msg':
        try:
            await context.bot.delete_message(chat_id=chat_username, message_id=message_id)
            await query.edit_message_text("ابشر طال عمرك 🫡\nتم مسح الرسالة من القروب نهائياً. 🗑️")
        except Exception as e: await query.edit_message_text(f"صار خطأ (قد تكون الرسالة مو للبوت أو قديمة): {e}")
        context.user_data.clear(); return ConversationHandler.END
    # تمت إضافة كود السحب هنا ⬇️
    elif choice == 'fetch_msg':
        try:
            await context.bot.copy_message(
                chat_id=update.effective_chat.id,
                from_chat_id=chat_username,
                message_id=message_id
            )
            await query.edit_message_text("ابشر طال عمرك 🫡\n✅ تم سحب الرسالة لك بالخاص بنجاح بدون أي أثر بالقروب (بدون توجيه) 🤫")
        except Exception as e:
            await query.edit_message_text(f"❌ صار خطأ (قد تكون الرسالة محذوفة أو البوت مو بالقروب): {e}")
        context.user_data.clear(); return ConversationHandler.END
    elif choice == 'cancel_action':
        await query.edit_message_text("تم الإلغاء. 🛡️")
        context.user_data.clear(); return ConversationHandler.END

async def handle_reaction_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; await query.answer(); data = query.data
    chat_username, message_id = context.user_data.get('chat_username'), context.user_data.get('message_id')

    if data == 'back_to_main':
        await query.edit_message_text("وش تبي البوت يسوي؟", reply_markup=get_main_action_keyboard())
        return CHOOSING_ACTION

    if data.startswith("re_"):
        emoji = data.replace("re_", "")
        try:
            await context.bot.set_message_reaction(chat_id=chat_username, message_id=message_id, reaction=[ReactionTypeEmoji(emoji)])
            await query.edit_message_text(f"تم! حطيت رياكشن {emoji} بالقروب. 😎")
        except Exception as e: await query.edit_message_text(f"خطأ: {e}")
        context.user_data.clear(); return ConversationHandler.END

async def send_custom_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await context.bot.copy_message(
            chat_id=context.user_data.get('chat_username'),
            from_chat_id=update.effective_chat.id,
            message_id=update.message.message_id,
            reply_to_message_id=context.user_data.get('message_id')
        )
        await update.message.reply_text("ابشر طال عمرك 🫡\nتم الرد بالقروب!")
    except Exception as e: await update.message.reply_text(f"خطأ: {e}")
    context.user_data.clear(); return ConversationHandler.END

async def edit_custom_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = context.user_data.get('chat_username')
    msg_id = context.user_data.get('message_id')
    new_text = update.message.text

    try:
        await context.bot.edit_message_text(chat_id=chat_id, message_id=msg_id, text=new_text)
        await update.message.reply_text("ابشر طال عمرك 🫡\n✅ تم تعديل الرسالة النصية بنجاح!")
    except BadRequest as e:
        if "There is no text in the message to edit" in str(e):
            try:
                await context.bot.edit_message_caption(chat_id=chat_id, message_id=msg_id, caption=new_text)
                await update.message.reply_text("ابشر طال عمرك 🫡\n✅ تم تعديل الوصف (الكبشن) للصورة بنجاح!")
            except Exception as ex:
                await update.message.reply_text(f"❌ ما قدرت أعدل الصورة: {ex}")
        elif "Message can't be edited" in str(e):
            await update.message.reply_text("❌ ما أقدر أعدل هذي الرسالة (لازم تكون من إرسال البوت نفسه).")
        else:
            await update.message.reply_text(f"❌ خطأ: {e}")
    except Exception as e:
        await update.message.reply_text(f"❌ خطأ عام: {e}")

    context.user_data.clear()
    return ConversationHandler.END

async def manual_save_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    user_id = update.effective_user.id
    if not msg or not msg.reply_to_message: return

    target = msg.reply_to_message
    is_photo, is_video = bool(target.photo), bool(target.video)
    is_text = bool(target.text and not (is_photo or is_video))

    if not (is_photo or is_video or is_text): return

    if (is_video or is_text) and user_id != ADMIN_ID:
        return

    text_content = msg.text.lower() if msg.text else ""
    bot_username = (await context.bot.get_me()).username.lower()

    if not (any(t in text_content for t in ["حفظ", "احفظ", "جيبها", "صياد", "save"]) or f"@{bot_username}" in text_content): 
        return

    status_msg = await msg.reply_text("ابشر طال عمرك 🫡" if user_id == ADMIN_ID else "🛡️ لحظات...")

    try:
        caption = f"✅ تم الحفظ.\n\n{target.caption if target.caption else ''}\n\n🤖 عبر بوت صياد العروض | {DEV_USERNAME}"

        if is_text: 
            await context.bot.send_message(chat_id=user_id, text=f"{target.text}\n\n🤖 @xxbassamxx")
        elif is_photo:
            file = await target.photo[-1].get_file(read_timeout=60, connect_timeout=60)
            stream = io.BytesIO()
            await file.download_to_memory(out=stream)
            stream.seek(0)

            is_ex = (target.from_user.id == EXEMPT_BOT_ID) or (f"@{target.from_user.username}".lower() == EXEMPT_BOT_USERNAME.lower())
            final = stream if is_ex else await asyncio.to_thread(add_secure_watermark, stream)

            if not final:
                raise Exception("فشل دمج الحقوق")

            final.seek(0)
            await context.bot.send_photo(
                chat_id=user_id, 
                photo=final, 
                caption=caption,
                read_timeout=60, 
                write_timeout=60, 
                connect_timeout=60
            )

        elif is_video:
            file = await target.video.get_file(read_timeout=120, connect_timeout=120)
            stream = io.BytesIO()
            await file.download_to_memory(out=stream)
            stream.seek(0)
            
            await context.bot.send_video(
                chat_id=user_id, 
                video=stream, 
                caption=caption,
                read_timeout=120, 
                write_timeout=120, 
                connect_timeout=120
            )

        if user_id != ADMIN_ID:
            await status_msg.edit_text("✅ تم الإرسال بالخاص.")

        await asyncio.sleep(5)
        await status_msg.delete()
        await msg.delete()

    except (Forbidden, BadRequest) as e:
        if isinstance(e, BadRequest) and "chat not found" not in str(e).lower():
            await status_msg.edit_text(f"❌ حدث خطأ غير متوقع: {e}")
            await asyncio.sleep(3)
            await status_msg.delete()
            return

        kb = InlineKeyboardMarkup([[InlineKeyboardButton("🤖 تفعيل البوت لاستلام الصور (اضغط هنا)", url=f"https://t.me/{bot_username}?start=1")]])
        await status_msg.edit_text(
            "⚠️ **عذراً، لا أستطيع إرسال الصورة لك!**\n\n"
            "يبدو أنك لم تقم بتفعيل البوت في الخاص، أو قمت بإيقافه.\n"
            "فضلاً، اضغط على الزر بالأسفل لتفعيل البوت ⬇️، ثم أعد طلب الحفظ.",
            reply_markup=kb,
            parse_mode=ParseMode.MARKDOWN
        )

    except Exception as e: 
        logging.error(f"Save Error: {e}")
        await status_msg.edit_text("❌ حدث خطأ أثناء تجهيز الصورة.")
        await asyncio.sleep(3)
        await status_msg.delete()

if __name__ == '__main__':
    Thread(target=run_web).start()
    
    app_bot = (
        ApplicationBuilder()
        .token(TOKEN)
        .read_timeout(60)
        .write_timeout(60)
        .connect_timeout(60)
        .pool_timeout(60)
        .build()
    )

    app_bot.add_handler(CommandHandler("start", start_command))
    app_bot.add_handler(CommandHandler("stats", stats_command, filters=filters.User(ADMIN_ID)))
    app_bot.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, bot_added_handler))

    app_bot.add_handler(ConversationHandler(
        entry_points=[CommandHandler("send", start_send, filters=filters.User(ADMIN_ID))],
        states={
            ASK_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_target_id)],
            ASK_MSG: [MessageHandler(filters.ALL & ~filters.COMMAND, receive_target_msg)],
            CONFIRM_SEND: [CallbackQueryHandler(handle_send_confirmation, pattern="^(confirm_yes|confirm_no)$")]
        },
        fallbacks=[CommandHandler('cancel', lambda u,c: ConversationHandler.END)]))

    app_bot.add_handler(ConversationHandler(
        entry_points=[CommandHandler("chat", start_live_chat, filters=filters.User(ADMIN_ID))],
        states={
            ASK_CHAT_GROUP: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_chat_group)],
            LIVE_CHAT_MODE: [MessageHandler(filters.ALL & ~filters.COMMAND, live_chat_handler)]
        },
        fallbacks=[CommandHandler('stop', live_chat_handler)]))

    app_bot.add_handler(ConversationHandler(
        entry_points=[MessageHandler(filters.Regex(r"t\.me/(?:c/)?.+/\d+") & filters.ChatType.PRIVATE & filters.User(ADMIN_ID), receive_link)],
        states={
            CHOOSING_ACTION: [CallbackQueryHandler(handle_button_choice)],
            WAITING_FOR_TEXT: [MessageHandler(filters.ALL & ~filters.COMMAND, send_custom_reply)],
            WAITING_FOR_EDIT_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_custom_message)],
            CHOOSING_REACTION: [CallbackQueryHandler(handle_reaction_choice)]
        },
        fallbacks=[CommandHandler('cancel', lambda u,c: ConversationHandler.END)]))

    app_bot.add_handler(ConversationHandler(
        entry_points=[CommandHandler("bc", start_broadcast, filters=filters.User(ADMIN_ID))],
        states={
            ASK_BC_MSG: [MessageHandler(filters.ALL & ~filters.COMMAND, receive_bc_msg)],
            CONFIRM_BC: [CallbackQueryHandler(handle_bc_confirmation, pattern="^(confirm_bc|cancel_bc)$")]
        },
        fallbacks=[CommandHandler('cancel', lambda u,c: ConversationHandler.END)]))

    app_bot.add_handler(ConversationHandler(
        entry_points=[CallbackQueryHandler(handle_dm_actions, pattern="^dm_|^cancel_dm_reply|^dm_ignore")],
        states={
            WAITING_FOR_DM_REPLY: [MessageHandler(filters.ALL & ~filters.COMMAND, send_dm_reply)]
        },
        fallbacks=[CommandHandler('cancel', lambda u,c: ConversationHandler.END)]))

    app_bot.add_handler(MessageHandler(filters.TEXT & filters.REPLY, manual_save_handler), group=1)
    app_bot.add_handler(MessageHandler(filters.ChatType.PRIVATE & ~filters.COMMAND & ~filters.User(ADMIN_ID), forward_to_admin))

    print("✅ البوت اشتغل! تم إضافة مهلة انتظار أطول لتفادي مشاكل ضعف السيرفر.")
    app_bot.run_polling()
