import Asciidoctor from "/static/vendor/asciidoctor.js";

// HTML preview with asciidoctor.js (ADR 0006).
// The iframe is sandboxed without allow-scripts, so nothing in it runs, even raw HTML from an
// untrusted package. allow-same-origin lets this page replace the body in place: no reload,
// so the reader keeps their scroll position while typing.

const asciidoctor = Asciidoctor();

const SHELL =
  '<!doctype html><html><head><meta charset="utf-8">' +
  '<link rel="stylesheet" href="/static/preview.css"></head><body></body></html>';

function toHtml(text, imagesdir) {
  return asciidoctor.convert(text, {
    safe: "secure",
    standalone: false,
    // env-pdf: show the same branches of ifdef/ifndef as the PDF build does.
    attributes: { imagesdir, showtitle: "", icons: "", "env-pdf": "", "env-preview": "" },
  });
}

export function renderPreview(frame, text, imagesdir) {
  const html = toHtml(text, imagesdir);
  const body = frame.contentDocument && frame.contentDocument.body;
  if (body && frame.dataset.ready === "1") {
    body.innerHTML = html;
    return;
  }
  frame.addEventListener("load", () => {
    frame.dataset.ready = "1";
    frame.contentDocument.body.innerHTML = html;
  }, { once: true });
  frame.srcdoc = SHELL;
}
