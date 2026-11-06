from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

def main_menu():
    return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="➕ Xarajat"),KeyboardButton(text="➕ Daromad")],[KeyboardButton(text="💳 Qarzlar"),KeyboardButton(text="📊 Hisobot")],[KeyboardButton(text="🤖 AI yordamchi"),KeyboardButton(text="⚙️ Sozlamalar")]],resize_keyboard=True,input_field_placeholder="Masalan: 45 000 ovqat tushlik")

EXPENSE_CATEGORIES = ["Oziq-ovqat", "Ichimliklar", "Transport", "Uy-joy", "Kommunal", "Aloqa", "Sog‘liq", "Ta’lim", "Kiyim", "Ko‘ngilochar", "Boshqa"]
INCOME_CATEGORIES = ["Ish haqi", "Mehnat daromadi", "Video xizmati", "Xizmat", "Savdo", "Ijara daromadi", "Investitsiya", "Sovg‘a", "Boshqa"]

def category_options(kind: str):
    return INCOME_CATEGORIES if kind == "income" else EXPENSE_CATEGORIES

def confirm_keyboard(token: str):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Tasdiqlash",callback_data=f"confirm:{token}"),InlineKeyboardButton(text="❌ Bekor qilish",callback_data=f"cancel:{token}")],
        [InlineKeyboardButton(text="✏️ Summani tahrirlash",callback_data=f"edit:{token}:amount"),InlineKeyboardButton(text="✏️ Kategoriyani tahrirlash",callback_data=f"edit:{token}:category")],
        [InlineKeyboardButton(text="✏️ Izohni tahrirlash",callback_data=f"edit:{token}:note")],
    ])

def category_keyboard(token: str, kind: str):
    options=category_options(kind)
    rows=[]
    for start in range(0,len(options),2):
        rows.append([InlineKeyboardButton(text=name,callback_data=f"cat:{token}:{index}") for index,name in enumerate(options[start:start+2],start)])
    rows.append([InlineKeyboardButton(text="✍️ O‘zim yozaman",callback_data=f"catcustom:{token}")])
    rows.append([InlineKeyboardButton(text="⬅️ Orqaga",callback_data=f"catback:{token}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def debt_keyboard(debts):
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=f"{d.title[:22]} · {d.remaining:,} so‘m",callback_data=f"debt:{d.id}")] for d in debts])

def payment_keyboard(debt_id: int):
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="To‘liq to‘landi",callback_data=f"payfull:{debt_id}"),InlineKeyboardButton(text="Qisman to‘lash",callback_data=f"paypart:{debt_id}")]])


def debt_confirmation_keyboard(token: str):
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Qarzni qo‘shish",callback_data=f"debtconfirm:{token}"),
        InlineKeyboardButton(text="❌ Bekor qilish",callback_data=f"debtcancel:{token}"),
    ]])
