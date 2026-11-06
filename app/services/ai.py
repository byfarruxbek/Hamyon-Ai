import json, logging, io
from datetime import date
from openai import AsyncOpenAI
from app.domain import ParsedEntry, normalize_category
log=logging.getLogger(__name__)

FINANCE_TERMS=(
    "moliya", "moliyav", "hamyon", "xarajat", "daromad", "kirim", "chiqim",
    "pul", "qarz", "tolov", "to‘lov", "toʻlov", "to'lov", "so‘m", "so'm",
    "summa", "uzs", "ming", "million", "mln", "budjet", "byudjet", "tejash",
    "jamg‘arma", "jamg'arma", "maosh", "oylik", "kredit", "bank", "hisobot",
    "balans", "limit", "sarf", "kategoriya", "investitsiya", "inflyatsiya",
    "depozit", "foiz", "soliq", "eslatma", "to‘landi", "to'landi",
)
CAPABILITY_TERMS=(
    "nima qila olasan", "nima qila oladi", "yordam bera olasan", "bot nima",
    "qanday ishlaydi", "qanday foydalan", "qaysi buyruq", "buyruqlar",
    "hamyon ai", "/help", "/start", "ovoz yubor", "rasm yubor",
)

def is_finance_question(question: str) -> bool:
    text=question.casefold()
    return any(term in text for term in FINANCE_TERMS+CAPABILITY_TERMS)

class AIUnavailable(RuntimeError): pass

class AIService:
    def __init__(self,key,model,transcribe_model="",base_url=None): self.client=AsyncOpenAI(api_key=key,base_url=base_url) if key else None;self.model=model;self.transcribe_model=transcribe_model
    def _decode_entry(self, content, kind_hint=None):
        raw=(content or "{}").strip()
        if raw.startswith("```"):
            raw=raw.strip("`")
            if raw.lower().startswith("json"): raw=raw[4:].strip()
        if not raw.startswith("{"):
            left=raw.find("{");right=raw.rfind("}")
            if left<0 or right<left: raise ValueError("JSON not found")
            raw=raw[left:right+1]
        data=json.loads(raw)
        kind=data.get("kind")
        if data.get("amount") is None: raise ValueError("amount uncertain")
        amount=int(data["amount"]);day=date.fromisoformat(data.get("date") or date.today().isoformat())
        if kind not in ("income","expense") or amount<=0: raise ValueError("invalid parse")
        if kind_hint: kind=kind_hint
        return ParsedEntry(kind,amount,normalize_category(data.get("category")),str(data.get("note", ""))[:300],day)

    async def parse_entry(self,text,kind_hint=None):
        if not self.client: raise AIUnavailable("AI API kaliti sozlanmagan")
        prompt="You parse personal finance entries from Uzbek (Latin/Cyrillic), Russian, colloquial Uzbek, slang and common typos. Return ONLY JSON keys kind (expense|income), amount (integer UZS or null), category, note, date (YYYY-MM-DD). Parse amounts exactly: ‘400 ming’=400000, ‘2 mln’=2000000. ‘Benzinga 200 ming ketdi’ is a 200000 expense in Transport; fuel/benzin belongs to Transport. ‘500 ming ishlab topdim’ is income, category Mehnat daromadi. Meals/food paid are expense, Oziq-ovqat. Do not guess: amount null if uncertain. Use today's date when no date is given. Preserve short meaningful description as note; exclude amount/currency/date words. Never classify a debt payment obligation as income/expense; return null."
        try:
            res=await self.client.chat.completions.create(model=self.model,temperature=0,messages=[{"role":"system","content":prompt},{"role":"user","content":text}])
            return self._decode_entry(res.choices[0].message.content,kind_hint)
        except Exception as exc:
            log.warning("AI parse failed (%s)",type(exc).__name__)
            raise AIUnavailable(type(exc).__name__) from exc

    async def parse_debt(self, text, today):
        if not self.client: raise AIUnavailable("AI API kaliti sozlanmagan")
        prompt=("You extract a personal debt payment reminder from Uzbek text. Return ONLY JSON: "
                '{"title":"...","amount":integer UZS,"due_date":"YYYY-MM-DD or null"}. '
                f"Today is {today.isoformat()}. Understand Uzbek date phrases such as 9-noyabrda, "
                "and amounts such as 2 mln so'm = 2000000 UZS. If a date has no year, choose the next upcoming occurrence. "
                "Keep the lender/card/credit name in title (for example TBC Osmon karta), remove case suffixes and action words. "
                "Do not invent missing amount or date; use null. Do not treat a debt the user owes as income or expense.")
        try:
            res=await self.client.chat.completions.create(model=self.model,temperature=0,messages=[{"role":"system","content":prompt},{"role":"user","content":text}])
            raw=(res.choices[0].message.content or "{}").strip()
            if raw.startswith("```"):
                raw=raw.strip("`")
                if raw.lower().startswith("json"): raw=raw[4:].strip()
            if not raw.startswith("{"):
                left=raw.find("{");right=raw.rfind("}")
                if left<0 or right<left: raise ValueError("JSON not found")
                raw=raw[left:right+1]
            data=json.loads(raw)
            amount=int(data["amount"]) if data.get("amount") is not None else None
            due=data.get("due_date")
            if amount is not None and amount<=0: raise ValueError("amount invalid")
            if due: date.fromisoformat(due)
            return {"title":str(data.get("title") or "Qarz to‘lovi")[:120],"amount":amount,"due_date":due}
        except Exception as exc:
            log.warning("AI debt parse failed (%s)",type(exc).__name__)
            raise AIUnavailable(type(exc).__name__) from exc

    async def transcribe(self, filename, content):
        if not self.transcribe_model: raise AIUnavailable("Audio uchun AI_TRANSCRIBE_MODEL sozlanmagan")
        if not self.client: raise AIUnavailable("AI API kaliti sozlanmagan")
        try:
            result=await self.client.audio.transcriptions.create(model=self.transcribe_model,file=(filename,content))
            return result.text
        except Exception as exc:
            log.warning("AI transcription failed (%s)",type(exc).__name__)
            raise AIUnavailable(type(exc).__name__) from exc

    async def parse_image(self, mime_type, content, kind_hint=None):
        if not self.client: raise AIUnavailable("AI API kaliti sozlanmagan")
        import base64
        prompt="Read this receipt and extract the final total actually paid, date, currency, and useful merchant/items. If there are multiple amounts, prefer the explicitly labelled total/paid amount, not subtotal, tax, change, or item price. Return ONLY JSON keys kind (expense|income), amount (integer UZS or null), category, note, date (YYYY-MM-DD). If total/currency/date is ambiguous, set amount null; never guess. Receipt purchases are expense unless clearly a refund/income."
        try:
            encoded=base64.b64encode(content).decode("ascii")
            res=await self.client.chat.completions.create(model=self.model,temperature=0,messages=[{"role":"system","content":prompt},{"role":"user","content":[{"type":"text","text":"Extract the transaction from this image."},{"type":"image_url","image_url":{"url":f"data:{mime_type};base64,{encoded}"}}]}])
            return self._decode_entry(res.choices[0].message.content,kind_hint)
        except Exception as exc:
            log.warning("AI image parse failed (%s)",type(exc).__name__)
            raise AIUnavailable(type(exc).__name__) from exc
    async def ask(self,question,context):
        if not self.client: raise AIUnavailable("AI API kaliti sozlanmagan")
        system_prompt="""Sen Hamyon AI — foydalanuvchiga savollarida yordam beradigan aqlli yordamchisan. Har doim o‘zbek tilida, lotin yozuvida, sodda va muloyim javob ber. Foydalanuvchi istalgan mavzuda savol berishi mumkin; foydali va aniq javob ber, mavzuni buyruq bilan cheklama. Bilmagan yoki ishonching komil bo‘lmagan narsani ochiq ayt, to‘qima.

Hamyon AI moliya imkoniyatlari:

BOT NIMALAR QILA OLADI:
- Xarajat va daromadni matn, chek rasmi yoki foydalanuvchi yoqqan bo‘lsa ovoz orqali tahlil qiladi. Saqlashdan oldin summa, kategoriya va izohni ko‘rsatib, tasdiq so‘raydi.
- Qarzlarni qo‘shish, ko‘rish, tahrirlash, o‘chirish va to‘lovni qayd etishga yordam beradi.
- Oylik daromad/xarajat hisobotini, kategoriya bo‘yicha sarfni va ochiq qarzlarni ko‘rsatadi.
- Xarajat limitini belgilash hamda sana-vaqtli eslatmalar qo‘shish imkonini beradi.
- Kiritilgan ma’lumotlar asosida savollarga javob berib, budjetni rejalashtirish bo‘yicha oddiy tavsiyalar beradi.

FOYDALANUVCHI “SEN NIMA QILA OLASAN?”, “BOT NIMA UCHUN KERAK?” yoki o‘xshash savol bersa, ma’lumot yetishmaydi deb aytma. Imkoniyatlarni qisqacha sanab, misol buyruqlarni ber: /xarajat 45000 ovqat tushlik, /daromad 5000000 oylik, /qarzlar, /hisobot, /savol Shu oy xarajatlarim qanday?

CHEGARALAR:
- Bank hisobi, kartasi yoki balansiga kira olmaydi; faqat botga foydalanuvchi kiritgan yozuvlarni ko‘radi. Bu ma’lumotni bankdagi haqiqiy balans deb ko‘rsatma.
- Pul o‘tkazmaydi; to‘lovni faqat qayd etadi.
- Shaxsiy moliyaviy savollarga faqat berilgan ma’lumotlar asosida javob ber. Ma’lumot bo‘lmasa, buni tushuntir va /hisobot yoki mos buyruqni taklif qil.
- Bank paroli, PIN yoki CVV kabi maxfiy ma’lumotlarni so‘rama.
- Bajara olmaydigan ishni bajargandek ko‘rsatma. AI tahlili natijasini foydalanuvchiga tasdiqlat.
- Javobni tabiiy, ravon o‘zbek tilida qisqa yoz. Markdown belgilarini (** yoki ##) ishlatma; sodda sarlavha va oddiy ro‘yxat yoz.
- Moliyaviy savolda faqat berilgan raqamlardan foydalan. Foydalanuvchi so‘ramasa, umumiy tavsiya yoki sun’iy maslahat qo‘shma. Noaniq ibora, uydirma kategoriya va hisob-kitob qilma.
"""
        try:
            res=await self.client.chat.completions.create(model=self.model,temperature=.3,messages=[{"role":"system","content":system_prompt},{"role":"user","content":f"Foydalanuvchining kiritgan moliyaviy ma'lumotlari: {json.dumps(context,ensure_ascii=False)}\nSavol: {question}"}])
            return res.choices[0].message.content or "Javob bo‘sh qaytdi."
        except Exception as exc:
            log.warning("AI answer failed (%s)",type(exc).__name__);raise AIUnavailable(type(exc).__name__) from exc
