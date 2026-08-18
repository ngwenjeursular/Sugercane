# Sugercane backend foundation

Security-first FastAPI/PostgreSQL starter for users, wallets, ledger transactions, sessions and a configurable 3-level referral tree.

## Referral defaults
Level 1 = 5%, Level 2 = 1%, Level 3 = 0.5%. These are applied to qualifying revenue, not deposited principal, and are configurable in the database.

## Local setup
1. Copy `.env.example` to `.env` and change secrets before sharing/deploying.
2. `docker compose up -d db`
3. `python -m venv .venv`
4. Activate the venv.
5. `pip install -r requirements.txt`
6. `alembic upgrade head`
7. `uvicorn app.main:app --reload`

Development API docs: `/docs`.

## Security notes
Passwords use Argon2id. Sessions are opaque random tokens whose hashes are stored in the database. Auth uses HttpOnly/Secure/SameSite cookies; state-changing cookie-authenticated requests require an X-CSRF-Token. Financial transactions have external-reference and idempotency fields so M-Pesa callbacks can later be reconciled without double-crediting.

This is not yet a live-money system. M-Pesa/Daraja integration, payment reconciliation, authorization controls, rate limiting, audit logging, monitoring, backups, secret management and production deployment still need to be implemented and reviewed before real funds are accepted.
