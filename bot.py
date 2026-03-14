import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes, ConversationHandler
)
from datetime import datetime
from pymongo import MongoClient

BOT_TOKEN = os.environ.get("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "123456789"))
BKASH_NUMBER = os.environ.get("BKASH_NUMBER", "01XXXXXXXXX")
NAGAD_NUMBER = os.environ.get("NAGAD_NUMBER", "01XXXXXXXXX")
CRYPTO_ADDRESS = os.environ.get("CRYPTO_ADDRESS", "YOUR_USDT_TRC20_ADDRESS")
MONGODB_URI = os.environ.get("MONGODB_URI", "")

client = MongoClient(MONGODB_URI)
db_mongo = client["hrbot"]
users_col = db_mongo["users"]
payments_col = db_mongo["payments"]
orders_col = db_mongo["orders"]

def get_user(user_id):
    uid = str(user_id)
    user = users_col.find_one({"_id": uid})
    if not user:
        user = {"_id": uid, "balance": 0, "orders": [], "name": ""}
        users_col.insert_one(user)
    return user

def update_balance(user_id, amount):
    uid = str(user_id)
    users_col.update_one({"_id": uid}, {"$inc": {"balance": amount}}, upsert=True)

PRODUCTS = {
    "p1": {"name": "🌐 VPN - 1 Month", "price": 50, "description": "Premium VPN - 1 মাস", "emoji": "🌐"},
    "p2": {"name": "🌐 VPN - 3 Months", "price": 130, "description": "Premium VPN - 3 মাস", "emoji": "🌐"},
    "p3": {"name": "🎵 Music Premium - 1 Month", "price": 60, "description": "Music Streaming Premium", "emoji": "🎵"},
    "p4": {"name": "🎬 Video Streaming - 1 Month", "price": 80, "description": "HD Video Streaming", "emoji": "🎬"},
    "p5": {"name": "☁️ Cloud Storage - 1 Year", "price": 200, "description": "100GB Cloud Storage", "emoji": "☁️"},
}

WAITING_PAYMENT_PROOF = 1
WAITING_AMOUNT = 2

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main_menu_keyboard():
    return ReplyKeyboardMarkup([
        ["🛒 Buy Products", "💰 Add Balance"],
        ["📦 My Orders", "💳 My Balance"],
        ["📞 Support", "ℹ️ About"]
    ], resize_keyboard=True)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    uid = str(user.id)
    existing = users_col.find_one({"_id": uid})
    if not existing:
        users_col.insert_one({"_id": uid, "balance": 0, "orders": [], "name": user.first_name})
    welcome_text = (
        f"╔══════════════════════╗\n"
        f"       🌟 *স্বাগতম / Welcome* 🌟\n"
        f"╚══════════════════════╝\n\n"
        f"হ্যালো *{user.first_name}* ! 👋\n\n"
        f"আমাদের প্রিমিয়াম সার্ভিস বটে আপনাকে স্বাগত!\n\n"
        f"👇 নিচের মেনু থেকে বেছে নিন:"
    )
    await update.message.reply_text(welcome_text, parse_mode="Markdown", reply_markup=main_menu_keyboard())

async def my_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_user(update.effective_user.id)
    await update.message.reply_text(
        f"💳 *আপনার Account*\n\n"
        f"👤 Name: *{update.effective_user.first_name}*\n"
        f"💰 Balance: *{user['balance']} TK*\n"
        f"📦 Total Orders: *{len(user.get('orders', []))}*\n\n"
        f"Balance যোগ করতে 💰 *Add Balance* বাটন চাপুন।",
        parse_mode="Markdown", reply_markup=main_menu_keyboard()
    )

async def add_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🟣 Bkash", callback_data="pay_bkash")],
        [InlineKeyboardButton("🟠 Nagad", callback_data="pay_nagad")],
        [InlineKeyboardButton("🟡 Binance (USDT)", callback_data="pay_crypto")],
        [InlineKeyboardButton("❌ Cancel", callback_data="cancel")],
    ]
    await update.message.reply_text(
        "💰 *Balance যোগ করুন*\n\n👇 পেমেন্ট মেথড বেছে নিন:",
        parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def payment_method_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    method = query.data.replace("pay_", "")
    context.user_data["payment_method"] = method
    if method == "bkash":
        info = f"🟣 *bKash Payment*\n\n📞 Number: `{BKASH_NUMBER}`\n\n"
    elif method == "nagad":
        info = f"🟠 *Nagad Payment*\n\n📞 Number: `{NAGAD_NUMBER}`\n\n"
    elif method == "crypto":
        info = f"🟡 *Binance / USDT (TRC20)*\n\n`{CRYPTO_ADDRESS}`\n\n"
    info += "1️⃣ Amount লিখুন (যেমন: `100`)\n2️⃣ Screenshot পাঠান"
    await query.edit_message_text(info, parse_mode="Markdown")
    return WAITING_AMOUNT

async def receive_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        amount = int(update.message.text.strip())
        if amount < 10:
            await update.message.reply_text("❌ Minimum amount is 10 TK")
            return WAITING_AMOUNT
        context.user_data["payment_amount"] = amount
        await update.message.reply_text(
            f"✅ Amount: *{amount} TK*\n\nএখন Screenshot বা Transaction ID পাঠান:",
            parse_mode="Markdown"
        )
        return WAITING_PAYMENT_PROOF
    except:
        await update.message.reply_text("❌ শুধু সংখ্যা লিখুন। Example: 100")
        return WAITING_AMOUNT

async def receive_payment_proof(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    amount = context.user_data.get("payment_amount", 0)
    method = context.user_data.get("payment_method", "unknown")
    payment_id = f"PAY{datetime.now().strftime('%Y%m%d%H%M%S')}{user.id}"
    payments_col.insert_one({
        "_id": payment_id,
        "user_id": str(user.id),
        "user_name": user.first_name,
        "amount": amount,
        "method": method,
        "status": "pending",
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })
    proof_text = update.message.text if update.message.text else "📷 Screenshot sent"
    admin_msg = (
        f"🔔 *নতুন Payment Request!*\n\n"
        f"👤 User: {user.first_name} (ID: `{user.id}`)\n"
        f"💰 Amount: *{amount} TK*\n"
        f"📱 Method: {method.upper()}\n"
        f"🆔 Payment ID: `{payment_id}`\n"
        f"📝 Proof: {proof_text}\n\n"
        f"✅ Approve: `/approve {payment_id}`\n"
        f"❌ Reject: `/reject {payment_id}`"
    )
    try:
        if update.message.photo:
            await context.bot.send_photo(ADMIN_ID, update.message.photo[-1].file_id, caption=admin_msg, parse_mode="Markdown")
        else:
            await context.bot.send_message(ADMIN_ID, admin_msg, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Could not notify admin: {e}")
    await update.message.reply_text(
        f"✅ *Payment Request পাঠানো হয়েছে!*\n\n🆔 `{payment_id}`\n💰 {amount} TK\n\nসাধারণত 30 মিনিটের মধ্যে verify হবে।",
        parse_mode="Markdown", reply_markup=main_menu_keyboard()
    )
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text("❌ Cancelled")
    else:
        await update.message.reply_text("❌ Cancelled", reply_markup=main_menu_keyboard())
    return ConversationHandler.END

async def buy_products(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = []
    for pid, product in PRODUCTS.items():
        keyboard.append([InlineKeyboardButton(
            f"{product['emoji']} {product['name']} ─ {product['price']} TK",
            callback_data=f"buy_{pid}"
        )])
    keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data="cancel")])
    await update.message.reply_text(
        "🛒 *পণ্য তালিকা*\n\n👇 পছন্দের পণ্য বেছে নিন:",
        parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def product_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    pid = query.data.replace("buy_", "")
    product = PRODUCTS.get(pid)
    if not product:
        await query.edit_message_text("❌ Product not found!")
        return
    user = get_user(query.from_user.id)
    keyboard = [
        [InlineKeyboardButton("✅ কিনুন / Buy Now", callback_data=f"confirm_{pid}")],
        [InlineKeyboardButton("❌ Cancel", callback_data="cancel")]
    ]
    balance_status = "✅ পর্যাপ্ত ব্যালেন্স আছে" if user["balance"] >= product["price"] else "❌ ব্যালেন্স কম!"
    await query.edit_message_text(
        f"{product['emoji']} *{product['name']}*\n\n💰 Price: *{product['price']} TK*\n💳 আপনার Balance: *{user['balance']} TK*\n{balance_status}",
        parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def confirm_purchase(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    pid = query.data.replace("confirm_", "")
    product = PRODUCTS.get(pid)
    user_data = get_user(query.from_user.id)
    if user_data["balance"] < product["price"]:
        await query.edit_message_text("❌ *ব্যালেন্স কম!*\n\nআগে Add Balance করুন।", parse_mode="Markdown")
        return
    update_balance(query.from_user.id, -product["price"])
    order_id = f"ORD{datetime.now().strftime('%Y%m%d%H%M%S')}"
    order = {"order_id": order_id, "product": product["name"], "price": product["price"], "status": "pending", "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
    users_col.update_one({"_id": str(query.from_user.id)}, {"$push": {"orders": order}})
    try:
        await context.bot.send_message(ADMIN_ID,
            f"🛒 *নতুন Order!*\n\n👤 {query.from_user.first_name} (ID: `{query.from_user.id}`)\n📦 {product['name']}\n💰 {product['price']} TK\n🆔 `{order_id}`\n\nDeliver: `/deliver {order_id} {query.from_user.id} <details>`",
            parse_mode="Markdown")
    except:
        pass
    new_balance = get_user(query.from_user.id)["balance"]
    await query.edit_message_text(
        f"✅ *Order সফল!*\n\n📦 {product['name']}\n💰 Paid: {product['price']} TK\
