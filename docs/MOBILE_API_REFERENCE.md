# CheckAvto — Mobile API Reference

Production-ready reference for **iOS / Android** clients integrating with the CheckAvto Django REST backend.

---

## 1. General

| Item | Value |
|------|--------|
| **Project** | CheckAvto |
| **Stack** | Django 5.x + Django REST Framework (DRF) |
| **Default response format** | JSON |
| **Default request body (REST)** | `Content-Type: application/json` |
| **Authentication** | **JWT** (`rest_framework_simplejwt`) |
| **OpenAPI schema** | `GET /schema/` |
| **Swagger UI** | `GET /docs/` |
| **ReDoc** | `GET /redoc/` |

### Base URLs

| Environment | Base URL | Notes |
|-------------|----------|--------|
| **Production** (from Spectacular config) | `http://31.128.43.149:6060` | Replace with HTTPS when deployed with TLS. |
| **Development** | `http://localhost:8002` | Match your local `runserver` / Daphne port. |
| **Staging** | *(not configured in repo)* | Align with your DevOps; path prefix is always `/api/...`. |

All API paths below are **relative to the base URL** (e.g. `POST {BASE}/api/auth/login/`).

### JWT usage (HTTP)

After login (see §2), send the access token on every protected request:

```http
Authorization: Bearer <access_token>
```

### JWT lifetimes (server configuration)

Configured in `SIMPLE_JWT`:

| Token | Lifetime |
|-------|----------|
| **access** | 7 days |
| **refresh** | 1 day |

**Important:** There is **no** public `POST /api/token/refresh/` route in the current URL configuration. Mobile apps should:

- Store both `tokens.access` and `tokens.refresh` from `check-sms-code`, and  
- **Re-run the SMS verification flow** (or ask backend team to add SimpleJWT `TokenRefreshView`) when the access token expires.

### WebSockets (JWT via query string)

The ASGI stack uses `TokenAuthMiddleware`: pass the JWT as a query parameter:

```
ws://<host>:<port>/ws/chat/<room_id>/?token=<access_token>
ws://<host>:<port>/ws/order/sos/?token=<access_token>
```

Use `wss://` when the server is behind TLS.

---

## 2. Authentication (SMS + JWT)

Mobile login is **not** username/password. Flow:

1. **`POST /api/auth/login/`** — send phone **or** email + **role**; server sends SMS code (and may return `sms_code` in response in dev/demo setups).
2. **`POST /api/auth/check-sms-code/`** — send same identifier, **4-digit** code, and **role**; server returns **JWT** + user profile.

**Roles** (string, required on both steps): one of `Driver`, `Master`, `Owner`.

### 2.1 Request verification code

| | |
|---|---|
| **METHOD** | `POST` |
| **URL** | `/api/auth/login/` |
| **Auth** | None |
| **Content-Type** | `application/json` |

**Body parameters**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `identifier` | string | **Yes** | Email **or** phone (RU/UZ formats supported; see backend validators). |
| `role` | string | **Yes** | `Driver` \| `Master` \| `Owner` |

**Example**

```json
{
  "identifier": "998901234567",
  "role": "Driver"
}
```

**Example response (200)**

```json
{
  "success": true,
  "message": "Код подтверждения отправлен …",
  "identifier": "998901234567",
  "identifier_type": "phone",
  "phone": "998901234567",
  "email": null,
  "user_exists": true,
  "sms_code": "1234"
}
```

> **Note:** `sms_code` may be present only in non-production or test configurations. Production clients must read the code from SMS.

---

### 2.2 Verify code and obtain JWT

| | |
|---|---|
| **METHOD** | `POST` |
| **URL** | `/api/auth/check-sms-code/` |
| **Auth** | None |
| **Content-Type** | `application/json` |

**Body parameters**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `identifier` | string | **Yes** | Same value as step 1 (email or phone). |
| `sms_code` | string | **Yes** | Exactly **4** digits. |
| `role` | string | **Yes** | `Driver` \| `Master` \| `Owner` |

**Example**

```json
{
  "identifier": "998901234567",
  "sms_code": "1234",
  "role": "Driver"
}
```

**Example response (200)**

```json
{
  "success": true,
  "message": "OK",
  "user": {
    "id": 1,
    "private_id": "…",
    "phone_number": "998901234567",
    "first_name": "",
    "last_name": "",
    "email": "",
    "description": "",
    "is_verified": true,
    "created_at": "2026-01-01T12:00:00Z",
    "roles": [{ "id": 1, "name": "Driver" }],
    "balance": { "amount": "0.00", "updated_at": "…" }
  },
  "user_created": false,
  "tokens": {
    "access": "<jwt_access_token>",
    "refresh": "<jwt_refresh_token>"
  }
}
```

Use **`tokens.access`** in the `Authorization: Bearer` header.

---

### 2.3 Swagger-only OAuth (not for production apps)

| | |
|---|---|
| **METHOD** | `POST` |
| **URL** | `/api/auth/oauth/token/` |
| **Content-Type** | `application/x-www-form-urlencoded` |

Used for Swagger UI convenience; issues JWT for an email without SMS. **Do not rely on this for mobile.**

---

### 2.4 Other public auth-related endpoints

| METHOD | URL | Description |
|--------|-----|-------------|
| `GET` | `/api/auth/sms-status/` | SMS gateway balance / status (ops). |
| `GET` | `/api/auth/faq/` | FAQ list. |
| `GET` | `/api/auth/user/<user_id>/` | Public user profile card (master/driver). |

---

## 3. User profile & devices

**Default:** JWT required (`IsAuthenticated`), unless noted.

| METHOD | URL | Description |
|--------|-----|-------------|
| `GET` | `/api/auth/user/` | Current user details (`success` + `user`). |
| `PUT` | `/api/auth/user/` | Full profile update. **Multipart** supported (`avatar` file). |
| `PATCH` | `/api/auth/user/` | Partial update. Multipart supported. |
| `POST` | `/api/auth/update-telegram-chat-id/` | Body: `chat_id` (string, required). |

**`UserUpdate` JSON fields (PUT/PATCH)** — all optional unless you replace whole object on PUT:

| Field | Type | Required | Notes |
|-------|------|----------|--------|
| `username` | string | No | |
| `first_name` | string | No | |
| `last_name` | string | No | |
| `date_of_birth` | date | No | |
| `avatar` | file | No | multipart |
| `address` | string | No | |
| `longitude` | number | No | |
| `latitude` | number | No | |
| `description` | string | No | |
| `roles` | string | No | e.g. `"Driver"` or `"Driver,Master"` (write-only) |

### Push devices (FCM tokens)

| METHOD | URL | Body / notes |
|--------|-----|----------------|
| `GET` | `/api/auth/devices/` | List devices. |
| `POST` | `/api/auth/devices/` | Register/update: `device_token` (required), `device_type` (optional, default Android in model), `is_active` (optional, default true). |
| `PUT` | `/api/auth/devices/<device_id>/` | Full update device fields. |
| `PATCH` | `/api/auth/devices/<device_id>/` | Body: `is_active` boolean (required). |

---

## 4. Payments & balance (auth)

> **Flow guide (Uzbek):** which API to call first for wallet vs order payment — see [`docs/PAYMENTS_AND_BALANCE.md`](PAYMENTS_AND_BALANCE.md).

| METHOD | URL | Body | Notes |
|--------|-----|------|--------|
| `GET` | `/api/auth/balance/payment-history/` | Query: `kind` (`balance_topup` \| `order` \| `master_topup`), `status`, `limit` (1–100, default 50) | Payment list + current `UserBalance`. Does **not** include accept fee / cancel penalties. |
| `POST` | `/api/auth/balance/sbp-qr/` | `price` (decimal string/number, **min** ≥ **5** RUB per `MIN_SBP_TOPUP_RUB`) | Returns `intent_id`, static SBP `pay_url`, QR base64. |
| `GET` | `/api/auth/balance/sbp-intent/<uuid>/` | — | Intent status; driver balance included when completed **and** caller owns intent. |
| `POST` | `/api/auth/balance/alfa-order-status/` | `alfa_order_id` **or** `alfa_order_number` (at least one); optional `intent_id`, `amount` | Poll Alfa; may complete internal intent. |
| `POST` | `/api/auth/balance/master-topup/` | `master_id` (int), `price` (decimal, **min 1000**) | **Owner** role only; Alfa dynamic pay link. |
| `GET` | `/api/auth/balance/master-available/` | — | **Master**: withdrawable accumulated balance. |
| `POST` | `/api/auth/balance/master-withdraw/` | `price` (decimal, min 0.01) | **Master**: create withdrawal request. |
| `GET` | `/api/auth/balance/master-withdrawals/` | — | **Master**: list withdrawal **requests** (separate from payment-history). |

**Server-to-server (not for mobile):**

| METHOD | URL | Headers / body |
|--------|-----|----------------|
| `POST` | `/api/auth/balance/sbp-webhook/` | `X-Sbp-Webhook-Secret`, JSON: `intent_id`, optional `amount`, `bank_reference` |
| `POST` | `/api/auth/balance/sbp-confirm-by-trx/` | Same secret; `trx_id`, optional `amount` |

---

## 5. Categories

| METHOD | URL | Query | Auth |
|--------|-----|-------|------|
| `GET` | `/api/categories/categories/` | `type` optional: `by_master` \| `by_car` \| `by_order` | None |

---

## 6. Cars (Driver group)

| METHOD | URL | Notes |
|--------|-----|--------|
| `GET` | `/api/car/` | List current user’s cars. |
| `POST` | `/api/car/` | Body: `category` (id), `brand`, `model`, `year` (all required on create). |
| `GET` | `/api/car/<pk>/` | Detail. |
| `PUT` / `PATCH` | `/api/car/<pk>/` | Update. |
| `DELETE` | `/api/car/<pk>/` | 204 No Content. |
| `GET` | `/api/car/stats/` | Aggregated stats for user’s cars. |

---

## 7. Masters

> **Listing rule:** `GET /api/master/masters/list/` returns **empty** if no filter query params are provided (by design).

Common patterns:

| METHOD | URL | Auth | Description |
|--------|-----|------|-------------|
| `GET` | `/api/master/masters/` | Optional | Profiles where current user is owner or employee; `[]` if anonymous. |
| `POST` | `/api/master/masters/` | **Owner** | Create workshop (`multipart` / JSON per serializer). |
| `GET` | `/api/master/masters/list/` | None | Filtered master list (geo + category + etc.). See Swagger for full query set. |
| `GET` | `/api/master/masters/by-user/` | None | Masters linked to user id (query param per `MasterNearbySerializer` / view). |
| `GET` | `/api/master/masters/filter-choices/` | — | Filter metadata. |
| `GET` | `/api/master/masters/<master_id>/` | None | Master detail. |
| `GET` / `POST` | `/api/master/masters/employees/` | Authenticated | Employee management. |
| `GET` | `/api/master/employees/` | — | Employee list view. |
| `POST` | `/api/master/service-items/` | Master | Bulk add service items. |
| `PATCH` | `/api/master/service-items/<item_id>/` | Master | Update item. |
| `DELETE` | `/api/master/service-items/<item_id>/delete/` | Master | Delete item. |
| `POST` | `/api/master/images/` | Master | Upload master images. |
| `PATCH` | `/api/master/images/<image_id>/` | Master | Update image. |
| `DELETE` | `/api/master/images/<image_id>/delete/` | Master | Delete image. |

*(Exact query parameters for `masters/list/` include category, geo `lat`/`long`/`radius`, name search — use `/docs/` for exhaustive list.)*

---

## 8. Orders

### 8.1 Driver-oriented

| METHOD | URL | Auth | Summary |
|--------|-----|------|---------|
| `POST` | `/api/order/scheduled/` | JWT | Create **scheduled** order (`order_type` forced `scheduled` on server). |
| `POST` | `/api/order/sos/` | JWT | Create **SOS** order (`order_type` forced `sos`). |
| `GET` | `/api/order/available-slots/` | JWT | Query: `master_id` (int, **required**), `date` (`YYYY-MM-DD`, **required**). |
| `GET` | `/api/order/` | JWT | List (role-dependent: driver sees own orders; master sees assigned). Query: `status`, `priority`, `master`, `search`, `ordering`. |
| `GET` / `PUT` / `PATCH` / `DELETE` | `/api/order/<id>/` | JWT | CRUD detail (`IsOrderOwnerOrMaster`). |
| `GET` | `/api/order/by-user/` | JWT | Driver’s orders + filters (`status`, `priority`, `category`, `location`, `car_category`, `order_type`, `name`, pagination). |
| `POST` | `/api/order/add-services/` | JWT | Body: `order_id`, `services_list` (int[]), `discount` optional default `0`. |
| `GET` | `/api/order/services-list/` | JWT | Query: `master_id` (**required**). |
| `POST` | `/api/order/reviews/create/` | JWT | Body: see §8.4. |
| `POST` | `/api/order/<order_id>/cancel/` | JWT | **Client cancel** with possible balance penalty. |

**Scheduled / SOS create (conceptual) — fields mirror `OrderCreateSerializer`:**

| Field | Type | Required | Notes |
|-------|------|----------|--------|
| `order_type` | string | Yes* | `scheduled` / `sos` (*views force type per endpoint). |
| `text` | string | Yes | |
| `location` | string | Yes | |
| `latitude` | number | Yes | |
| `longitude` | number | Yes | |
| `car_list` | int[] | Yes | non-empty |
| `category_list` | int[] | Yes | non-empty |
| `master_id` | int | For SOS & scheduled | |
| `priority` | string | SOS | `low` \| `high` |
| `scheduled_date` | date | scheduled | |
| `scheduled_time_start` | time | scheduled | |
| `scheduled_time_end` | time | scheduled | |
| `masters_list` | int[] | No | Extra user IDs to attach |

### 8.2 Master-oriented

| METHOD | URL | Auth | Summary |
|--------|-----|------|---------|
| `GET` | `/api/order/available/` | JWT | Unassigned orders near master. Query: `master_id` (**required**), `radius`, filters. Paginated. |
| `GET` | `/api/order/by-master/` | JWT | Master’s jobs; many filters (`is_new`, `is_work`, `is_archive`, geo polygon, `order_type`, …). |
| `GET` | `/api/order/incoming-sync/` | JWT | **Master**: active incoming orders for this user (WS/push fallback). |
| `POST` | `/api/order/<order_id>/accept/` | JWT | Accept job; balance rules (min **1000** ₽, **200** ₽ fee). |
| `POST` | `/api/order/<order_id>/decline/` | JWT | Decline / reject per business rules (SOS broadcast vs scheduled). |
| `POST` | `/api/order/<order_id>/workflow/` | JWT | Body: `status` = `on_the_way` \| `arrived` \| `in_progress`. |
| `POST` | `/api/order/<order_id>/work-completion-images/` | JWT | Multipart: `images` (files, max 15). |
| `POST` | `/api/order/<order_id>/complete/` | JWT | Complete order + payment intent / Alfa `form_url` for client. See [`PAYMENTS_AND_BALANCE.md`](PAYMENTS_AND_BALANCE.md) §B. |
| `POST` | `/api/order/<order_id>/payment/resend/` | JWT | New Alfa payment link. |
| `POST` | `/api/order/<order_id>/master-cancel/` | JWT | Body: `cancel_reason` ∈ `customer_no_show`, `vehicle_not_ready`, `emergency`, `other` (**not** `too_far`). |
| `POST` | `/api/order/add-masters/` | JWT | Body: `order_id`, `master_ids` (non-empty user id list). |
| `POST` | `/api/order/<order_id>/status/` | JWT | Status updates **except** lifecycle states reserved for `accept` / `workflow` (see server validation). |

### 8.3 Order statuses (enum)

`pending`, `accepted`, `on_the_way`, `arrived`, `in_progress`, `completed`, `cancelled`, `rejected`

Typical master flow: `accept` → `workflow` (`on_the_way` → `arrived` → `in_progress`) → service lines → `complete` → client pays.

### 8.4 Review body

| Field | Type | Required |
|-------|------|----------|
| `order_id` | int | Yes |
| `rating` | int | Yes (1–5) |
| `tag` | string | Yes (enum `ReviewTag` in backend) |
| `comment` | string | No |

---

## 9. Chat

Pagination: default **20** / page, `page_size` max **100**.

| METHOD | URL | Description |
|--------|-----|-------------|
| `GET` | `/api/chat/rooms/` | List rooms (paginated). |
| `POST` | `/api/chat/rooms/` | Body: `participant_id` (int). |
| `GET` | `/api/chat/rooms/<room_id>/` | Room detail. |
| `GET` | `/api/chat/rooms/<room_id>/messages/` | Message history (paginated). |
| `POST` | `/api/chat/rooms/<room_id>/messages/` | Send message — prefer **multipart** if attaching files. |
| `POST` | `/api/chat/rooms/<room_id>/mark-read/` | Mark peer messages read (empty body). |

**Send message fields (`SendMessageSerializer`):**

| Field | Type | Required | Notes |
|-------|------|----------|--------|
| `room` | int | Set automatically from URL in handler | |
| `message_type` | string | Yes | `text` \| `image` \| `file` \| `audio` |
| `text` | string | If type=`text` | |
| `image` | file | If type=`image` | |
| `file` | file | If type=`file` | |
| `audio` | file | If type=`audio` | |

---

## 10. Errors & pagination

- **401** `{"detail": "Authentication credentials were not provided."}` — missing/invalid JWT.  
- Many endpoints return **`{"success": false, ...}`** (auth/app) or field-level validation errors `{ "field": ["…"] }`.
- **Global pagination** (where `LimitOffsetPagination` applies): query `limit` (default **100**), `offset`.  
- **Chat / some order lists** use **page** / **page_size** instead — see each section.

---

## 11. Source of truth

If this document drifts from the backend, regenerate from the live schema:

- `GET /schema/` — OpenAPI 3
- `GET /docs/` — Swagger UI

**Document version:** generated from repository state as of internal audit (CheckAvto DRF + JWT + SMS auth).
