import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes, ConversationHandler
)
from datetime import datetime
import json

# ==================== CONFIG ====================
BOT_TOKEN = os.environ.get("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "123456789"))  # Your Telegram User ID

BKASH_NUMBER = os.environ.get("BKASH_NUMBER", "01XXXXXXXXX")
NAGAD_NUMBER = os.environ.get("NAGAD_NUMBER", "01XXXXXXXXX")
CRYPTO_ADDRESS = os.environ.get("CRYPTO_ADDRESS", "YOUR_USDT_TRC20_ADDRESS")

# ==================== DATABASE (JSON file based) ====================
DB_FILE = "database.json"

def load_db():
    if not os.path.exists(DB_FILE):
        return {"users": {}, "orders": {}, "pending_payments": {}}
    with open(DB_FILE, "r") as f:
        return json.load(f)

def save_db(db):
    with open(DB_FILE, "w") as f:
        json.dump(db, f, indent=2)

def get_user(user_id):
    db = load_db()
    uid = str(user_id)
    if uid not in db["users"]:
        db["users"][uid] = {"balance": 0, "orders": [], "name": ""}
        save_db(db)
    return db["users"][uid]

def update_balance(user_id, amount):
    db = load_db()
    uid = str(user_id)
    db["users"][uid]["balance"] = db["users"][uid].get("balance", 0) + amount
    save_db(db)

# ==================== PRODUCTS ====================
PRODUCTS = {
    "p1": {"name": "🌐 VPN - 1 Month", "price": 50, "description": "Premium VPN - 1 মাস", "emoji": "🌐"},
    "p2": {"name": "🌐 VPN - 3 Months", "price": 130, "description": "Premium VPN - 3 মাস (সাশ্রয়ী)", "emoji": "🌐"},
    "p3": {"name": "🎵 Music Premium - 1 Month", "price": 60, "description": "Music Streaming Premium", "emoji": "🎵"},
    "p4": {"name": "🎬 Video Streaming - 1 Month", "price": 80, "description": "HD Video Streaming", "emoji": "🎬"},
    "p5": {"name": "☁️ Cloud Storage - 1 Year", "price": 200, "description": "100GB Cloud Storage", "emoji": "☁️"},
}

# ==================== STATES ====================
WAITING_PAYMENT_PROOF = 1
WAITING_AMOUNT = 2

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ==================== MAIN MENU ====================
def main_menu_keyboard():
    return ReplyKeyboardMarkup([
        ["🛒 Buy Products", "💰 Add Balance"],
        ["📦 My Orders", "💳 My Balance"],
        ["📞 Support", "ℹ️ About"]
    ], resize_keyboard=True)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db = load_db()
    uid = str(user.id)
    if uid not in db["users"]:
        db["users"][uid] = {"balance": 0, "orders": [], "name": user.first_name}
        save_db(db)
    
    welcome_text = (
        f"╔══════════════════════╗\n"
        f"       🌟 *স্বাগতম / Welcome* 🌟\n"
        f"╚══════════════════════╝\n\n"
        f"হ্যালো *{user.first_name}* ! 👋\n\n"
        f"আমাদের প্রিমিয়াম সার্ভিস বটে আপনাকে স্বাগত!\n"
        f"Welcome to our Premium Service Bot!\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🛒 পণ্য কিনুন  |  💰 Balance যোগ করুন\n"
        f"📦 Orders দেখুন  |  💳 Balance চেক করুন\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👇 নিচের মেনু থেকে বেছে নিন:"
    )
    await update.message.reply_text(
        welcome_text, 
        parse_mode="Markdown",
        reply_markup=main_menu_keyboard()
    )

# ==================== BALANCE ====================
async def my_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_user(update.effective_user.id)
    await update.message.reply_text(
        f"💳 *আপনার Account / Your Account*\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 Name: *{update.effective_user.first_name}*\n"
        f"💰 Balance: *{user['balance']} TK*\n"
        f"📦 Total Orders: *{len(user.get('orders', []))}*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"Balance যোগ করতে 💰 *Add Balance* বাটন চাপুন।",
        parse_mode="Markdown",
        reply_markup=main_menu_keyboard()
    )

# ==================== ADD BALANCE ====================
async def add_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🟣  Bkash", callback_data="pay_bkash")],
        [InlineKeyboardButton("🟠  Nagad", callback_data="pay_nagad")],
        [InlineKeyboardButton("🟡  Binance (USDT)", callback_data="pay_crypto")],
        [InlineKeyboardButton("❌  Cancel", callback_data="cancel")],
    ]
    await update.message.reply_text(
        "💰 *Balance যোগ করুন / Add Balance*\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "👇 পেমেন্ট মেথড বেছে নিন:\n"
        "👇 Choose your payment method:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def payment_method_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    method = query.data.replace("pay_", "")
    context.user_data["payment_method"] = method
    
    if method == "bkash":
        info = (
            "🟣 *bKash Payment*\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "📲 Send Money to:\n"
            f"📞 Number: `{BKASH_NUMBER}`\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
        )
    elif method == "nagad":
        info = (
            "🟠 *Nagad Payment*\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "📲 Send Money to:\n"
            f"📞 Number: `{NAGAD_NUMBER}`\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
        )
    elif method == "crypto":
        info = (
            "🟡 *Binance / USDT (TRC20)*\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "📲 Send USDT to:\n"
            f"`{CRYPTO_ADDRESS}`\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
        )

    info += (
        "✅ *পাঠানোর পর নিচের steps follow করুন:*\n\n"
        "1️⃣  Amount লিখুন (যেমন: `100`)\n"
        "2️⃣  Transaction ID / Screenshot পাঠান\n\n"
        "⏰ সাধারণত ৩০ মিনিটের মধ্যে approve হবে।"
    )
    
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
            f"✅ Amount: *{amount} TK*\n\n"
            f"এখন Transaction ID অথবা Screenshot পাঠান:\n"
            f"Now send Transaction ID or Screenshot:",
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
    
    # Save pending payment
    db = load_db()
    payment_id = f"PAY{datetime.now().strftime('%Y%m%d%H%M%S')}{user.id}"
    db["pending_payments"][payment_id] = {
        "user_id": str(user.id),
        "user_name": user.first_name,
        "amount": amount,
        "method": method,
        "status": "pending",
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    save_db(db)
    
    # Notify admin
    proof_text = update.message.text if update.message.text else "📷 Screenshot sent"
    admin_msg = (
        f"🔔 *নতুন Payment Request!*\n\n"
        f"👤 User: {user.first_name} (ID: `{user.id}`)\n"
        f"💰 Amount: *{amount} TK*\n"
        f"📱 Method: {method.upper()}\n"
        f"🆔 Payment ID: `{payment_id}`\n"
        f"📝 Proof: {proof_text}\n\n"
        f"✅ Approve করতে:\n`/approve {payment_id}`\n"
        f"❌ Reject করতে:\n`/reject {payment_id}`"
    )
    
    try:
        if update.message.photo:
            await context.bot.send_photo(
                ADMIN_ID, 
                update.message.photo[-1].file_id,
                caption=admin_msg,
                parse_mode="Markdown"
            )
        else:
            await context.bot.send_message(ADMIN_ID, admin_msg, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Could not notify admin: {e}")
    
    await update.message.reply_text(
        f"✅ *Payment Request পাঠানো হয়েছে!*\n\n"
        f"🆔 Payment ID: `{payment_id}`\n"
        f"💰 Amount: {amount} TK\n\n"
        f"আমরা শীঘ্রই verify করব। সাধারণত 30 মিনিটের মধ্যে।\n"
        f"We'll verify soon. Usually within 30 minutes.",
        parse_mode="Markdown",
        reply_markup=main_menu_keyboard()
    )
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text("❌ Cancelled")
    else:
        await update.message.reply_text("❌ Cancelled", reply_markup=main_menu_keyboard())
    return ConversationHandler.END

# ==================== BUY PRODUCTS ====================
async def buy_products(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = []
    for pid, product in PRODUCTS.items():
        keyboard.append([InlineKeyboardButton(
            f"{product['emoji']}  {product['name']}  ─  {product['price']} TK",
            callback_data=f"buy_{pid}"
        )])
    keyboard.append([InlineKeyboardButton("❌  Cancel", callback_data="cancel")])

    await update.message.reply_text(
        "🛒 *পণ্য তালিকা / Product List*\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "👇 পছন্দের পণ্য বেছে নিন:\n"
        "👇 Choose your product below:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
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
    
    balance_status = "✅ পর্যাপ্ত ব্যালেন্স আছে" if user["balance"] >= product["price"] else "❌ ব্যালেন্স কম! Add Balance করুন"
    
    await query.edit_message_text(
        f"{product['emoji']} *{product['name']}*\n\n"
        f"📝 {product['description']}\n"
        f"💰 Price: *{product['price']} TK*\n\n"
        f"💳 আপনার Balance: *{user['balance']} TK*\n"
        f"{balance_status}",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def confirm_purchase(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    pid = query.data.replace("confirm_", "")
    product = PRODUCTS.get(pid)
    user_data = get_user(query.from_user.id)
    
    if user_data["balance"] < product["price"]:
        await query.edit_message_text(
            "❌ *ব্যালেন্স কম!*\n\nআগে Add Balance করুন।\nPlease add balance first.",
            parse_mode="Markdown"
        )
        return
    
    # Deduct balance and create order
    update_balance(query.from_user.id, -product["price"])
    
    db = load_db()
    order_id = f"ORD{datetime.now().strftime('%Y%m%d%H%M%S')}"
    order = {
        "order_id": order_id,
        "product": product["name"],
        "price": product["price"],
        "status": "pending",
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    uid = str(query.from_user.id)
    db["users"][uid]["orders"].append(order)
    save_db(db)
    
    # Notify admin
    admin_msg = (
        f"🛒 *নতুন Order!*\n\n"
        f"👤 User: {query.from_user.first_name} (ID: `{query.from_user.id}`)\n"
        f"📦 Product: {product['name']}\n"
        f"💰 Price: {product['price']} TK\n"
        f"🆔 Order ID: `{order_id}`\n\n"
        f"Deliver করতে:\n`/deliver {order_id} {query.from_user.id} <details>`"
    )
    try:
        await context.bot.send_message(ADMIN_ID, admin_msg, parse_mode="Markdown")
    except:
        pass
    
    new_balance = get_user(query.from_user.id)["balance"]
    await query.edit_message_text(
        f"✅ *Order সফল! / Order Successful!*\n\n"
        f"📦 {product['name']}\n"
        f"💰 Paid: {product['price']} TK\n"
        f"💳 Remaining Balance: {new_balance} TK\n"
        f"🆔 Order ID: `{order_id}`\n\n"
        f"শীঘ্রই আপনার কাছে পৌঁছে দেওয়া হবে।\nWill be delivered soon!",
        parse_mode="Markdown"
    )

# ==================== MY ORDERS ====================
async def my_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = get_user(update.effective_user.id)
    orders = user_data.get("orders", [])
    
    if not orders:
        await update.message.reply_text(
            "📦 *আপনার কোনো Order নেই।*\n\nYou have no orders yet.\n\nপণ্য কিনতে 'Buy Products' চাপুন।",
            parse_mode="Markdown",
            reply_markup=main_menu_keyboard()
        )
        return
    
    text = "📦 *আপনার Orders / Your Orders:*\n\n"
    for order in orders[-5:]:  # Show last 5
        status_emoji = "✅" if order["status"] == "delivered" else "⏳"
        text += f"{status_emoji} {order['product']}\n"
        text += f"   💰 {order['price']} TK | 🆔 `{order['order_id']}`\n"
        text += f"   📅 {order['time']}\n\n"
    
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=main_menu_keyboard())

# ==================== SUPPORT ====================
async def support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📞 *Support / সাপোর্ট*\n\n"
        "যেকোনো সমস্যায় আমাদের সাথে যোগাযোগ করুন:\n"
        "For any issues, contact us:\n\n"
        "👤 Admin: @YourAdminUsername\n"
        "⏰ সময়: সকাল ৯টা - রাত ১১টা\n"
        "⏰ Time: 9 AM - 11 PM",
        parse_mode="Markdown",
        reply_markup=main_menu_keyboard()
    )

# ==================== ADMIN COMMANDS ====================
async def approve_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    
    if not context.args:
        await update.message.reply_text("Usage: /approve <payment_id>")
        return
    
    payment_id = context.args[0]
    db = load_db()
    
    if payment_id not in db["pending_payments"]:
        await update.message.reply_text("❌ Payment ID not found!")
        return
    
    payment = db["pending_payments"][payment_id]
    user_id = int(payment["user_id"])
    amount = payment["amount"]
    
    update_balance(user_id, amount)
    db["pending_payments"][payment_id]["status"] = "approved"
    save_db(db)
    
    # Notify user
    try:
        await context.bot.send_message(
            user_id,
            f"✅ *Payment Approved!*\n\n"
            f"💰 *{amount} TK* আপনার account এ যোগ হয়েছে!\n"
            f"💰 *{amount} TK* has been added to your account!\n\n"
            f"🆔 Payment ID: `{payment_id}`",
            parse_mode="Markdown"
        )
    except:
        pass
    
    await update.message.reply_text(f"✅ Payment approved! {amount} TK added for user {user_id}")

async def reject_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    
    if not context.args:
        await update.message.reply_text("Usage: /reject <payment_id>")
        return
    
    payment_id = context.args[0]
    db = load_db()
    
    if payment_id not in db["pending_payments"]:
        await update.message.reply_text("❌ Payment ID not found!")
        return
    
    payment = db["pending_payments"][payment_id]
    db["pending_payments"][payment_id]["status"] = "rejected"
    save_db(db)
    
    try:
        await context.bot.send_message(
            int(payment["user_id"]),
            f"❌ *Payment Rejected*\n\n"
            f"আপনার payment verify করা যায়নি।\n"
            f"Your payment could not be verified.\n\n"
            f"সাহায্যের জন্য Support এ যোগাযোগ করুন।",
            parse_mode="Markdown"
        )
    except:
        pass
    
    await update.message.reply_text("❌ Payment rejected and user notified.")

async def deliver_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    
    if len(context.args) < 3:
        await update.message.reply_text("Usage: /deliver <order_id> <user_id> <details>")
        return
    
    order_id = context.args[0]
    target_user_id = int(context.args[1])
    details = " ".join(context.args[2:])
    
    # Update order status
    db = load_db()
    uid = str(target_user_id)
    if uid in db["users"]:
        for order in db["users"][uid]["orders"]:
            if order["order_id"] == order_id:
                order["status"] = "delivered"
    save_db(db)
    
    try:
        await context.bot.send_message(
            target_user_id,
            f"🎉 *আপনার Order Deliver হয়েছে!*\n\n"
            f"🆔 Order ID: `{order_id}`\n\n"
            f"📦 Details:\n{details}\n\n"
            f"ধন্যবাদ! Thank you!",
            parse_mode="Markdown"
        )
        await update.message.reply_text("✅ Order delivered and user notified!")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")

async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    db = load_db()
    total_users = len(db["users"])
    pending = sum(1 for p in db["pending_payments"].values() if p["status"] == "pending")
    await update.message.reply_text(
        f"📊 *Bot Stats*\n\n"
        f"👥 Total Users: {total_users}\n"
        f"⏳ Pending Payments: {pending}\n",
        parse_mode="Markdown"
    )

async def handle_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "🛒 Buy Products":
        await buy_products(update, context)
    elif text == "💰 Add Balance":
        await add_balance(update, context)
    elif text == "📦 My Orders":
        await my_orders(update, context)
    elif text == "💳 My Balance":
        await my_balance(update, context)
    elif text == "📞 Support":
        await support(update, context)

# ==================== MAIN ====================
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Conversation handler for payment
    payment_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(payment_method_selected, pattern="^pay_")],
        states={
            WAITING_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_amount)],
            WAITING_PAYMENT_PROOF: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_payment_proof),
                MessageHandler(filters.PHOTO, receive_payment_proof),
            ],
        },
        fallbacks=[
            CallbackQueryHandler(cancel, pattern="^cancel$"),
            CommandHandler("cancel", cancel),
        ],
    )
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("approve", approve_payment))
    app.add_handler(CommandHandler("reject", reject_payment))
    app.add_handler(CommandHandler("deliver", deliver_order))
    app.add_handler(CommandHandler("stats", admin_stats))
    app.add_handler(payment_conv)
    app.add_handler(CallbackQueryHandler(product_selected, pattern="^buy_"))
    app.add_handler(CallbackQueryHandler(confirm_purchase, pattern="^confirm_"))
    app.add_handler(CallbackQueryHandler(cancel, pattern="^cancel$"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_menu))
    
    print("🤖 Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
