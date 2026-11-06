from app.domain import parse_manual_entry,normalize_category,validate_payment,InputError
from app.handlers.ai import is_report_request,telegram_safe_answer
from app.services.engagement import inactivity_nudge_due
from datetime import datetime,timedelta
def test_currency_is_not_category():
 e=parse_manual_entry("45000 so'm", "expense");assert e.amount==45000 and e.category=="Boshqa"
def test_category_survives_currency_word():
 e=parse_manual_entry("45 000 so‘m ovqat", "expense");assert e.amount==45000 and e.category=="Oziq-ovqat"
def test_income_is_income(): assert parse_manual_entry("5000000 oylik", "income").kind=="income"
def test_payment_limits():
 assert validate_payment(100,None)==100
 try: validate_payment(100,101)
 except InputError: pass
 else: assert False
def test_currency_cleaning(): assert normalize_category("UZS") == "Boshqa"


def test_uzbek_thousand_phrase():
 e=parse_manual_entry("video qiberdim 400 ming so‘m", "income")
 assert e.amount==400000 and e.category=="Video xizmati" and e.note=="video qiberdim"

def test_numeric_first_with_ming():
 e=parse_manual_entry("400 ming video xizmati", "income")
 assert e.amount==400000 and e.category=="Video xizmati"

def test_million_suffix():
 assert parse_manual_entry("2 mln oylik", "income").amount==2000000

def test_benzin_typo_maps_to_transport():
 e=parse_manual_entry("Benzinga 200 ming ketdi", "expense")
 assert e.amount==200000 and e.category=="Transport"

def test_earned_income_phrase():
 e=parse_manual_entry("500 ming ishlab topdim", "income")
 assert e.amount==500000 and e.category=="Mehnat daromadi"

def test_report_request_uses_structured_report():
 assert is_report_request("2026-noyabr moliyaviy hisoboti")

def test_ai_markdown_is_renderable_html():
 result=telegram_safe_answer("**Hisobot**\n- Xarajat: 55 000 so'm")
 assert "**" not in result and "<b>Hisobot</b>" in result and "• Xarajat" in result

def test_inactivity_nudge_has_cooldown():
 now=datetime(2026,11,6,19)
 assert not inactivity_nudge_due(now-timedelta(days=2),None,now)
 assert inactivity_nudge_due(now-timedelta(days=3),None,now)
 assert not inactivity_nudge_due(now-timedelta(days=10),now-timedelta(days=3),now)
 assert inactivity_nudge_due(now-timedelta(days=10),now-timedelta(days=7),now)
