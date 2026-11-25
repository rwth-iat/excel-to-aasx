# Deployment

The web app is public and anonymous (ADR 0005). It runs as three containers (ADR 0009, 0011): `app`, `builder` (PDFs) and `diagrams` (PlantUML for the live preview, 1 CPU). None has Docker access.

## Run

```bash
docker compose up -d --build
# APP_PORT=8766 docker compose up -d --build   # if 8000 is taken
docker compose ps        # all three "healthy"
docker compose logs -f
```

The app listens on `127.0.0.1:${APP_PORT:-8000}` only. Do not publish that port directly: put a reverse proxy in front of it.

## Reverse proxy (required for public use)

The proxy terminates HTTPS and limits requests per client. The app itself has global limits (body size, 4 parallel uploads, 2 parallel PDF builds, 2 parallel diagram renders, 200 sessions) and per-session limits for diagrams (one at a time, 2 s apart, 60 s of render time per 10 minutes). It has no per-client limits: sessions are cheap, so without the proxy one client could still take all slots.

Example for nginx:

```nginx
limit_req_zone $binary_remote_addr zone=uploads:10m rate=6r/m;
limit_req_zone $binary_remote_addr zone=pdf:10m rate=10r/m;
limit_req_zone $binary_remote_addr zone=diagram:10m rate=20r/m;
limit_req_zone $binary_remote_addr zone=general:10m rate=10r/s;

server {
    listen 443 ssl http2;
    server_name aasx.example.org;
    # ssl_certificate ...; ssl_certificate_key ...;

    client_max_body_size 55m;          # app limit is 50 MB plus form overhead
    proxy_read_timeout 300s;           # PDF builds can take a while

    location = /api/workspaces {
        limit_req zone=uploads burst=3 nodelay;
        proxy_pass http://127.0.0.1:8000;
    }
    location ~ ^/api/workspaces/[0-9a-f]+/pdf$ {
        limit_req zone=pdf burst=5 nodelay;
        proxy_pass http://127.0.0.1:8000;
    }
    location ~ ^/api/workspaces/[0-9a-f]+/diagram$ {
        limit_req zone=diagram burst=5 nodelay;
        proxy_pass http://127.0.0.1:8000;
    }
    location / {
        limit_req zone=general burst=40 nodelay;
        proxy_pass http://127.0.0.1:8000;
    }
}
```

Add `Strict-Transport-Security` at the proxy once HTTPS works. The app already sends CSP, `X-Frame-Options`, `nosniff` and `no-store`.

## Configuration

| Variable | Service | Default | Meaning |
|---|---|---|---|
| `APP_PORT` | compose | `8000` | Host port (bound to 127.0.0.1). |
| `EXCEL_TO_AASX_BUILDER_URL` | app | set in compose | Builder base URL; unset = a local container per build (needs Docker). |
| `EXCEL_TO_AASX_DIAGRAM_URL` | app | set in compose | Diagram service base URL; unset = the builder URL, or a local container per diagram. |
| `EXCEL_TO_AASX_WORKSPACES` | app | `/data/workspaces` | Session folders (volume `workspaces`). |
| `BUILDER_PARALLEL` | builder, diagrams | `2` | PDF builds at the same time; `0` in the diagram service. |
| `BUILDER_PARALLEL_DIAGRAMS` | builder, diagrams | `2` | Diagram renders at the same time; `0` in the builder. Per-render limits (10 s CPU, 5 MB SVG, 15 s) are constants in `builder/server.py`. |
| `BUILDER_TIMEOUT_SECONDS` | builder | `240` | Per build; the process group is killed after it. |
| `BUILDER_MAX_ZIP_BYTES` / `BUILDER_MAX_UNPACKED_BYTES` | builder | 60 MB / 200 MB | Request limits. |

Limits inside the app (upload size, session count, idle timeout of 2 h) are constants in `src/excel_to_aasx/main.py` and `adapters/web/api.py`.

## Sizing

- Memory: app 1 GB, builder 2 GB, diagrams 768 MB (compose limits). A large document build takes up to ~1 GB; a diagram render up to ~300 MB.
- CPU: builder 2, diagrams 1 (compose limits).
- Disk: up to 200 sessions × (upload ≤ 50 MB + package + document files). Sessions are deleted after 2 h idle or on "New file".

## Updating

- The asciidoctor image is pinned in two places: `builder/Dockerfile` and `ASCIIDOCTOR_IMAGE` in `src/excel_to_aasx/main.py`. Change both together, and update the PlantUML jar path that comes with the image (`PLANTUML_JAR` in `src/excel_to_aasx/adapters/pdf/diagram.py` and `builder/server.py`; a test keeps the two equal, and the Docker test fails if the jar moved). Afterwards run the tests with Docker available (they build the demo PDF and render a diagram) and, if you have them, compare a PDF with the local reference files (ADR 0010).
- Python dependencies: `uv lock --upgrade`, then rebuild.
- Frontend libraries: `tools/vendor.sh` (needs npm), then rebuild.
