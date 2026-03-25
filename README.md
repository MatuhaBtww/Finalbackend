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
cmd /c "for %I in (.) do @echo %~sI"
$env:SQLITE_NAME = "SHORT_PATH_FROM_COMMAND\\db.sqlite3"
.\.venv\bin\python.exe manage.py migrate
.\\.venv\\bin\\python.exe manage.py seed_demo_data
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
- `/api/audit-logs/`

## Notes

- SQLite is used as the default development database.
- If SQLite raises a disk I/O error inside OneDrive, set `SQLITE_NAME` to a short ASCII path for the database file.
- The schema now follows the ER diagram more closely, with dedicated entities for roles, statuses, transactions, and AI data.
- AI endpoint stores prediction results in `Aidata` using a built-in heuristic scorer for no-show probability.
- Swagger-style docs page loads the OpenAPI schema from `/api/schema/`.
