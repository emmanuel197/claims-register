# Claims Register

A small web application that records insurance claims and the payments made against them, derives each claim's status from its money position, and shows a filterable list with a per-currency totals row.

- **Live app:** _see the deployment section — URL added after first deploy_
- **API:** _added after first deploy_ (`/api/claims/`, `/api/health/`)
- **Stack:** Django 5.2 + Django REST Framework on Render · React 19 + Vite + Tailwind 4 on Vercel · PostgreSQL on Neon

```
claims-register/
├── backend/    Django project (config/) and the `claims` app
└── frontend/   Vite + React single-page app
```

## Running locally

Prerequisites: Python 3.12, Node 20+, and a PostgreSQL database (Docker is the quickest way).

```bash
# 1. Database
cd backend
docker compose up -d                 # postgres:16 on localhost:5432 (user/pass/db: claims)

# 2. API
python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                                  # DATABASE_URL already points at the docker db
python manage.py migrate
python manage.py seed_claims                          # 18 sample claims, idempotent
python manage.py runserver                            # http://localhost:8000/api/claims/

# 3. Frontend (new terminal)
cd frontend
npm install
npm run dev                                           # http://localhost:5173 — proxies /api to Django
```

Tests and smoke checks:

```bash
cd backend
python manage.py test                # 55 tests: rounding, status, constraints, totals identities, API
bash scripts/smoke.sh                # curl + jq against a running API; pass the hosted URL to check production
```

Postgres is required (SQLite is deliberately unsupported): money columns are `numeric` and the totals row is summed in SQL, which SQLite would do in floating point. Settings refuse to start without a Postgres `DATABASE_URL`.

## How it works

### Data model

```
Claim                                   Payment
─────                                   ───────
id (sequence → CLM-00042)               claim  → Claim (PROTECT)
policy_number        indexed            payment_date
insured_name                            amount                  what was actually paid
loss_date            indexed            currency                … and in which currency
date_notified        indexed            exchange_rate           claim ccy per 1 payment ccy (1 when same)
loss_nature          enum               amount_in_claim_currency  amount × rate, rounded once, stored
currency             GHS|USD|EUR|GBP    reference
estimated_loss_amount  numeric(14,2)
approved_amount        numeric(14,2), null until settled
approved_at
```

Database `CHECK` constraints back up the API validation: `estimated_loss_amount > 0`, `approved_amount IS NULL OR > 0`, `date_notified >= loss_date`, `approved_amount` and `approved_at` set together, `payment.amount <> 0`, `exchange_rate > 0`.

### Derived figures (`backend/claims/queries.py`)

Nothing about the money position is stored twice. `total_paid`, `outstanding_balance` and `status` are queryset annotations computed in SQL:

```
total_paid          = Σ payments.amount_in_claim_currency          (0 when none)
outstanding_balance = approved_amount − total_paid                 (NULL until approved)
status              = reserved              if approved_amount is NULL
                      settled_outstanding   if outstanding_balance > 0
                      settled_paid          otherwise (zero or below)
```

Because status is an annotation, the list filters on it in a `WHERE` clause, and the totals row is one grouped aggregate over exactly the same filtered rows — so the footer always equals the sum of the rows above it. `test_totals.py` asserts that, plus the accounting identities `approved − paid_on_settled = outstanding` and `paid_on_settled + paid_on_reserved = total_paid`, for every currency.

### Cross-currency payments

A claim is reserved in one currency and every claim-level figure is in that currency. A payment in another currency records the amount actually paid, its currency, and an exchange rate (claim currency per one unit of payment currency). The converted amount is computed once at recording time, rounded half-up to 2 dp, and **stored** — so historical totals never move when rates do, and the footer is the sum of the visible rows rather than a re-rounded recomputation. The UI prefills an indicative rate; the user confirms or edits it before saving. This follows how paid losses are treated in practice (payment-date rate per payment) rather than re-valuing at a live rate.

### API

| Method | Path | Notes |
| --- | --- | --- |
| GET | `/api/health/` | `{"status":"ok"}` |
| GET | `/api/meta/` | Select options and dated indicative FX rates for the forms |
| GET | `/api/claims/` | Filters: `date_from`, `date_to` (inclusive), `date_field=loss_date\|date_notified`, `status`, `currency`, `search`; `ordering`. Returns `{count, results, totals}` |
| POST | `/api/claims/` | Register a claim (optionally with `approved_amount`) |
| GET | `/api/claims/{id}/` | Claim with derived figures and its payments |
| PATCH | `/api/claims/{id}/` | Edit header fields; set or change `approved_amount` |
| GET / POST | `/api/claims/{id}/payments/` | List / record a payment; POST returns the payment and the refreshed claim |

Money is serialised as strings (`"1250.00"`) so no client ever receives a float. `totals.by_claim_currency` has one row per claim currency with `estimated_loss_amount`, `approved_amount`, `total_paid`, `paid_on_settled`, `paid_on_reserved`, `outstanding_balance`, `overpaid` and `claims`; `totals.paid_by_payment_currency` shows what actually left the bank, by payment currency.

## Assumptions and decisions

The brief left several things open; these are the calls I made.

**Money and currency**
- A claim has exactly one (reserve) currency. Estimated, approved, total paid and outstanding are all expressed in it, and the totals row is grouped by **claim** currency. Actual outflows by **payment** currency are shown separately beneath the footer.
- Exchange rates are supplied by the user at recording time (prefilled from dated indicative constants, not market data). There is no live FX lookup — a demo that depends on a third-party rate API is fragile, and in practice the rate on a payment voucher is a recorded fact, not a lookup.
- Conversion rounds once, half-up, to 2 dp, at storage. Sums are over stored values.
- A same-currency payment stores rate `1`; supplying any other rate for it is rejected (400) rather than silently ignored.
- Payments are immutable. A mistake is corrected with a reversing negative payment at the original rate (the "Reverse" action prefills this), so the pair nets to exactly zero. There are no delete endpoints for claims or payments.

**Status and balance**
- "Outstanding balance (approved less paid)" is undefined until an approved amount exists, so it is shown as `—` and the claim is *Reserved*. Interim payments **are** allowed on reserved claims (advances are normal); they count in *Total paid* and in the footer's `paid_on_reserved`, but are not deducted from any balance until approval.
- Balance exactly `0` → *Settled and paid*, as the brief says ("zero or below"). A negative balance (overpayment) is also *Settled and paid* and is shown in red; the footer nets it and reports the overpaid total in a tooltip.
- `approved_amount` must be `> 0` when set (an approval of zero would masquerade as "paid"). It can be set at registration or later, and raised or lowered afterwards, but never removed. `approved_at` records the first approval.
- Claim currency is locked once a payment exists (changing it would silently re-denominate stored conversions).

**List and filters**
- The date range applies to `loss_date` by default, switchable to `date_notified`; both bounds are inclusive, dates only, no time zone. The range selects *claims*; money figures are always current, not "as of" the range.
- Filters drive both the rows and the footer. The list is unpaginated (the brief's scale is tens of claims).
- Sorting is available on loss date, date notified, estimated and outstanding.

**Validation**
- No date may be in the future ("today" is UTC on the server; Ghana is on GMT). `date_notified >= loss_date`; `payment_date >= loss_date`. `estimated_loss_amount > 0`; `payment.amount != 0`.
- `policy_number` is not unique (a policy can have several claims). Four currencies and eight loss natures are supported.

**Seed and hosting**
- `seed_claims` is idempotent on `(policy_number, loss_date)` and runs on every deploy, so claims a reviewer enters survive redeploys and the 18 samples are never duplicated. Claim numbers come from the database sequence and may have gaps.
- The API runs on Render's free tier and sleeps when idle: the first request after a quiet spell can take 30–60 s. The UI says so while it waits.

## What I would do differently with more time

- **Reserve re-valuation.** Outstanding reserves on foreign-currency claims would be re-measured at a statement-date rate for reporting, with paid losses staying at their historical rates — the standard split between transaction-date and balance-sheet-date rates. That needs a rates table and an "as-of" parameter on the list.
- **Audit history** for approval changes and payment corrections (an event table rather than `approved_at` alone), and payment editing with a full trail instead of reversal-only.
- **Pagination and server-side totals over large sets**, plus CSV export of the filtered list with its footer.
- **Authentication and roles** (adjuster vs. finance), which the brief scoped out.
- **Frontend tests** (Vitest + Testing Library for the money formatting and forms; Playwright for the register → approve → pay flow the smoke script currently covers at the API level).
- **Live FX lookup as a suggestion** (still user-confirmed), with the rate source and timestamp stored on the payment.
- A managed Postgres on the same provider as the API to remove the Neon cold-start from the first request.

## Deployment

- **API (Render):** blueprint in `render.yaml` at the repo root — Python web service with root directory `backend/`, build `bash build.sh` (installs, collects static, migrates, seeds), start `gunicorn`. Environment: `DATABASE_URL` (Neon), `CORS_ALLOWED_ORIGINS` (the Vercel URL), `SECRET_KEY`, `DEBUG=False`, `ALLOWED_HOSTS=.onrender.com`.
- **Frontend (Vercel):** root `frontend/`, framework Vite, environment `VITE_API_BASE_URL=https://<render-service>.onrender.com/api`. `vercel.json` rewrites all routes to `index.html` for client-side routing.
