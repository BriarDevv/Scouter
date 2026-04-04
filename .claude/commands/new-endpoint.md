Create a new API endpoint for Scouter.

The user will provide: endpoint path, HTTP method, purpose, and request/response shape.

## Checklist

1. **Create or update the endpoint file** in `app/api/v1/<resource>.py`
2. **Define schemas** in `app/schemas/<resource>.py`:
   - `XxxCreate` for POST request body
   - `XxxUpdate` for PATCH request body
   - `XxxResponse` for response
   - Use `model_config = {"from_attributes": True}` for ORM mode
3. **Add service function** in `app/services/<resource>_service.py`:
   - Stateless function, takes `db: Session` as first param
   - Raise custom exceptions for domain errors
4. **Register the router** in `app/api/router.py` if it's a new file
5. **Add the model** if needed in `app/models/` + export in `app/models/__init__.py`
6. **Create migration** if new model: `alembic revision --autogenerate -m "description"`
7. **Add frontend API function** in `dashboard/lib/api/client.ts`
8. **Add frontend types** in `dashboard/types/index.ts`

## Conventions

- UUID primary keys with `default=uuid.uuid4`
- Endpoints use `Depends(get_session)` for DB access
- POST returns `status_code=201` with `response_model=XxxResponse`
- Async tasks: queue via Celery `.delay()`, track with `queue_task_run()`, return `TaskEnqueueResponse`
- Logging: `logger.info("event_name", resource_id=id)` — structured, no f-strings
- Error responses: `HTTPException(status_code=xxx, detail="descriptive message")`

## Patterns to follow

- Simple CRUD: `app/api/v1/suppression.py`
- Complex with async: `app/api/v1/pipelines.py`
- Settings-heavy: `app/api/v1/settings.py`

## After creation

Run:
```bash
pytest -v              # Backend tests
alembic upgrade head   # Apply migration if created
```
