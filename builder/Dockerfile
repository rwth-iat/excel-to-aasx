# PDF builder service (ADR 0009). Build from the repository root:
#   docker build -f builder/Dockerfile -t excel-to-aasx-builder .
FROM asciidoctor/docker-asciidoctor:1.108.1

RUN adduser -D -H -u 10001 builder
COPY builder/server.py /opt/builder/server.py
COPY src/excel_to_aasx/adapters/pdf/extensions/numbered_paragraphs.rb /opt/builder/numbered_paragraphs.rb

# PlantUML: no file or URL access from diagram sources (!include, !includeurl).
ENV PLANTUML_SECURITY_PROFILE=SANDBOX \
    HOME=/tmp \
    PYTHONDONTWRITEBYTECODE=1

USER builder
WORKDIR /tmp
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s CMD python3 -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/health', timeout=3)"
ENTRYPOINT []
CMD ["python3", "/opt/builder/server.py"]
