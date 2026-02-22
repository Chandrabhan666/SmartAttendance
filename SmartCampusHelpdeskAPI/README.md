# Smart Campus Helpdesk API (Separate Project)

This is a completely separate project from SmartAttendance.

## Tech Stack
- Django
- Django REST Framework
- JWT (SimpleJWT)
- PostgreSQL
- django-filter

## Implemented Features
- Django project + app setup
- PostgreSQL integration
- Ticket model with required fields
- CRUD APIs for tickets
- JWT-based authentication
- Admin login (session auth at `/admin/`)
- Pagination
- Filtering by `category` and `status`
- Ordering by `priority` and `created_at`
- Search by `title` or `description`
- Redis marked as future enhancement (not implemented)

## Project Path
`/Users/chandrabhanpatel/Downloads/SmartAttendance/SmartCampusHelpdeskAPI`

## Default Users Created
- Admin (for `/admin/` + API): `admin` / `Admin@12345`
- API user: `student1` / `Student@12345`

## PostgreSQL (Local Dedicated Instance for This Project)
This project uses its own PostgreSQL data directory: `.postgres/data`
and runs on port `5433`.

### Start DB
```bash
cd /Users/chandrabhanpatel/Downloads/SmartAttendance/SmartCampusHelpdeskAPI
./scripts/start_postgres.sh
```

### Stop DB
```bash
cd /Users/chandrabhanpatel/Downloads/SmartAttendance/SmartCampusHelpdeskAPI
./scripts/stop_postgres.sh
```

## Run API
```bash
cd /Users/chandrabhanpatel/Downloads/SmartAttendance/SmartCampusHelpdeskAPI
source .venv/bin/activate
python manage.py runserver
```

## Authentication Flow
1. Get JWT tokens with username + password.
2. Use access token in header:
   `Authorization: Bearer <access_token>`
3. Use refresh token to get new access token.
4. Admin can also use Django session auth at `/admin/`.

## API Endpoints
- `POST /api/token/`
- `POST /api/token/refresh/`
- `POST /tickets/`
- `GET /tickets/`
- `GET /tickets/<id>/`
- `PATCH /tickets/<id>/`
- `DELETE /tickets/<id>/`

## Query Support on List API
`GET /tickets/?category=network&status=open&search=wifi&ordering=priority&page=1`

- Filtering: `category`, `status`
- Search: `search` on title/description
- Ordering:
  - `ordering=priority`
  - `ordering=-priority`
  - `ordering=created_at`
  - `ordering=-created_at`
- Pagination: `page`

## Required Sample Payload (Included)
File: `sample_ticket.json`

```json
{
  "title": "WiFi not working",
  "description": "No internet in block A",
  "category": "network",
  "priority": "high"
}
```

## Quick API Test Commands

### 1) Get JWT token
```bash
curl -X POST http://127.0.0.1:8000/api/token/ \
  -H "Content-Type: application/json" \
  -d '{"username":"student1","password":"Student@12345"}'
```

### 2) Create ticket with your payload
```bash
curl -X POST http://127.0.0.1:8000/tickets/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  -d @sample_ticket.json
```

### 3) List tickets with all list features
```bash
curl "http://127.0.0.1:8000/tickets/?category=network&status=open&search=internet&ordering=priority&page=1" \
  -H "Authorization: Bearer <ACCESS_TOKEN>"
```

## Run Tests
```bash
cd /Users/chandrabhanpatel/Downloads/SmartAttendance/SmartCampusHelpdeskAPI
source .venv/bin/activate
python manage.py test
```
