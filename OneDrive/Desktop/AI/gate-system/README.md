# Gate System (Raspberry Pi Entrance Control) — Microservices Starter

Production-ready starter for a physical entrance gate with RFID/NFC access, balance management, payments (cash/card), and Raspberry Pi hardware control.

## Architecture

- **Frontend**: React + TypeScript (Vite), TanStack Query, Axios, protected routes, admin dashboard
- **Backend**: 5 Python **FastAPI** microservices (async), REST, OpenAPI
- **Database**: PostgreSQL (normalized tables, separated by service schemas)
- **Cache/Broker**: Redis (caching + pub/sub for real-time events)
- **Reverse proxy**: Nginx (single public entrypoint)
- **Auth**: JWT (access + refresh), RBAC (user/admin)
- **Hardware**: Raspberry Pi GPIO/serial abstraction with **mock mode**

Services:

- `user-service`: auth, users, roles/permissions
- `chip-service`: chip registry/assignment, balances, chip history
- `payment-service`: card/cash abstraction, transactions, refunds, recharge ops
- `hardware-service`: RFID reader + coin acceptor + relay lock + health monitoring
- `access-control-service`: orchestrates entrance authorization, logs access, real-time events

## Quickstart (Docker)

1. Copy env examples:

```bash
cd gate-system
cp .env.example .env
cp services/user-service/.env.example services/user-service/.env
cp services/chip-service/.env.example services/chip-service/.env
cp services/payment-service/.env.example services/payment-service/.env
cp services/hardware-service/.env.example services/hardware-service/.env
cp services/access-control-service/.env.example services/access-control-service/.env
cp apps/dashboard/.env.example apps/dashboard/.env
```

2. Start everything:

```bash
docker compose up --build
```

3. Open:

- **Dashboard**: `http://localhost/`
- **OpenAPI**:
  - `http://localhost/api/users/docs`
  - `http://localhost/api/chips/docs`
  - `http://localhost/api/payments/docs`
  - `http://localhost/api/hardware/docs`
  - `http://localhost/api/access/docs`

## Real-time events

- Services publish events to Redis channels (e.g. `hardware.events`, `access.events`).
- `access-control-service` exposes WebSockets at `/ws/events` and forwards pub/sub events to connected dashboards.

## Where card payment callbacks arrive

- `payment-service` exposes provider webhook endpoints under `/webhooks/*`.
- Webhooks validate signature, update `transactions`, and publish `payment.events` to Redis.
- `access-control-service` subscribes to payment events for flows like “recharge” completion.

## Raspberry Pi hardware communication

- `hardware-service` runs on the Pi (or locally with mock mode).
- It reads RFID scans and cash acceptor pulses via GPIO/serial, controls a relay for the door lock, and publishes events to Redis.
- `access-control-service` triggers door opens by calling `hardware-service` REST endpoint `/door/open` (and can also publish to Redis if you prefer command channels).

## Folder structure

```
gate-system/
  apps/
    dashboard/                 # React TS app
  services/
    access-control-service/
    chip-service/
    hardware-service/
    payment-service/
    user-service/
  shared/
    py/                        # shared Python package (schemas, auth, errors)
  deploy/
    nginx/
    postgres/
  diagrams/                    # Mermaid + UML-like docs
```

## Testing

- Unit tests per service: `pytest`
- Integration tests (docker): planned under `tests/integration/` (starter included)

## Next steps (typical)

- Replace `payment-service` provider stub with Stripe/Adyen/etc.
- Add Alembic migrations per service schema
- Harden production settings (TLS, secrets manager, HSTS, rate limiting config)

