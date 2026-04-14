# Backend for hair salon course project

This repository contains a Django backend for the course project "Hair salon online booking".

## Implemented foundation

- separate Role and AccessRight entities
- custom User linked to Role
- services, statuses, and master schedules
- appointments with overlap checks
- transactions, AI prediction data, and audit log
- JWT auth endpoints for register/login/profile
- OpenAPI schema and Swagger-style docs page
- seed command for demo data
- Django admin and REST API endpoints

## Run locally

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:POSTGRES_DB = "hair_salon_db"
$env:POSTGRES_USER = "postgres"
$env:POSTGRES_PASSWORD = "postgres"
$env:POSTGRES_HOST = "127.0.0.1"
$env:POSTGRES_PORT = "5432"
.\.venv\bin\python.exe manage.py migrate
.\.venv\bin\python.exe manage.py seed_demo_data
.\.venv\bin\python.exe manage.py createsuperuser
.\.venv\bin\python.exe manage.py runserver
```

## Main API endpoints

- `/api/docs/`
- `/api/schema/`
- `/api/auth/register/`
- `/api/auth/login/`
- `/api/auth/refresh/`
- `/api/auth/profile/`
- `/api/auth/logout/`
- `/api/roles/`
- `/api/access-rights/`
- `/api/users/`
- `/api/services/`
- `/api/statuses/`
- `/api/master-schedules/`
- `/api/appointments/`
- `/api/appointments/{id}/confirm/`
- `/api/appointments/{id}/cancel/`
- `/api/appointments/{id}/complete/`
- `/api/appointments/{id}/pay/`
- `/api/appointments/{id}/predict-no-show/`
- `/api/transactions/`
- `/api/ai-data/`
- `/api/ai/train/`
- `/api/ai/model-info/`
- `/api/audit-logs/`

## Notes

- PostgreSQL is used as the main database for the project.
- Database connection settings are taken from `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST`, and `POSTGRES_PORT`.
- Before running Django, make sure the PostgreSQL server is installed, started, and the target database already exists.
- The schema now follows the ER diagram more closely, with dedicated entities for roles, statuses, transactions, and AI data.
- AI endpoint stores prediction results in `Aidata` using a trained MLP-style neural network, with a heuristic fallback until the model is trained.
- Swagger-style docs page loads the OpenAPI schema from `/api/schema/`.
