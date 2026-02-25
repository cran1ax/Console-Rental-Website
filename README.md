# Corner Console 🎮

PlayStation Rental Platform — rent PS4/PS5 consoles with ease.

## Tech Stack

- **Backend:** Django 5.1, Django REST Framework
- **Database:** PostgreSQL 16
- **Auth:** django-allauth + JWT (dj-rest-auth + SimpleJWT)
- **Payments:** Stripe
- **Task Queue:** Celery + Redis
- **Docs:** drf-spectacular (Swagger / ReDoc)

## Quick Start

```bash
# 1. Clone & enter project
cd "Console Rental Website"

# 2. Create virtual environment
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS/Linux

# 3. Install dependencies
pip install -r requirements/dev.txt

# 4. Copy environment variables
copy .env.example .env        # Windows
# cp .env.example .env        # macOS/Linux

# 5. Start PostgreSQL & Redis (Docker)
docker compose up -d db redis

# 6. Run migrations
python manage.py makemigrations
python manage.py migrate

# 7. Create superuser
python manage.py createsuperuser

# 8. Run development server
python manage.py runserver
```

## API Docs

- Swagger UI: http://localhost:8000/api/docs/
- ReDoc: http://localhost:8000/api/redoc/
- Schema: http://localhost:8000/api/schema/

## API Endpoints

### Auth
| Method | Endpoint                          | Description           |
|--------|-----------------------------------|-----------------------|
| POST   | `/api/v1/auth/registration/`      | Register              |
| POST   | `/api/v1/auth/login/`             | Login (JWT)           |
| POST   | `/api/v1/auth/token/refresh/`     | Refresh token         |
| GET    | `/api/v1/auth/me/`                | Current user          |
| PATCH  | `/api/v1/auth/me/profile/`        | Update profile        |

### Rentals
| Method | Endpoint                               | Description           |
|--------|----------------------------------------|-----------------------|
| GET    | `/api/v1/rentals/consoles/`            | List consoles         |
| GET    | `/api/v1/rentals/consoles/{slug}/`     | Console detail        |
| POST   | `/api/v1/rentals/bookings/`            | Create rental         |
| GET    | `/api/v1/rentals/bookings/`            | My rentals            |
| POST   | `/api/v1/rentals/bookings/{id}/cancel/`| Cancel rental         |
| POST   | `/api/v1/rentals/reviews/`             | Submit review         |

### Payments
| Method | Endpoint                               | Description           |
|--------|----------------------------------------|-----------------------|
| POST   | `/api/v1/payments/create-intent/`      | Create payment intent |
| GET    | `/api/v1/payments/`                    | Payment history       |
| POST   | `/api/v1/payments/webhook/stripe/`     | Stripe webhook        |

## Project Structure

```
├── config/                  # Django project configuration
│   ├── settings/
│   │   ├── base.py          # Base settings
│   │   ├── dev.py           # Development overrides
│   │   ├── prod.py          # Production overrides
│   │   └── test.py          # Test overrides
│   ├── urls.py              # Root URL config
│   ├── celery.py            # Celery app + beat schedule
│   ├── wsgi.py
│   └── asgi.py
├── apps/
│   ├── core/                # Shared base models, utils, permissions
│   ├── users/               # Custom user model, auth, profiles
│   ├── rentals/             # Consoles, rentals, reviews, Celery tasks
│   └── payments/            # Stripe payments, webhooks, Celery tasks
├── docker/
│   └── entrypoint.sh        # Production entrypoint (migrate + collectstatic)
├── nginx/
│   └── nginx.conf           # Nginx reverse proxy config
├── templates/
│   └── emails/              # HTML email templates
├── static/
├── media/
├── requirements/
│   ├── base.txt
│   ├── dev.txt
│   └── prod.txt
├── frontend/                # React 18 + Vite SPA
├── docker-compose.yml       # Development services
├── docker-compose.prod.yml  # Production stack (Nginx + Gunicorn + Celery)
├── Dockerfile               # Multi-stage production build
├── gunicorn.conf.py         # Gunicorn configuration
├── Makefile                 # Dev & prod shortcuts
└── manage.py
```

## Celery Tasks

| Task | Schedule | Description |
|------|----------|-------------|
| `send_rental_end_reminders` | Daily @ 9:00 AM | Email users whose rental ends tomorrow |
| `auto_mark_late_rentals` | Daily @ 00:05 | Mark overdue ACTIVE rentals as LATE |
| `auto_refund_deposits` | Daily @ 10:00 AM | Refund deposits for on-time returns |
| `expire_stale_checkout_sessions` | Every 30 min | Expire abandoned payment sessions |

## Production Deployment

### Prerequisites

- Docker & Docker Compose v2
- Domain name with DNS configured
- (Optional) SSL certificate or use Let's Encrypt

### 1. Clone & Configure

```bash
git clone https://github.com/cran1ax/Console-Rental-Website.git
cd Console-Rental-Website

# Create production environment file
cp .env.prod.example .env.prod
# Edit .env.prod with your production values (database, Stripe live keys, SMTP, etc.)
```

### 2. Build & Start

```bash
# Build all images
make prod-build

# Start all services (Nginx, Gunicorn, PostgreSQL, Redis, Celery, Flower)
make prod-up

# Create superuser
make prod-createsuperuser
```

### 3. Verify

```bash
# Check service status
make prod-status

# Tail logs
make prod-logs

# Health check
curl http://yourdomain.com/health/
```

### 4. SSL Setup (Optional)

1. Place your SSL certificates in `nginx/ssl/`:
   - `fullchain.pem`
   - `privkey.pem`
2. Uncomment the SSL lines in `nginx/nginx.conf`
3. Restart: `make prod-restart`

### Architecture

```
                ┌─────────────┐
    Internet ──▶│    Nginx    │
                │  (port 80)  │
                └──────┬──────┘
                       │
          ┌────────────┼────────────┐
          │            │            │
    /static/     /media/      proxy_pass
    /media/                        │
                            ┌──────▼──────┐
                            │  Gunicorn   │
                            │  (port 8000)│
                            └──────┬──────┘
                                   │
                ┌──────────────────┼──────────────────┐
                │                  │                   │
         ┌──────▼──────┐   ┌──────▼──────┐   ┌───────▼───────┐
         │ PostgreSQL  │   │    Redis    │   │ Celery Worker │
         │   (5432)    │   │   (6379)    │   │ + Beat        │
         └─────────────┘   └─────────────┘   └───────────────┘
```

### Production Makefile Commands

| Command | Description |
|---------|-------------|
| `make prod-build` | Build Docker images |
| `make prod-up` | Start all services |
| `make prod-down` | Stop all services |
| `make prod-logs` | Tail all logs |
| `make prod-logs-web` | Tail web + nginx logs |
| `make prod-restart` | Restart web + workers |
| `make prod-shell` | Django shell in container |
| `make prod-migrate` | Run migrations |
| `make prod-status` | Show service status |
| `make prod-backup-db` | Backup PostgreSQL |

## License

Private — All rights reserved.
