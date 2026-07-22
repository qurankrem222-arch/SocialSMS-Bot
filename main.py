import asyncio
import logging
import json
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, CommandObject
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton, LabeledPrice
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

BOT_TOKEN = "8410968304:AAEwoOxU4stdUEK_JSefuLGov3nMD1iQT6s"
ADMIN_ID = 8811384711
ORDERS_CHANNEL_ID = -1004466989868
FORCE_JOIN_CHANNELS = ["@SocialSMS2", "@SocialSMS1"]
SUPPORT_USERNAME = "@SocialSMSSUPPORT"
REFERRAL_REWARD_STARS = 0.3

CLEAN_NUMBERS = {
    "🇲🇲 ميانمار": {"stars": 20, "usd": 0.2},
    "🇸🇾 سوريا": {"stars": 80, "usd": 0.8},
    "🇲🇦 المغرب": {"stars": 60, "usd": 0.6},
    "🇺🇸 امريكا": {"stars": 30, "usd": 0.3},
    "🇮🇳 الهند": {"stars": 25, "usd": 0.25},
    "🇸🇦 السعودية": {"stars": 130, "usd": 1.3},
    "🇪🇬 مصر": {"stars": 70, "usd": 0.7},
}
SPAM_NUMBERS = {
    "🇲🇲 ميانمار": {"stars": 15, "usd": 0.15},
    "🇺🇸 امريكا": {"stars": 20, "usd": 0.2},
    "🇮🇳 الهند": {"stars": 20, "usd": 0.2},
}
CURRENCY_WALLETS = {
    "🆔 Cwallet ID": "61824874",
    "💵 USDT BEP20": "0x3dcF20c18f03F0016BeB5dE3A2979cF65e5DE596",
    "💵 USDT TRC20": "TRmkCedsJP9MongBrvy4gwdfBX5v8nSsqL",
    "💵 USDT ERC20": "0x5623f438C721D284e9257d2815a82a267b7F4d51",
    "💵 USDT POL": "0x5D14363342328D49C9094b61822608aB285Db59a",
    "🪙 LTC": "ltc1qk7gs0gt4zt0e0ztsv8g65sgq6h0s79ucfyl6ld",
    "🟡 BNB BEP20": "0x3dcF20c18f03F0016BeB5dE3A2979cF65e5DE596",
    "💲 USDC SOL": "Dw27gnVFsjQRTG3HpsVwawBPfzx1RPpRDsJtdKGNop2p",
    "💎 GRAM": "EQD14kgmngE0fNYVs7_9dw78V3rPhNt7_Ee-7X3ykDORQvMp",
    "🚰 FaucetPay": "primexstore22",
    "💳 فودافون كاش": "راسل الدعم @SocialSMSSUPPORT",
}
CURRENCIES = list(CURRENCY_WALLETS.keys())
STAR_PACKAGES = {
    "15": {"stars": 15, "price_usd": 0.12},
    "25": {"stars": 25, "price_usd": 0.22},
    "50": {"stars": 50, "price_usd": 0.42},
    "100": {"stars": 100, "price_usd": 0.90},
}
DB_FILE = "database.json"
def load_db():
    if not os.path.exists(DB_FILE):
        return {"users": {}, "orders": {}, "order_counter": 0, "banned": [], "deposits": {}, "deposit_counter": 0}
    try:
        with open(DB_FILE, "r", encoding="utf-8") as ff:
            data = json.load(ff)
            for k in ["banned","users","orders","deposits"]:
                if k not in data: data[k] = [] if k=="banned" else {}
            if "order_counter" not in data: data["order_counter"]=0
            if "deposit_counter" not in data: data["deposit_counter"]=0
            return data
    except:
        return {"users": {}, "orders": {}, "order_counter": 0, "banned": [], "deposits": {}, "deposit_counter": 0}

def save_db(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(f, data, ensure_ascii=False, indent=2)

db = load_db()

class DeliverState(StatesGroup):
    waiting_order_id = State()
    waiting_number = State()
    waiting_add_balance_id = State()
    waiting_add_balance_amount = State()
    waiting_ban_id = State()
    waiting_unban_id = State()
    waiting_broadcast = State()
    waiting_deposit_currency = State()
    waiting_deposit_amount = State()
    waiting_deposit_screenshot = State()

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
logging.basicConfig(level=logging.INFO)

def main_keyboard():
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="🛒 شراء حسابات")],
        [KeyboardButton(text="👥 دعوة اصدقاء"), KeyboardButton(text="👤 حسابي")],
        [KeyboardButton(text="⭐ شحن بالنجوم"), KeyboardButton(text="💳 شحن رصيد")],
        [KeyboardButton(text="📞 الدعم")]
    ], resize_keyboard=True)

def category_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ الأرقام السليمة", callback_data="cat_clean")],
        [InlineKeyboardButton(text="⚠️ أرقام سبام (محظورة)", callback_data="cat_spam")],
    ])

def get_price_info(item):
    if isinstance(item, dict):
        return item.get("stars", 0), item.get("usd", 0)
    return item, round(item * 0.009, 2)

def countries_keyboard(cat):
    data = CLEAN_NUMBERS if cat == "clean" else SPAM_NUMBERS
    buttons = []
    for name, price_data in data.items():
        stars, usd = get_price_info(price_data)
        buttons.append([InlineKeyboardButton(text=f"{name} - {stars} ⭐ (${usd})", callback_data=f"buy_{cat}_{name}_{stars}")])
    buttons.append([InlineKeyboardButton(text="🔙 رجوع", callback_data="cat_back")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

async def check_join(user_id):
    for ch in FORCE_JOIN_CHANNELS:
        try:
            member = await bot.get_chat_member(ch, user_id)
            if member.status in ["left", "kicked"]:
                return False
        except:
            continue
    return True

@dp.message(Command("start"))
async def start_cmd(message: types.Message, command: CommandObject):
    try:
        if str(message.from_user.id) in db.get("banned", []):
            await message.answer("🚫 انت محظور\nراسل الدعم: " + SUPPORT_USERNAME)
            return
        user_id = str(message.from_user.id)
        args = command.args
        is_new = user_id not in db["users"]
        if is_new:
            db["users"][user_id] = {"balance": 0.0, "invites": 0, "username": message.from_user.username or "بدون", "first_name": message.from_user.first_name or ""}
            save_db(db)
            if args and args!= user_id and args in db["users"]:
                try:
                    db["users"][args]["balance"] = float(db["users"][args].get("balance",0)) + float(REFERRAL_REWARD_STARS)
                    db["users"][args]["invites"] = int(db["users"][args].get("invites",0)) + 1
                    save_db(db)
                    await bot.send_message(int(args), f"🎉 شخص جديد دخل بدعوتك! كسبت {REFERRAL_REWARD_STARS} ⭐")
                except Exception as e:
                    print(f"referral error {e}")
            try:
                await bot.send_message(ADMIN_ID, f"👤 مستخدم جديد: {message.from_user.first_name} @{message.from_user.username} `{message.from_user.id}`")
            except: pass

        if not await check_join(message.from_user.id):
            kb = []
            for ch in FORCE_JOIN_CHANNELS:
                kb.append([InlineKeyboardButton(text=f"اشترك في {ch}", url=f"https://t.me/{ch.replace('@','')}")])
            kb.append([InlineKeyboardButton(text="✅ تحققت", callback_data="check_join")])
            await message.answer("⚠️ لازم تشترك في القنوات الاول", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
            return

        await message.answer(f"أهلا {message.from_user.first_name} 👋\nرصيدك: {db['users'][user_id].get('balance',0)} ⭐", reply_markup=main_keyboard())
    except Exception as e:
        print(f"start error {e}")
        logging.exception(e)

@dp.callback_query(F.data=="check_join")
async def check_join_cb(call: types.CallbackQuery):
    if await check_join(call.from_user.id):
        await call.message.delete()
        await call.message.answer(f"تم الاشتراك بنجاح ✅\nرصيدك: {db['users'].get(str(call.from_user.id),{}).get('balance',0)} ⭐", reply_markup=main_keyboard())
    else:
        await call.answer("لسه مشتركتش في كل القنوات", show_alert=True)

@dp.message(F.text == "🛒 شراء حسابات")
async def buy_menu(message: types.Message):
    await message.answer("اختر نوع الأرقام 👇", reply_markup=category_keyboard())

@dp.callback_query(F.data.startswith("cat_"))
async def cat_handler(call: types.CallbackQuery):
    if call.data == "cat_clean":
        await call.message.edit_text("✅ الأرقام السليمة\nاختر الدولة:", reply_markup=countries_keyboard("clean"))
    elif call.data == "cat_spam":
        await call.message.edit_text("⚠️ أرقام السبام\nاختر الدولة:", reply_markup=countries_keyboard("spam"))
    elif call.data == "cat_back":
        await call.message.edit_text("اختر نوع الأرقام 👇", reply_markup=category_keyboard())
    await call.answer()

@dp.callback_query(F.data.startswith("buy_"))
async def buy_country(call: types.CallbackQuery):
    try:
        _, cat, name, price = call.data.split("_", 3)
        price = int(float(price))
        await bot.send_invoice(chat_id=call.from_user.id, title=f"شراء رقم {name}", description=f"الدولة: {name}", payload=f"order_{cat}_{name}_{price}", provider_token="", currency="XTR", prices=[LabeledPrice(label=f"{name}", amount=price)])
        await call.answer()
    except Exception as e:
        print(f"buy error {e}")
        await call.answer("خطأ حاول مرة أخرى")

@dp.pre_checkout_query()
async def pre_checkout(q: types.PreCheckoutQuery):
    await bot.answer_pre_checkout_query(q.id, ok=True)

@dp.message(F.successful_payment)
async def success_pay(message: types.Message):
    try:
        pay = message.successful_payment
        payload = pay.invoice_payload
        _, cat, name, price = payload.split("_", 3)
        db["order_counter"] += 1
        order_id = db["order_counter"]
        db["orders"][str(order_id)] = {"id": order_id, "user_id": message.from_user.id, "username": message.from_user.username or "بدون", "type": "سليم ✅" if cat=="clean" else "سبام ⚠️", "country": name, "price": pay.total_amount, "status": "pending"}
        save_db(db)
        await message.answer(f"✅ تم الدفع!\n🆔 طلبك #{order_id}\n📦 {name}\n⏳ جاري التسليم...")
        try:
            await bot.send_message(ORDERS_CHANNEL_ID, f"🔔 طلب جديد #{order_id}\n👤 @{message.from_user.username} | {message.from_user.id}\n🌍 {name} - {pay.total_amount} ⭐")
        except: pass
    except Exception as e:
        print(f"pay error {e}")

@dp.message(F.text == "👥 دعوة اصدقاء")
async def invite(message: types.Message):
    me = await bot.get_me()
    link = f"https://t.me/{me.username}?start={message.from_user.id}"
    invites = db["users"].get(str(message.from_user.id), {}).get("invites", 0)
    await message.answer(f"👥 دعواتك: {invites}\n🔗 رابطك:\n`{link}`\n💰 تربح {REFERRAL_REWARD_STARS} على كل دعوة", parse_mode="Markdown")

@dp.message(F.text == "👤 حسابي")
async def my_account(message: types.Message):
    u = db["users"].get(str(message.from_user.id), {"balance":0, "invites":0})
    await message.answer(f"👤 حسابك\n🆔 {message.from_user.id}\n💳 {u.get('balance',0)} ⭐\n👥 {u.get('invites',0)}")

@dp.message(F.text == "📞 الدعم")
async def support(message: types.Message):
    await message.answer(f"📞 الدعم: {SUPPORT_USERNAME}")

@dp.message(F.text == "⭐ شحن بالنجوم")
async def charge_stars_menu(message: types.Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="15 ⭐ - 0.12$", callback_data="pack_15")],
        [InlineKeyboardButton(text="25 ⭐ - 0.22$", callback_data="pack_25")],
        [InlineKeyboardButton(text="50 ⭐ - 0.42$", callback_data="pack_50")],
        [InlineKeyboardButton(text="100 ⭐ - 0.90$", callback_data="pack_100")],
    ])
    await message.answer("⭐ شحن بالنجوم\nاختر الباقة:", reply_markup=kb)

@dp.message(F.text == "💳 شحن رصيد")
async def charge(message: types.Message, state: FSMContext):
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=c, callback_data=f"curr_{c}")] for c in CURRENCIES])
    await message.answer("💳 اختر العملة:", reply_markup=kb)
    await state.set_state(DeliverState.waiting_deposit_currency)

@dp.callback_query(F.data.startswith("curr_"))
async def deposit_choose_currency(call: types.CallbackQuery, state: FSMContext):
    currency = call.data.replace("curr_", "")
    wallet = CURRENCY_WALLETS.get(currency, "")
    await state.update_data(currency=currency)
    text = f"✅ اخترت: {currency}\n📥 العنوان:\n`{wallet}`\n\n✍️ اكتب كمية النجوم:"
    await call.message.edit_text(text, parse_mode="Markdown")
    await state.set_state(DeliverState.waiting_deposit_amount)
    await call.answer()

@dp.message(DeliverState.waiting_deposit_amount)
async def deposit_get_amount(message: types.Message, state: FSMContext):
    try:
        amount = float(message.text.strip())
        await state.update_data(amount=amount)
        await message.answer("📸 ابعت صورة التحويل دلوقتي")
        await state.set_state(DeliverState.waiting_deposit_screenshot)
    except:
        await message.answer("❌ اكتب رقم صحيح")

@dp.message(DeliverState.waiting_deposit_screenshot, F.photo)
async def deposit_get_screenshot(message: types.Message, state: FSMContext):
    data = await state.get_data()
    db["deposit_counter"] += 1
    dep_id = str(db["deposit_counter"])
    db["deposits"][dep_id] = {"id": dep_id, "user_id": message.from_user.id, "username": message.from_user.username or "بدون", "currency": data.get("currency"), "amount": data.get("amount"), "photo_id": message.photo[-1].file_id, "status": "pending"}
    save_db(db)
    await message.answer(f"✅ تم استلام طلبك #{dep_id} قيد المراجعة")
    caption = f"💸 طلب شحن #{dep_id}\n👤 @{message.from_user.username} | {message.from_user.id}\n💳 {data.get('currency')}\n⭐ {data.get('amount')}"
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="✅ قبول", callback_data=f"dep_ok_{dep_id}"), InlineKeyboardButton(text="❌ رفض", callback_data=f"dep_no_{dep_id}")]])
    try:
        await bot.send_photo(chat_id=ADMIN_ID, photo=message.photo[-1].file_id, caption=caption, reply_markup=kb)
    except: pass
    await state.clear()

@dp.callback_query(F.data.startswith("dep_ok_"))
async def deposit_accept(call: types.CallbackQuery):
    dep_id = call.data.replace("dep_ok_", "")
    dep = db["deposits"].get(dep_id)
    if not dep:
        await call.answer("مش موجود")
        return
    uid = str(dep["user_id"])
    if uid not in db["users"]: db["users"][uid] = {"balance": 0, "invites": 0, "username": dep["username"]}
    db["users"][uid]["balance"] = float(db["users"][uid].get("balance",0)) + float(dep["amount"])
    dep["status"] = "accepted"
    save_db(db)
    await call.answer("تم القبول")
    try: await bot.send_message(int(uid), f"✅ تم شحن {dep['amount']} ⭐\nرصيدك: {db['users'][uid]['balance']} ⭐")
    except: pass

@dp.callback_query(F.data.startswith("dep_no_"))
async def deposit_reject(call: types.CallbackQuery):
    dep_id = call.data.replace("dep_no_", "")
    dep = db["deposits"].get(dep_id)
    if dep:
        dep["status"]="rejected"
        save_db(db)
    await call.answer("تم الرفض")

@dp.message(Command("admin"))
async def admin_panel(message: types.Message):
    if message.from_user.id!= ADMIN_ID: return
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 الطلبات", callback_data="admin_pending")],
        [InlineKeyboardButton(text="📦 تسليم", callback_data="admin_deliver")],
        [InlineKeyboardButton(text="💳 اضافة رصيد", callback_data="admin_add_balance")],
        [InlineKeyboardButton(text="📊 احصائيات", callback_data="admin_stats")],
    ])
    await message.answer("👑 لوحة الادمن", reply_markup=kb)

@dp.callback_query(F.data == "admin_pending")
async def admin_pending(call: types.CallbackQuery):
    pending = [o for o in db["orders"].values() if o["status"]=="pending"]
    txt = "📋 المعلقة:\n" + "\n".join([f"#{o['id']} - {o['country']} - {o['user_id']}" for o in pending[-10:]]) if pending else "لا يوجد"
    await call.message.answer(txt)
    await call.answer()

@dp.callback_query(F.data == "admin_deliver")
async def admin_deliver_start(call: types.CallbackQuery, state: FSMContext):
    await call.message.answer("ابعت رقم الطلب:")
    await state.set_state(DeliverState.waiting_order_id)
    await call.answer()

@dp.message(DeliverState.waiting_order_id)
async def deliver_get_id(message: types.Message, state: FSMContext):
    oid = message.text.strip()
    if oid not in db["orders"]:
        await message.answer("رقم الطلب مش موجود")
        return
    await state.update_data(order_id=oid)
    await message.answer(f"تمام طلب #{oid}\nابعت الرقم للعميل")
    await state.set_state(DeliverState.waiting_number)

@dp.message(DeliverState.waiting_number)
async def deliver_get_number(message: types.Message, state: FSMContext):
    data = await state.get_data()
    oid = data["order_id"]
    db["orders"][oid]["status"] = "delivered"
    db["orders"][oid]["delivered_number"] = message.text
    save_db(db)
    try:
        await bot.send_message(db["orders"][oid]["user_id"], f"✅ تم تسليم طلبك #{oid}\n\n{message.text}")
        await message.answer("تم التسليم ✅")
    except Exception as e:
        await message.answer(f"خطأ: {e}")
    await state.clear()

@dp.callback_query(F.data == "admin_add_balance")
async def admin_add_balance_start(call: types.CallbackQuery, state: FSMContext):
    await call.message.answer("ابعت ايدي العميل:")
    await state.set_state(DeliverState.waiting_add_balance_id)
    await call.answer()

@dp.message(DeliverState.waiting_add_balance_id)
async def add_balance_get_id(message: types.Message, state: FSMContext):
    await state.update_data(target_uid=message.text.strip())
    await message.answer("ابعت كمية النجوم:")
    await state.set_state(DeliverState.waiting_add_balance_amount)

@dp.message(DeliverState.waiting_add_balance_amount)
async def add_balance_get_amount(message: types.Message, state: FSMContext):
    data = await state.get_data()
    uid = data["target_uid"]
    try:
        amount = float(message.text.strip())
        if uid not in db["users"]: db["users"][uid] = {"balance": 0, "invites": 0, "username": "غير معروف"}
        db["users"][uid]["balance"] = float(db["users"][uid].get("balance",0)) + amount
        save_db(db)
        await message.answer(f"✅ تم اضافة {amount} للعميل {uid}")
        try: await bot.send_message(int(uid), f"✅ تم شحن {amount} ⭐")
        except: pass
    except Exception as e:
        await message.answer(f"خطأ: {e}")
    await state.clear()

@dp.callback_query(F.data == "admin_stats")
async def admin_stats(call: types.CallbackQuery):
    total_users = len(db["users"])
    total_orders = len(db["orders"])
    pending = len([o for o in db["orders"].values() if o["status"]=="pending"])
    txt = f"📊 المستخدمين: {total_users}\n📦 الطلبات: {total_orders}\n⏳ المعلقة: {pending}"
    await call.message.answer(txt)
    await call.answer()

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
