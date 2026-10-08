FROM python:3.12-slim-bookworm@sha256:34386ef0cb081344d7ec1c103ba398e6e9f64e9ab3a1509accc92a4e24a07258

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.lock ./
COPY vendor/ /vendor/
RUN if [ -d /vendor/wheels ]; then \
      python -m pip install --no-cache-dir --no-index --find-links=/vendor/wheels --require-hashes -r requirements.lock; \
    else \
      python -m pip install --no-cache-dir --require-hashes -r requirements.lock; \
    fi \
    && useradd --create-home --uid 10001 app
COPY --chown=app:app . /app
RUN mkdir -p /app/.local && chown app:app /app/.local && chmod 700 /app/.local
USER app
EXPOSE 8000
CMD ["sh", "scripts/start_container.sh"]
