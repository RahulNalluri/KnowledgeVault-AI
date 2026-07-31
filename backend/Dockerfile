FROM python:3.13.5-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

RUN addgroup --system knowledgevault \
    && adduser --system --ingroup knowledgevault knowledgevault

COPY pyproject.toml ./
COPY apps ./apps
COPY config ./config
COPY manage.py ./

RUN python -m pip install --no-cache-dir . \
    && chown -R knowledgevault:knowledgevault /app

USER knowledgevault

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
