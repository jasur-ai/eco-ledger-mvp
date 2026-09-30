# Cheklovlar (TZ §9 — yashirilmaydi)

1. **Sintetik obyektlar.** Demo 78 obyekt bilan ishlaydi; real korxona nomlari ishlatilmaydi
   (TZ §1 anti-da'vosi). Real oqim: PF-56/PQ-184 tizimlari ochilgach.
2. **Bot tokeni.** `scripts/bot.py` yozilgan, ammo jonli ishga tushirish uchun
   `ECO_BOT_TOKEN` kerak (S5 to'liq yakuni shunga bog'liq).
3. **SQLite demo ↔ PostGIS production.** Demo SQLite'da (bitta fayl); produksiya sxemasi
   `db/schema_postgis.sql` da tayyor (ko'chirish uchun kod izohlarida moslik saqlangan).
4. **Bayramlar hisobga olinmagan.** SLA ish kunlari faqat Sh/Ya'ni tashlaydi (TZ §6.5 —
   ishlab chiqarishda bayram kalendari ulanadi).
5. **Yuridik jihat.** Platforma korxonani ayblamaydi; natija yuridik dalil emas (anti-da'volar).
   «Qizil» — ustuvor tekshiruv manzili, hukm emas.
6. **LLM rejimi.** Hozir deterministik shablon (kalitsiz); LLM kaliti ulanganda promt `prompt_v1.md`
   bo'yicha ishlaydi va SHU 6 qavatdan o'tadi — verifikatsiya o'zgarmaydi.
7. **Dioksin/kul monitoringi.** WtE obyektlari uchun alohida indikator MVP'da yo'q
   (kelajak ro'yxatida, Maqola 2 — tavsiya 12).
