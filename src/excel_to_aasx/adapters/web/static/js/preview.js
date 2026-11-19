import Asciidoctor from "/static/vendor/asciidoctor.js";

// HTML preview with asciidoctor.js (ADR 0006). Rendered into a sandboxed iframe without
// scripts, because AsciiDoc can carry raw HTML from an untrusted package.

const asciidoctor = Asciidoctor();

export function renderPreview(frame, text, imagesdir) {
  const html = asciidoctor.convert(text, {
    safe: "secure",
    standalone: false,
    attributes: { imagesdir, showtitle: "", icons: "", "env-preview": "" },
  });
  frame.srcdoc =
    '<!doctype html><html><head><meta charset="utf-8">' +
    '<link rel="stylesheet" href="/static/preview.css"></head>' +
    `<body>${html}</body></html>`;
}
