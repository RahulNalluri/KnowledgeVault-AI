# KnowledgeVault AI

KnowledgeVault AI is a planned multi-user retrieval-augmented generation (RAG) platform for securely organizing documents and asking grounded questions across private organizational knowledge bases.

> **Project status:** Phase 0 is complete and Phase 1 is active. The Django foundation now has split environment settings, pinned dependencies, tested health endpoints, and a Dockerized PostgreSQL 17 database with pgvector. Redis, Celery, the backend container, and the frontend remain upcoming foundation work.

## Product vision

The finished platform will let individuals and teams:

- Create isolated organization workspaces and invite members.
- Create multiple knowledge bases with role-aware access.
- Upload PDF, DOCX, TXT, and Markdown files for asynchronous processing.
- Search authorized content with vector and keyword retrieval.
- Ask questions and receive grounded answers with validated citations.
- Inspect sources, provide feedback, and monitor usage and processing health.

The design prioritizes tenant isolation, transparent RAG logic, testability, and honest no-answer behavior.

## Planned architecture

The monorepo will contain a Django REST API, Celery workers, a Next.js frontend, PostgreSQL with pgvector, Redis, and Nginx. Development and production deployments will use separate Docker Compose configurations.

```mermaid
flowchart LR
    User["Web user"] --> Web["Next.js frontend"]
    Web --> API["Django REST API"]
    API --> DB[("PostgreSQL + pgvector")]
    API --> Redis[("Redis")]
    API --> Storage["Object storage"]
    Redis --> Worker["Celery workers"]
    Worker --> DB
    Worker --> Storage
    Worker --> Embed["Embedding provider"]
    API --> LLM["LLM provider"]
```

The diagram above summarizes the planned service boundaries. Implementation is proceeding incrementally from the Django and PostgreSQL foundation.

## Technology plan

| Area | Planned technology |
| --- | --- |
| Backend | Python 3.12+ (3.13.5 verified), Django 6.0.7 |
| Tasks | Celery and Redis |
| Data | PostgreSQL, pgvector, PostgreSQL full-text search |
| AI | Sentence Transformers behind an embedding interface; OpenRouter behind an LLM interface |
| Frontend | Next.js, React, TypeScript, Tailwind CSS, accessible UI primitives |
| API | Versioned REST API with OpenAPI via drf-spectacular |
| Infrastructure | Docker Compose, Nginx, Gunicorn/Uvicorn, S3-compatible production storage |
| Quality | pytest, Ruff, mypy where practical, frontend unit/E2E tests, GitHub Actions |

Active backend dependencies and development tools are pinned in `backend/pyproject.toml`. Later-phase dependencies will be added only when their features are introduced.

## Repository layout

Current foundation files:

```text
.
|-- README.md
|-- .gitignore
|-- .env.example
|-- backend/
|   |-- manage.py
|   |-- pyproject.toml
|   |-- config/
|   `-- apps/
|       `-- health/
|-- docker/
|   `-- postgres/init/
|-- docker-compose.yml
`-- docker-compose.dev.yml
```

The `frontend/` and remaining infrastructure services will be created during later Phase 1 slices rather than represented by empty placeholders.

## Local setup

PowerShell setup from the repository root:

```powershell
Copy-Item .env.example .env
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install --editable ".\backend[dev]"
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d postgres
```

Bash equivalent:

```bash
cp .env.example .env
python -m venv venv
source venv/bin/activate
python -m pip install --upgrade pip
python -m pip install --editable "./backend[dev]"
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d postgres
```

The development database is available on `localhost:5432`. The named volume preserves data when the container stops. Do not use the known development credentials from `.env.example` in any deployed environment.

## Environment variables

Secrets and environment-specific values must never be committed. Copy `.env.example` to the ignored `.env` file for local development. Development loads this root file without overriding variables already supplied by the shell. Production never loads `.env` and fails closed when required settings are absent.

## Development commands

Current verification commands:

```powershell
.\venv\Scripts\ruff.exe check backend
.\venv\Scripts\ruff.exe format --check backend
.\venv\Scripts\pytest.exe backend --config-file backend\pyproject.toml
.\venv\Scripts\python.exe backend\manage.py check
```

The implemented operational endpoints are:

- `GET /api/v1/health/live/` — confirms the Django process can serve requests.
- `GET /api/v1/health/ready/` — confirms the configured database can answer a minimal query.

Start Django locally after PostgreSQL is healthy:

```powershell
.\venv\Scripts\python.exe backend\manage.py runserver
```

Inspect the database and pgvector version:

```powershell
docker compose -f docker-compose.yml -f docker-compose.dev.yml exec -T postgres psql -U knowledgevault -d knowledgevault -c "SELECT current_setting('server_version'), extversion FROM pg_extension WHERE extname = 'vector';"
```

No persistent Django migrations should be applied until the custom user model is introduced.

## API documentation

The API will live under `/api/v1/` and expose generated OpenAPI schema and interactive documentation. Endpoint examples will be added as the corresponding APIs are implemented.

## Security

Tenant isolation is release-blocking. Every organization-owned query—including vector retrieval and citation lookup—must be scoped to the authenticated user's authorized organization and knowledge base. Uploaded documents are untrusted data and must never override system instructions.

## Deployment

The target deployment uses immutable application images, Nginx, externally managed secrets, PostgreSQL backups, Redis, S3-compatible object storage, health checks, structured logs, and non-root containers where practical. Production deployment is deferred until Phase 13 and will not be automated before explicit configuration.

## Screenshots

Screenshots will be added after the relevant UI exists. No mock screenshot is presented as working product functionality.

## Known limitations

- The backend currently contains only the Django scaffold and health-check application.
- PostgreSQL/pgvector and its development container are implemented; Redis, Celery, the Django container, and frontend are not.
- Nine backend tests exist; broader domain, integration, security, and frontend suites remain pending.
- The repaired local virtual environment is usable but not portable and must not be committed.
- Production settings fail closed and include an initial secure baseline, but full production hardening remains Phase 13 work.
- Authentication, storage, streaming, and deployment details remain future architectural decisions.

## Roadmap

Development is divided into Phases 0 through 14. Phase 1 currently focuses on the backend, database, background-task, and container foundations.

## License and contributions

`LICENSE`, `CONTRIBUTING.md`, and `SECURITY.md` will be added during the project-foundation and hardening phases. Until a license is added, no open-source license is granted.
