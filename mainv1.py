import os
import io
import logging
import math
import asyncio
import re
from threading import Thread
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReactionTypeEmoji
from telegram.constants import ParseMode
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, CommandHandler, filters, ConversationHandler, CallbackQueryHandler
from telegram.error import Forbidden, BadRequest
from PIL import Image, ImageDraw, ImageFont
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
FONT_FILE = "font.ttf"
DEV_USERNAME = "@xxbassamxx"
ALLOWED_GROUPS = [-1002142197378, -1002793271442]

# إعدادات البوت المستثنى
EXEMPT_BOT_USERNAME = "@Hunterof_bot"
EXEMPT_BOT_ID = 7758344981

# قائمة الرياكشنات الشاملة (كل رياكشنات تلجرام المتاحة حالياً)
ALL_REACTIONS = [
    "👍", "👎", "❤️", "🔥", "🥰", "👏", "😁", "🤔", "🤯", "😱", "🤬", "😢", "🤩", "🤮", "💩", "🙏", "👌", "🕊️", "🤡", "🥱", "🥴", "🌚", "🌭", "💯", "🤣", "⚡️", "🍌", "🏆", "💔", "🤨", "😐", "🍓", "🍾", "💋", "🖕", "😈", "😴", "😭", "🤓", "👻", "👨‍💻", "👀", "🎃", "🎄", "💥", "🫡", "💊", "🍓"
]

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# ================= دالة الحقوق (Watermark) =================
def add_secure_watermark(image_bytes):
    try:
        base_image = Image.open(image_bytes).convert("RGBA")
        width, height = base_image.size
        diagonal = int(math.sqrt(width**2 + height**2))
        canvas_size = int(diagonal * 1.5)
        txt_layer = Image.new("RGBA", (canvas_size, canvas_size), (255, 255, 255, 0))
        draw = ImageDraw.Draw(txt_layer)
        text_raw = "صياد العروض"
        reshaped_text = arabic_reshaper.reshape(text_raw)
        bidi_text = get_display(reshaped_text)
        font_size = int(width / 16)
        if font_size < 24: font_size = 24
        try:
            if os.path.exists(FONT_FILE): font = ImageFont.truetype(FONT_FILE, font_size)
            else: font = ImageFont.load_default()
        except: font = ImageFont.load_default()
        stroke_width = int(font_size / 12)
        if stroke_width < 1: stroke_width = 1
        text_bbox = draw.textbbox((0, 0), bidi_text, font=font, stroke_width=stroke_width)
        text_w, text_h = text_bbox[2] - text_bbox[0], text_bbox[3] - text_bbox[1]
        gap_x, gap_y = int(text_w * 2.0), int(text_h * 3.0)
        center_offset = canvas_size // 2
        for y in range(-center_offset, canvas_size, gap_y):
            for x in range(-center_offset, canvas_size, gap_x):
                shift = (y // gap_y) % 2 * (gap_x // 2)
                pos = (x + shift, y)
                draw.text(pos, bidi_text, font=font, fill=(0, 0, 0, 70), stroke_width=stroke_width, stroke_fill=(0, 0, 0, 70))
                draw.text(pos, bidi_text, font=font, fill=(255, 255, 255, 70))
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
        logging.error(f"Watermark Error: {e}"); return None

# ================= أوامر البداية والحماية =================
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_name = update.effective_user.first_name
    welcome_msg = f"👋 أهلاً بك يا {user_name} في **بوت صياد العروض**.\n\n✅ **تم تفعيل حسابك.**\nالآن يمكنك استخدام البوت في المجموعة المخصصة.\n\n👨‍💻 المبرمج: {DEV_USERNAME}"
    await update.message.reply_text(welcome_msg, parse_mode=ParseMode.MARKDOWN)

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

# ================= نظام الرد بالروابط والرياكشنات =================
CHOOSING_ACTION, WAITING_FOR_TEXT, CHOOSING_REACTION = range(3)

def get_reaction_keyboard():
    keyboard = []
    row = []
    for index, emoji in enumerate(ALL_REACTIONS):
        row.append(InlineKeyboardButton(emoji, callback_data=f"re_{emoji}"))
        if len(row) == 6: # 6 أزرار في كل صف
            keyboard.append(row)
            row = []
    if row: keyboard.append(row)
    keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data='back_to_main')])
    return InlineKeyboardMarkup(keyboard)

async def receive_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    link = update.message.text
    match = re.search(r"t\.me/([^/]+)/(\d+)", link)
    if match:
        context.user_data['chat_username'] = f"@{match.group(1)}"
        context.user_data['message_id'] = int(match.group(2))

        keyboard = [
            [InlineKeyboardButton("💬 أرد عليه بكلام", callback_data='reply_text')],
            [InlineKeyboardButton("🎭 إضافة رياكشن (كل الأنواع)", callback_data='open_reactions')],
            [InlineKeyboardButton("🗑️ حذف الرسالة", callback_data='delete_msg')],
            [InlineKeyboardButton("❌ إلغاء", callback_data='cancel_action')]
        ]
        await update.message.reply_text("وصل الرابط 🎯\nوش تبي البوت يسوي؟", reply_markup=InlineKeyboardMarkup(keyboard))
        return CHOOSING_ACTION
    return ConversationHandler.END

async def handle_button_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    choice = query.data
    chat_username = context.user_data.get('chat_username')
    message_id = context.user_data.get('message_id')

    if choice == 'reply_text':
        await query.edit_message_text("أرسل الكلام اللي تبيه:")
        return WAITING_FOR_TEXT

    elif choice == 'open_reactions':
        await query.edit_message_text("اختر الرياكشن المطلوب من القائمة أدناه: 👇", reply_markup=get_reaction_keyboard())
        return CHOOSING_REACTION

    elif choice == 'delete_msg':
        try:
            await context.bot.delete_message(chat_id=chat_username, message_id=message_id)
            await query.edit_message_text("ابشر طال عمرك 🫡\nتم مسح الرسالة من القروب نهائياً. 🗑️")
        except Exception as e:
            await query.edit_message_text(f"صار خطأ ما قدرت أحذفها: {e}")
        context.user_data.clear()
        return ConversationHandler.END

    elif choice == 'cancel_action':
        await query.edit_message_text("تم الإلغاء. 🛡️")
        context.user_data.clear()
        return ConversationHandler.END

async def handle_reaction_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    chat_username = context.user_data.get('chat_username')
    message_id = context.user_data.get('message_id')

    if data == 'back_to_main':
        keyboard = [
            [InlineKeyboardButton("💬 أرد عليه بكلام", callback_data='reply_text')],
            [InlineKeyboardButton("🎭 إضافة رياكشن (كل الأنواع)", callback_data='open_reactions')],
            [InlineKeyboardButton("🗑️ حذف الرسالة", callback_data='delete_msg')],
            [InlineKeyboardButton("❌ إلغاء", callback_data='cancel_action')]
        ]
        await query.edit_message_text("وش تبي البوت يسوي؟", reply_markup=InlineKeyboardMarkup(keyboard))
        return CHOOSING_ACTION

    if data.startswith("re_"):
        emoji = data.replace("re_", "")
        try:
            await context.bot.set_message_reaction(chat_id=chat_username, message_id=message_id, reaction=[ReactionTypeEmoji(emoji)])
            await query.edit_message_text(f"تم! حطيت رياكشن {emoji} بالقروب. 😎")
        except Exception as e:
            await query.edit_message_text(f"خطأ في التفاعل: {e}")
        context.user_data.clear()
        return ConversationHandler.END

async def send_custom_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await context.bot.send_message(chat_id=context.user_data.get('chat_username'), reply_to_message_id=context.user_data.get('message_id'), text=update.message.text)
        await update.message.reply_text("تم الرد بالقروب! 🫡")
    except Exception as e: await update.message.reply_text(f"خطأ: {e}")
    context.user_data.clear()
    return ConversationHandler.END

# ================= نظام الإرسال بالخاص (/send) =================
ASK_ID, ASK_MSG, CONFIRM_SEND = range(3, 6)

async def start_send(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("أرسل آيدي الشخص:")
    return ASK_ID

async def receive_target_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.text.isdigit(): await update.message.reply_text("أرقام بس!"); return ASK_ID
    context.user_data['target_id'] = update.message.text
    await update.message.reply_text("وش الرسالة؟"); return ASK_MSG

async def receive_target_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['target_msg'] = update.message.text
    kb = [[InlineKeyboardButton("✅ تأكيد", callback_data='confirm_yes'), InlineKeyboardButton("❌ إلغاء", callback_data='confirm_no')]]
    await update.message.reply_text(f"أرسل لـ `{context.user_data['target_id']}`؟\n\n{update.message.text}", reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN)
    return CONFIRM_SEND

async def handle_send_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; await query.answer()
    if query.data == 'confirm_yes':
        try:
            await context.bot.send_message(chat_id=context.user_data['target_id'], text=context.user_data['target_msg'])
            await query.edit_message_text("تم الإرسال بنجاح! ✅")
        except Exception as e: await query.edit_message_text(f"فشل الإرسال: {e}")
    else: await query.edit_message_text("تم الإلغاء.")
    context.user_data.clear(); return ConversationHandler.END

# ================= نظام الإرسال للقروب (/post) =================
ASK_GROUP, ASK_POST_MSG, CONFIRM_POST = range(6, 9)

async def start_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(ALLOWED_GROUPS) == 1:
        context.user_data['post_group'] = ALLOWED_GROUPS[0]
        await update.message.reply_text("✏️ أرسل نص الرسالة اللي تبي ترسلها للقروب:")
        return ASK_POST_MSG
    groups_text = "\n".join([f"• `{gid}`" for gid in ALLOWED_GROUPS])
    await update.message.reply_text(f"📢 اختر القروب:\n\n{groups_text}\n\nأرسل الآيدي أو `all`:", parse_mode=ParseMode.MARKDOWN)
    return ASK_GROUP

async def receive_group_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if text.lower() == 'all': context.user_data['post_group'] = 'all'
    elif text.lstrip('-').isdigit() and int(text) in ALLOWED_GROUPS: context.user_data['post_group'] = int(text)
    else: await update.message.reply_text("⚠️ معرف خاطئ:"); return ASK_GROUP
    await update.message.reply_text("✏️ أرسل نص الرسالة:"); return ASK_POST_MSG

async def receive_post_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['post_msg'] = update.message.text
    kb = [[InlineKeyboardButton("✅ تأكيد", callback_data='post_confirm_yes'), InlineKeyboardButton("❌ إلغاء", callback_data='post_confirm_no')]]
    await update.message.reply_text(f"سيتم الإرسال لـ {context.user_data['post_group']}\n\nتأكيد؟", reply_markup=InlineKeyboardMarkup(kb))
    return CONFIRM_POST

async def handle_post_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query; await query.answer()
    if query.data == 'post_confirm_yes':
        target = context.user_data.get('post_group')
        msg_text = context.user_data.get('post_msg')
        if target == 'all':
            for gid in ALLOWED_GROUPS:
                try: await context.bot.send_message(chat_id=gid, text=msg_text)
                except: pass
            await query.edit_message_text("✅ تم الإرسال للجميع!")
        else:
            try:
                await context.bot.send_message(chat_id=target, text=msg_text)
                await query.edit_message_text("✅ تم الإرسال للقروب!")
            except Exception as e: await query.edit_message_text(f"فشل: {e}")
    else: await query.edit_message_text("❌ تم الإلغاء.")
    context.user_data.clear(); return ConversationHandler.END

# ================= ميزة Forwarding & Watermark =================
async def forward_to_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type == 'private' and update.effective_user.id != ADMIN_ID:
        user = update.effective_user
        info = f"📩 **رسالة من عضو:** {user.first_name}\n🆔 `{user.id}`\n\n{update.message.text}"
        await context.bot.send_message(chat_id=ADMIN_ID, text=info, parse_mode=ParseMode.MARKDOWN)
        await update.message.reply_text("وصلت رسالتك للإدارة! 🙏")

async def manual_save_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message; user_id = update.effective_user.id
    if not msg or not msg.reply_to_message: return
    target = msg.reply_to_message
    is_photo, is_video = bool(target.photo), bool(target.video)
    is_text = bool(target.text and not (is_photo or is_video))
    if not (is_photo or is_video or is_text): return
    if (is_video or is_text) and user_id != ADMIN_ID: return
    text_content = msg.text.lower() if msg.text else ""
    bot_username = (await context.bot.get_me()).username.lower()
    if not (any(t in text_content for t in ["حفظ", "احفظ", "جيبها", "صياد", "save"]) or f"@{bot_username}" in text_content): return

    status_msg = await msg.reply_text("ابشر طال عمرك 🫡" if user_id == ADMIN_ID else "🛡️ لحظات...")
    try:
        caption = f"✅ تم الحفظ.\n\n{target.caption if target.caption else ''}\n\n🤖 عبر بوت صياد العروض | {DEV_USERNAME}"
        if is_text: await context.bot.send_message(chat_id=user_id, text=f"✅ تم الحفظ.\n\n{target.text}\n\n🤖 @xxbassamxx")
        elif is_photo:
            file = await target.photo[-1].get_file(); stream = io.BytesIO(); await file.download_to_memory(out=stream)
            is_ex = (target.from_user.id == EXEMPT_BOT_ID) or (f"@{target.from_user.username}".lower() == EXEMPT_BOT_USERNAME.lower())
            final = stream if is_ex else await asyncio.to_thread(add_secure_watermark, stream)
            if final: final.seek(0); await context.bot.send_photo(chat_id=user_id, photo=final, caption=caption, parse_mode=ParseMode.MARKDOWN)
        elif is_video:
            file = await target.video.get_file(); stream = io.BytesIO(); await file.download_to_memory(out=stream); stream.seek(0)
            await context.bot.send_video(chat_id=user_id, video=stream, caption=caption, parse_mode=ParseMode.MARKDOWN)
        if user_id != ADMIN_ID: await status_msg.edit_text("✅ تم الإرسال للخاص.")
        await asyncio.sleep(5); await status_msg.delete(); await msg.delete()
    except Forbidden:
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("تفعيل البوت 🤖", url=f"https://t.me/{bot_username}?start=1")]])
        await status_msg.edit_text("⚠️ **يجب تفعيل البوت أولاً.**", reply_markup=kb, parse_mode=ParseMode.MARKDOWN)
    except Exception: await status_msg.delete()

# ================= التشغيل النهائي =================
if __name__ == '__main__':
    Thread(target=run_web).start()
    app_bot = ApplicationBuilder().token(TOKEN).build()

    app_bot.add_handler(CommandHandler("start", start_command))
    app_bot.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, bot_added_handler))

    # محادثة الروابط (تم إضافة حالة CHOOSING_REACTION)
    app_bot.add_handler(ConversationHandler(
        entry_points=[MessageHandler(filters.Regex(r"t\.me/.+/\d+") & filters.ChatType.PRIVATE & filters.User(ADMIN_ID), receive_link)],
        states={
            CHOOSING_ACTION: [CallbackQueryHandler(handle_button_choice)],
            WAITING_FOR_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, send_custom_reply)],
            CHOOSING_REACTION: [CallbackQueryHandler(handle_reaction_choice)]
        },
        fallbacks=[CommandHandler('cancel', lambda u,c: ConversationHandler.END)]))

    # محادثة /send
    app_bot.add_handler(ConversationHandler(
        entry_points=[CommandHandler("send", start_send, filters=filters.User(ADMIN_ID))],
        states={
            ASK_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_target_id)],
            ASK_MSG: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_target_msg)],
            CONFIRM_SEND: [CallbackQueryHandler(handle_send_confirmation)]
        },
        fallbacks=[CommandHandler('cancel', lambda u,c: ConversationHandler.END)]))

    # محادثة /post
    app_bot.add_handler(ConversationHandler(
        entry_points=[CommandHandler("post", start_post, filters=filters.User(ADMIN_ID))],
        states={
            ASK_GROUP: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_group_id)],
            ASK_POST_MSG: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_post_msg)],
            CONFIRM_POST: [CallbackQueryHandler(handle_post_confirmation)]
        },
        fallbacks=[CommandHandler('cancel', lambda u,c: ConversationHandler.END)]))

    app_bot.add_handler(MessageHandler(filters.ChatType.PRIVATE & filters.TEXT & ~filters.COMMAND & ~filters.User(ADMIN_ID), forward_to_admin))
    app_bot.add_handler(MessageHandler(filters.TEXT & filters.REPLY, manual_save_handler))

    print("✅ تم التطوير! كل الرياكشنات متاحة الآن.")
    app_bot.run_polling()