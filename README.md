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
│   ├── celery.py            # Celery app
│   ├── wsgi.py
│   └── asgi.py
├── apps/
│   ├── core/                # Shared base models, utils, permissions
│   ├── users/               # Custom user model, auth, profiles
│   ├── rentals/             # Consoles, rentals, reviews
│   └── payments/            # Stripe payments, webhooks
├── templates/
├── static/
├── media/
├── requirements/
│   ├── base.txt
│   ├── dev.txt
│   └── prod.txt
├── docker-compose.yml
├── Dockerfile
├── Makefile
└── manage.py
```

## License

Private — All rights reserved.
