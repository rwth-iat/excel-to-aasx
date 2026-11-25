# Web app (ADR 0005-0007, 0009). PDF builds go to the builder service; no Docker access here.
FROM python:3.13-slim

COPY --from=ghcr.io/astral-sh/uv:0.13.4 /uv /bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PROJECT_ENVIRONMENT=/opt/venv

WORKDIR /app
COPY pyproject.toml uv.lock README.md ./
COPY src ./src
RUN uv sync --frozen --no-dev --no-editable && rm -rf /root/.cache

RUN useradd --uid 10000 --no-create-home --shell /usr/sbin/nologin app \
    && mkdir -p /data/workspaces && chown app /data/workspaces
USER app
ENV EXCEL_TO_AASX_WORKSPACES=/data/workspaces PATH=/opt/venv/bin:$PATH
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/', timeout=3)"
CMD ["excel-to-aasx", "serve", "--host", "0.0.0.0", "--port", "8000"]
