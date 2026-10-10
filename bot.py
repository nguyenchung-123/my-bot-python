import os
import json
import random
import string
from datetime import datetime, timedelta
from flask import Flask, request, jsonify
from flask_cors import CORS
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# --- CẤU HÌNH FLASK & CORS ---
app = Flask(__name__)
CORS(app)

DB_FILE = 'database.json'
SUPER_ADMIN_ID = 6478447629  # ID Telegram quyền cao nhất

def load_db():
    if not os.path.exists(DB_FILE):
        return {
            "admins": [str(SUPER_ADMIN_ID)],
            "keys": {}
        }
    try:
        with open(DB_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if "admins" not in data:
                data["admins"] = [str(SUPER_ADMIN_ID)]
            if "keys" not in data:
                data["keys"] = {}
            return data
    except:
        return {
            "admins": [str(SUPER_ADMIN_ID)],
            "keys": {}
        }

def save_db(data):
    with open(DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# --- LỆNH CẤP QUYỀN ADMIN (/addadmin) ---
async def add_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if user_id != str(SUPER_ADMIN_ID):
        await update.message.reply_text("❌ Bạn không có quyền sử dụng lệnh này!")
        return
        
    args = context.args
    if not args or not args[0].isdigit():
        await update.message.reply_text("⚠️ Cú pháp: `/addadmin <telegram_id>`", parse_mode="Markdown")
        return
        
    new_admin_id = args[0]
    db = load_db()
    if new_admin_id in db["admins"]:
        await update.message.reply_text(f"ℹ️ ID `{new_admin_id}` đã là Admin từ trước!", parse_mode="Markdown")
        return
        
    db["admins"].append(new_admin_id)
    save_db(db)
    await update.message.reply_text(f"✅ Đã cấp quyền Admin cho ID: `{new_admin_id}`", parse_mode="Markdown")

# --- LỆNH TẠO KEY (/createkey) ---
async def create_key(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    db = load_db()
    
    if user_id not in db["admins"]:
        await update.message.reply_text("❌ Bạn không có quyền tạo key!")
        return
        
    args = context.args
    days = int(args[0]) if args and args[0].isdigit() else 1
    
    random_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
    key = f"DRAKON-{random_str[:4]}-{random_str[4:]}"
    expires_at = (datetime.now() + timedelta(days=days)).strftime('%Y-%m-%d %H:%M:%S')
    
    db["keys"][key] = {
        "expires_at": expires_at,
        "device_id": None,
        "created_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "created_by": user_id
    }
    save_db(db)
    
    await update.message.reply_text(
        f"✅ **Tạo Key Thành Công!**\n\n"
        f"🔑 Key: `{key}`\n"
        f"⏳ Thời hạn: {days} ngày\n"
        f"📅 Hết hạn: {expires_at}",
        parse_mode="Markdown"
    )

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🤖 Bot quản lý Key Drakon Head đang hoạt động!")

# --- FLASK API XÁC THỰC ---
@app.route('/api/verify', methods=['POST'])
def verify_key():
    data = request.json or {}
    user_key = data.get('key', '').strip()
    device_id = data.get('device_id', 'unknown').strip()
    
    if not user_key:
        return jsonify({"status": "error", "message": "Vui lòng nhập key!"}), 400
        
    db = load_db()
    keys_db = db["keys"]
    
    if user_key not in keys_db:
        return jsonify({"status": "error", "message": "Key không tồn tại!"}), 404
        
    key_info = keys_db[user_key]
    expires_at = datetime.strptime(key_info['expires_at'], '%Y-%m-%d %H:%M:%S')
    
    if datetime.now() > expires_at:
        return jsonify({"status": "error", "message": "Key đã hết hạn!"}), 400
        
    if key_info['device_id'] is None:
        key_info['device_id'] = device_id
        save_db(db)
    elif key_info['device_id'] != device_id:
        return jsonify({"status": "error", "message": "Key đã kích hoạt trên thiết bị khác!"}), 400
        
    return jsonify({
        "status": "success",
        "message": "Xác thực thành công!",
        "expires_at": key_info['expires_at']
    })

@app.route('/', methods=['GET'])
def home():
    return "Drakon Bot & API Server is running smoothly!", 200

# --- KHỞI CHẠY ---
if __name__ == '__main__':
    import threading
    port = int(os.environ.get("PORT", 5000))
    
    def run_flask():
        app.run(host='0.0.0.0', port=port)
        
    threading.Thread(target=run_flask, daemon=True).start()
    
    TOKEN = "8855559629:AAHSvaBw7YbC1H8dO1bI3T-t54XHbqVDX1s"
    application = ApplicationBuilder().token(TOKEN).build()
    
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("addadmin", add_admin))
    application.add_handler(CommandHandler("createkey", create_key))
    
    print("🤖 Bot Telegram và Flask API đang khởi chạy...")
    application.run_polling()
