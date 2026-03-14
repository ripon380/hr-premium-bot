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
    "p1": {"name": "VPN - 1 Month", "price": 50, "description": "Premium VPN - 1 mas", "emoji": "VPN"},
    "p2": {"name": "VPN - 3 Months", "price": 130, "description": "Premium VPN - 3 mas", "emoji": "VPN"},
    "p3": {"name": "Music Premium - 1 Month", "price": 60, "description": "Music Streaming Premium", "emoji": "Music"},
    "p4": {"name": "Video Streaming - 1 Month", "price": 80, "description": "HD Video Streaming", "emoji": "Video"},
    "p5": {"name": "Cloud Storage - 1 Year", "price": 200, "description": "100GB Cloud Storage", "emoji": "Cloud"},
}

WAITING_PAYMENT_PROOF = 1
WAITING_AMOUNT = 2

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main_menu_keyboard():
    return ReplyKeyboardMarkup([
        ["Buy Products", "Add Balance"],
        ["My Orders", "My Balance"],
        ["Support", "About"]
    ], resize_keyboard=True)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    uid = str(user.id)
    existing = users_col.find_one({"_id": uid})
    if not existing:
        users_col.insert_one({"_id": uid, "balance": 0, "orders": [], "name": user.first_name})
    welcome_text = (
        "*╔══════════════════════╗*\n"
        "*    HR Premium Store   *\n"
        "*╚══════════════════════╝*\n\n"
        "আসসালামু আলাইকুম *" + user.first_name + "* ভাই! 👋\n\n"
        "আপনাকে স্বাগতম আমাদের *HR Premium Store* এ!\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "এখানে আপনি পাবেন:\n"
        "🌐 সেরা দামে *VPN* সার্ভিস\n"
        "🎵 *Music* Premium একাউন্ট\n"
        "🎬 *Video Streaming* সার্ভিস\n"
        "☁️ *Cloud Storage* সুবিধা\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "💰 *সাশ্রয়ী মূল্যে* সেরা সার্ভিস!\n"
        "⚡ *দ্রুত ডেলিভারি* নিশ্চিত!\n"
        "✅ *বিশ্বস্ত সেবা* সবসময়!\n\n"
        "👇 নিচের মেনু থেকে শুরু করুন:"
    )
    await update.message.reply_text(welcome_text, parse_mode="Markdown", reply_markup=main_menu_keyboard())

async def my_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_user(update.effective_user.id)
    text = (
        "*Your Account*\n\n"
        "Name: *" + update.effective_user.first_name + "*\n"
        "Balance: *" + str(user['balance']) + " TK*\n"
        "Total Orders: *" + str(len(user.get('orders', []))) + "*\n\n"
        "To add balance press *Add Balance*."
    )
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=main_menu_keyboard())

async def add_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Bkash", callback_data="pay_bkash")],
        [InlineKeyboardButton("Nagad", callback_data="pay_nagad")],
        [InlineKeyboardButton("Binance USDT", callback_data="pay_crypto")],
        [InlineKeyboardButton("Cancel", callback_data="cancel")],
    ]
    await update.message.reply_text(
        "*Add Balance*\n\nChoose payment method:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def payment_method_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    method = query.data.replace("pay_", "")
    context.user_data["payment_method"] = method
    if method == "bkash":
        info = "*bKash Payment*\n\nSend Money to:\nNumber: `" + BKASH_NUMBER + "`\n\n"
    elif method == "nagad":
        info = "*Nagad Payment*\n\nSend Money to:\nNumber: `" + NAGAD_NUMBER + "`\n\n"
    elif method == "crypto":
        info = "*Binance USDT TRC20*\n\nSend to:\n`" + CRYPTO_ADDRESS + "`\n\n"
    else:
        info = "*Payment*\n\n"
    info += "1. Write Amount (e.g: `100`)\n2. Send Screenshot\n\nUsually approved within 30 minutes."
    await query.edit_message_text(info, parse_mode="Markdown")
    return WAITING_AMOUNT

async def receive_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        amount = int(update.message.text.strip())
        if amount < 10:
            await update.message.reply_text("Minimum amount is 10 TK")
            return WAITING_AMOUNT
        context.user_data["payment_amount"] = amount
        await update.message.reply_text(
            "Amount: *" + str(amount) + " TK*\n\nNow send Transaction ID or Screenshot:",
            parse_mode="Markdown"
        )
        return WAITING_PAYMENT_PROOF
    except Exception:
        await update.message.reply_text("Please write numbers only. Example: 100")
        return WAITING_AMOUNT

async def receive_payment_proof(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    amount = context.user_data.get("payment_amount", 0)
    method = context.user_data.get("payment_method", "unknown")
    payment_id = "PAY" + datetime.now().strftime('%Y%m%d%H%M%S') + str(user.id)
    payments_col.insert_one({
        "_id": payment_id,
        "user_id": str(user.id),
        "user_name": user.first_name,
        "amount": amount,
        "method": method,
        "status": "pending",
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })
    proof_text = update.message.text if update.message.text else "Screenshot sent"
    admin_msg = (
        "*New Payment Request!*\n\n"
        "User: " + user.first_name + " (ID: `" + str(user.id) + "`)\n"
        "Amount: *" + str(amount) + " TK*\n"
        "Method: " + method.upper() + "\n"
        "Payment ID: `" + payment_id + "`\n"
        "Proof: " + proof_text + "\n\n"
        "Approve: `/approve " + payment_id + "`\n"
        "Reject: `/reject " + payment_id + "`"
    )
    try:
        if update.message.photo:
            await context.bot.send_photo(ADMIN_ID, update.message.photo[-1].file_id, caption=admin_msg, parse_mode="Markdown")
        else:
            await context.bot.send_message(ADMIN_ID, admin_msg, parse_mode="Markdown")
    except Exception as e:
        logger.error("Could not notify admin: " + str(e))
    await update.message.reply_text(
        "*Payment Request Sent!*\n\nID: `" + payment_id + "`\nAmount: " + str(amount) + " TK\n\nWe will verify within 30 minutes.",
        parse_mode="Markdown",
        reply_markup=main_menu_keyboard()
    )
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text("Cancelled")
    else:
        await update.message.reply_text("Cancelled", reply_markup=main_menu_keyboard())
    return ConversationHandler.END

async def buy_products(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = []
    for pid, product in PRODUCTS.items():
        keyboard.append([InlineKeyboardButton(
            product['name'] + " - " + str(product['price']) + " TK",
            callback_data="buy_" + pid
        )])
    keyboard.append([InlineKeyboardButton("Cancel", callback_data="cancel")])
    await update.message.reply_text(
        "*Product List*\n\nChoose your product:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def product_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    pid = query.data.replace("buy_", "")
    product = PRODUCTS.get(pid)
    if not product:
        await query.edit_message_text("Product not found!")
        return
    user = get_user(query.from_user.id)
    keyboard = [
        [InlineKeyboardButton("Buy Now", callback_data="confirm_" + pid)],
        [InlineKeyboardButton("Cancel", callback_data="cancel")]
    ]
    if user["balance"] >= product["price"]:
        balance_status = "Balance is enough"
    else:
        balance_status = "Not enough balance! Please Add Balance."
    text = (
        "*" + product['name'] + "*\n\n"
        + product['description'] + "\n"
        "Price: *" + str(product['price']) + " TK*\n\n"
        "Your Balance: *" + str(user['balance']) + " TK*\n"
        + balance_status
    )
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

async def confirm_purchase(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    pid = query.data.replace("confirm_", "")
    product = PRODUCTS.get(pid)
    user_data = get_user(query.from_user.id)
    if user_data["balance"] < product["price"]:
        await query.edit_message_text("Not enough balance! Please add balance first.")
        return
    update_balance(query.from_user.id, -product["price"])
    order_id = "ORD" + datetime.now().strftime('%Y%m%d%H%M%S')
    order = {
        "order_id": order_id,
        "product": product["name"],
        "price": product["price"],
        "status": "pending",
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    users_col.update_one({"_id": str(query.from_user.id)}, {"$push": {"orders": order}})
    try:
        await context.bot.send_message(
            ADMIN_ID,
            "*New Order!*\n\nUser: " + query.from_user.first_name + " (ID: `" + str(query.from_user.id) + "`)\nProduct: " + product['name'] + "\nPrice: " + str(product['price']) + " TK\nOrder ID: `" + order_id + "`\n\nDeliver: `/deliver " + order_id + " " + str(query.from_user.id) + " <details>`",
            parse_mode="Markdown"
        )
    except Exception:
        pass
    new_balance = get_user(query.from_user.id)["balance"]
    await query.edit_message_text(
        "*Order Successful!*\n\nProduct: " + product['name'] + "\nPaid: " + str(product['price']) + " TK\nRemaining Balance: " + str(new_balance) + " TK\nOrder ID: `" + order_id + "`\n\nWill be delivered soon!",
        parse_mode="Markdown"
    )

async def my_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = get_user(update.effective_user.id)
    orders = user_data.get("orders", [])
    if not orders:
        await update.message.reply_text("No orders yet.\n\nPress Buy Products to buy.", reply_markup=main_menu_keyboard())
        return
    text = "*Your Orders:*\n\n"
    for order in orders[-5:]:
        status_emoji = "Done" if order["status"] == "delivered" else "Pending"
        text += status_emoji + " " + order['product'] + "\n"
        text += str(order['price']) + " TK | ID: `" + order['order_id'] + "`\n"
        text += order['time'] + "\n\n"
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=main_menu_keyboard())

async def support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "*Support*\n\nContact: @YourAdminUsername\nTime: 9 AM - 11 PM",
        parse_mode="Markdown",
        reply_markup=main_menu_keyboard()
    )

async def approve_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    if not context.args:
        await update.message.reply_text("Usage: /approve <payment_id>")
        return
    payment_id = context.args[0]
    payment = payments_col.find_one({"_id": payment_id})
    if not payment:
        await update.message.reply_text("Payment ID not found!")
        return
    user_id = int(payment["user_id"])
    amount = payment["amount"]
    update_balance(user_id, amount)
    payments_col.update_one({"_id": payment_id}, {"$set": {"status": "approved"}})
    try:
        await context.bot.send_message(
            user_id,
            "*Payment Approved!*\n\n" + str(amount) + " TK added to your account!\nPayment ID: `" + payment_id + "`",
            parse_mode="Markdown"
        )
    except Exception:
        pass
    await update.message.reply_text("Payment approved! " + str(amount) + " TK added for user " + str(user_id))

async def reject_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    if not context.args:
        await update.message.reply_text("Usage: /reject <payment_id>")
        return
    payment_id = context.args[0]
    payment = payments_col.find_one({"_id": payment_id})
    if not payment:
        await update.message.reply_text("Payment ID not found!")
        return
    payments_col.update_one({"_id": payment_id}, {"$set": {"status": "rejected"}})
    try:
        await context.bot.send_message(
            int(payment["user_id"]),
            "*Payment Rejected*\n\nYour payment could not be verified.\nContact support for help.",
            parse_mode="Markdown"
        )
    except Exception:
        pass
    await update.message.reply_text("Payment rejected.")

async def deliver_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    if len(context.args) < 3:
        await update.message.reply_text("Usage: /deliver <order_id> <user_id> <details>")
        return
    order_id = context.args[0]
    target_user_id = int(context.args[1])
    details = " ".join(context.args[2:])
    users_col.update_one(
        {"_id": str(target_user_id), "orders.order_id": order_id},
        {"$set": {"orders.$.status": "delivered"}}
    )
    try:
        await context.bot.send_message(
            target_user_id,
            "*Order Delivered!*\n\nOrder ID: `" + order_id + "`\n\nDetails:\n" + details + "\n\nThank you!",
            parse_mode="Markdown"
        )
        await update.message.reply_text("Order delivered!")
    except Exception as e:
        await update.message.reply_text("Error: " + str(e))

async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    total_users = users_col.count_documents({})
    pending = payments_col.count_documents({"status": "pending"})
    await update.message.reply_text(
        "*Bot Stats*\n\nUsers: " + str(total_users) + "\nPending Payments: " + str(pending),
        parse_mode="Markdown"
    )

async def handle_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "Buy Products":
        await buy_products(update, context)
    elif text == "Add Balance":
        await add_balance(update, context)
    elif text == "My Orders":
        await my_orders(update, context)
    elif text == "My Balance":
        await my_balance(update, context)
    elif text == "Support":
        await support(update, context)

def main():
    app = Application.builder().token(BOT_TOKEN).build()
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
    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
