# To‘lovlar va balans — mobil integratsiya

Bu hujjat `MOBILE_API_REFERENCE.md` dagi **§4 Payments & balance (auth)** va **buyurtma (order) to‘lovlari** bo‘yicha **qaysi API qachon chaqirilishi** tartibini tushuntiradi.

---

## Ikki xil “pul” tizimi

| Tizim | Kim uchun | Maqsad | Asosiy maydon |
|--------|-----------|--------|----------------|
| **UserBalance** (garanти / depozit) | **Haydovchi (Driver)** | Buyurtma qabul qilish uchun minimal balans, qabulda **200 ₽** yechiladi, bekor qilishda jarima | `GET /api/auth/user/` → `user.balance.amount` |
| **MasterAvailableBalance** | **Usta (Master)** | Mijoz buyurtmani to‘lagach ustaga tushadigan summa, **yechib olish** | `GET /api/auth/balance/master-available/` |
| **Buyurtma to‘lovi** (Alfa + intent) | **Haydovchi** mijoz sifatida | Usta ishni tugatgach xizmatlar summasi | `order.payment_status`, `POST .../complete/` javobidagi `payment` |

**Muhim:** garanти balans to‘ldirish (`sbp-qr`) va buyurtma uchun to‘lov (`complete` → Alfa `form_url`) — **turli jarayonlar**. Mobil ilova ularni alohida ekranlarda ko‘rsatishi kerak.

---

## Qism A — Auth balans API’lari (ketma-ketlik)

Barcha yo‘llar: `{BASE}/api/auth/balance/...`  
Auth: **JWT** (`Authorization: Bearer ...`).

### A1. Joriy balansni ko‘rish (birinchi qadam)

| Tartib | API | Rol |
|--------|-----|-----|
| 1 | `GET /api/auth/user/` | Driver, Master, Owner |

Javobda `user.balance.amount` — garanти balans (₽). Usta uchun alohida “ishlab topilgan” balans bu emas (qarang A6).

---

### A2. Garanти balansni to‘ldirish (Driver / Master — `UserBalance`)

| Tartib | API | Tavsif |
|--------|-----|--------|
| 1 | `POST /api/auth/balance/sbp-qr/` | Body: `{ "price": "1000.00" }` — min **5 ₽** (`MIN_SBP_TOPUP_RUB`). Javob: `intent_id`, `pay_url`, `qr_image_base64`. |
| 2 | *(foydalanuvchi bankda to‘laydi)* | Statik SBP QR; bankda summa = `price`. |
| 3 | `GET /api/auth/balance/sbp-intent/<uuid>/` | `status`: `pending` \| `completed` \| `expired`. `completed` bo‘lsa va siz intent egasisiz — `balance` yangilanadi. |
| 4 *(ixtiyoriy)* | `POST /api/auth/balance/alfa-order-status/` | Alfa orqali ro‘yxatdan o‘tgan to‘lovlar uchun (asosan **master-topup** va **order** `PaymentTransaction` bilan). |
| 5 | `GET /api/auth/balance/payment-history/` | Barcha to‘lovlar ro‘yxati (yangi API, quyida). |

**Server (mobil emas):** `POST .../sbp-webhook/`, `POST .../sbp-confirm-by-trx/` — to‘lovni tasdiqlash.

---

### A3. Buyurtma qabul qilishda balansdan yechish (Driver — Master emas!)

| Tartib | API | Balans |
|--------|-----|--------|
| 1 | `GET /api/auth/user/` | Kamida **1000 ₽** kerak (`accept` tekshiradi). |
| 2 | `POST /api/order/<order_id>/accept/` | Muvaffaqiyatda **200 ₽** `UserBalance` dan yechiladi. |

Agar balans yetmasa — `400` va `current_balance` / `required_balance`.

> **Eslatma:** bu yechish hozircha `payment-history` da **ko‘rinmaydi** (faqat bank orqali to‘lovlar va Alfa tranzaksiyalar).

---

### A4. Bekor qilish — jarima (Driver)

| API | Balans |
|-----|--------|
| `POST /api/order/<order_id>/cancel/` | Statusga qarab `UserBalance` dan foiz yechilishi mumkin. |

Bu ham tarixda yo‘q (hozircha).

---

### A5. Owner — ustaga balans to‘ldirish

| Tartib | API | Rol |
|--------|-----|-----|
| 1 | `POST /api/auth/balance/master-topup/` | **Owner** — `master_id`, `price` (min **1000 ₽**). |
| 2 | Mijoz `form_url` orqali to‘laydi | Javobdagi `form_url`. |
| 3 | `POST /api/auth/balance/alfa-order-status/` | `alfa_order_id` / `alfa_order_number`, `intent_id`. |
| 4 | `GET /api/auth/balance/payment-history/?kind=master_topup` | Tarixda `kind: master_topup`. |

---

### A6. Usta — ishlab topilgan balans va yechib olish

| Tartib | API | Tavsif |
|--------|-----|--------|
| 1 | `GET /api/auth/balance/master-available/` | Mijoz buyurtmani to‘lagach shu yerda o‘sadi. |
| 2 | `POST /api/auth/balance/master-withdraw/` | Body: `{ "price": "500.00" }` — summa darhol rezerv qilinadi. |
| 3 | `GET /api/auth/balance/master-withdrawals/` | Yechib olish **arizalari** (bu payment-history emas, alohida ro‘yxat). |

---

## Qism B — Buyurtma (order) to‘lovi API’lari

Yo‘llar: `{BASE}/api/order/<order_id>/...`

### B1. Umumiy oqim (ketma-ketlik)

```
accept → workflow (on_the_way → arrived → in_progress)
      → add-services
      → work-completion-images
      → complete  ──► payment (Alfa form_url + intent_id)
      → mijoz to‘laydi
      → payment_status = paid
```

| Tartib | API | Kim | Vazifa |
|--------|-----|-----|--------|
| 1 | `POST .../accept/` | Master | Buyurtmani oladi; driver balansidan 200 ₽ (A3). |
| 2 | `POST .../workflow/` | Master | `on_the_way` → `arrived` → `in_progress`. |
| 3 | `POST /api/order/add-services/` | Driver/Master | Xizmatlar va summa. |
| 4 | `POST .../work-completion-images/` | Master | Kamida 1 rasm (`images`). |
| 5 | `POST .../complete/` | Master | Body: `{ "completion_pin": "...." }`. Status `completed`, `payment_status: pending`, **`payment.form_url`**, `intent_id`. |
| 6 | *(haydovchi to‘laydi)* | Driver | `form_url` (Alfa) yoki polling. |
| 7 | `GET /api/auth/balance/sbp-intent/<intent_id>/` | Driver / Master / order ishtirokchisi | `status: completed` → buyurtma `paid`. |
| 8 *(agar link eskirgan)* | `POST .../payment/resend/` | Master | Yangi `form_url` va yangi `intent_id`. |
| 9 | `GET /api/order/<id>/` | Driver | `payment_status`, `payment` maydonlari. |
| 10 | `GET /api/auth/balance/payment-history/?kind=order` | Driver | Buyurtma to‘lovlari tarixi. |

**Webhook (server):** `POST /api/auth/balance/sbp-webhook/` — `intent_id` bo‘yicha buyurtmani `paid` qiladi.

**Fon:** Celery `check_pending_payments` Alfa statusini so‘raydi (`PaymentTransaction` pending → paid).

---

### B2. `order.payment_status` (mobil UI)

| Qiymat | Ma’nosi |
|--------|---------|
| `none` | Hali to‘lov yaratilmagan |
| `pending` | `complete` dan keyin — mijoz to‘lashi kerak |
| `paid` | To‘lov tasdiqlandi |

---

## Payment history API (yangi)

| | |
|--|--|
| **Method** | `GET` |
| **URL** | `/api/auth/balance/payment-history/` |
| **Auth** | JWT |

### Query parametrlar

| Param | Qiymatlar | Izoh |
|-------|-----------|------|
| `kind` | `balance_topup` \| `order` \| `master_topup` | Filtr |
| `status` | `pending` \| `paid` \| `failed` \| `completed` \| `expired` | `paid`/`failed` — tranzaksiya; `completed`/`expired` — SBP intent |
| `limit` | 1–100 (default **50**) | |

### Javob (200)

```json
{
  "success": true,
  "count": 2,
  "balance": {
    "amount": "1500.00",
    "updated_at": "2026-05-21T12:00:00+00:00"
  },
  "results": [
    {
      "record_type": "payment_transaction",
      "transaction_id": 12,
      "kind": "order",
      "status": "paid",
      "intent_status": "completed",
      "amount": "3500.00",
      "intent_id": "uuid-...",
      "order_id": 5,
      "master_id": 3,
      "alfa_order_id": "...",
      "alfa_order_number": "order-5-abc",
      "form_url": "https://...",
      "initiated_by_me": true,
      "beneficiary_me": true,
      "created_at": "...",
      "completed_at": "...",
      "updated_at": "..."
    },
    {
      "record_type": "balance_topup",
      "transaction_id": null,
      "kind": "balance_topup",
      "status": "completed",
      "intent_id": "uuid-...",
      "order_id": null,
      "amount": "1000.00",
      "initiated_by_me": true,
      "beneficiary_me": true,
      "created_at": "...",
      "completed_at": "..."
    }
  ]
}
```

### `kind` turlari

| `kind` | Manba | Kim ko‘radi |
|--------|-------|-------------|
| `balance_topup` | `SbpPaymentIntent` (faqat `sbp-qr`, tranzaksiyasiz) | Intent egasi |
| `order` | `PaymentTransaction` + `complete` / `resend` | Odatda haydovchi (`beneficiary`) |
| `master_topup` | Owner `master-topup` | Owner (`initiated_by_me`) va usta (`beneficiary_me`) |

### Tarixda **yo‘q** (hozircha)

- `accept` dagi **200 ₽** yechish  
- `cancel` jarimalari  
- `master-withdrawals` (ular uchun `GET .../master-withdrawals/`)

---

## Tezkor jadval: auth vs order

| Vazifa | Auth (`/api/auth/balance/`) | Order (`/api/order/`) |
|--------|----------------------------|------------------------|
| Garanти balans ko‘rish | `GET /api/auth/user/` | — |
| Garanти to‘ldirish | `sbp-qr` → bank → `sbp-intent` | — |
| Buyurtma uchun to‘lov | `sbp-intent`, `alfa-order-status`, `payment-history` | `complete`, `payment/resend` |
| Usta daromad | `master-available`, `master-withdraw*` | `complete` → mijoz to‘lagach |
| To‘lovlar tarixi | **`payment-history`** | — |

---

## Mobil ekranlar uchun tavsiya

1. **Hamyon / Balans** — `user.balance` + `payment-history?kind=balance_topup` + tugma “To‘ldirish” → `sbp-qr`.  
2. **Buyurtma to‘lovi** — `complete` dan keyin `payment.form_url` + `sbp-intent` polling yoki push `order_payment_paid`.  
3. **Usta daromad** — `master-available` + `master-withdrawals` (alohida).  
4. **Barcha to‘lovlar** — `payment-history` (filtr: `kind`, `status`).

---

## Manbalar

- To‘liq endpoint jadvali: `docs/MOBILE_API_REFERENCE.md` §4 va §8.  
- Swagger: `GET /docs/`  
- OpenAPI: `GET /schema/`
