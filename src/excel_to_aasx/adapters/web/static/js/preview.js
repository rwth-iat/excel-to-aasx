import Asciidoctor from "/static/vendor/asciidoctor.js";

// HTML preview with asciidoctor.js (ADR 0006).
// The iframe is sandboxed without allow-scripts, so nothing in it runs, even raw HTML from an
// untrusted package. allow-same-origin lets this page replace the body in place: no reload,
// so the reader keeps their scroll position while typing.

const asciidoctor = Asciidoctor();
const LINE_ROLE = "src-line-";

const SHELL =
  '<!doctype html><html><head><meta charset="utf-8">' +
  '<link rel="stylesheet" href="/static/preview.css"></head><body></body></html>';

function toHtml(text, imagesdir) {
  const doc = asciidoctor.load(text, {
    safe: "secure",
    standalone: false,
    sourcemap: true,
    // env-pdf: show the same branches of ifdef/ifndef as the PDF build does.
    attributes: { imagesdir, showtitle: "", icons: "", "env-pdf": "", "env-preview": "" },
  });
  // Tag every block with its source line, so the preview can follow the editor.
  for (const block of doc.findBy()) {
    const line = block.getLineNumber();
    if (line) block.addRole(`${LINE_ROLE}${line}`);
  }
  return doc.convert();
}

export function renderPreview(frame, text, imagesdir) {
  const html = toHtml(text, imagesdir);
  return new Promise((resolve) => {
    const body = frame.contentDocument && frame.contentDocument.body;
    if (body && frame.dataset.ready === "1") {
      body.innerHTML = html;
      resolve();
      return;
    }
    frame.addEventListener("load", () => {
      frame.dataset.ready = "1";
      frame.contentDocument.body.innerHTML = html;
      resolve();
    }, { once: true });
    frame.srcdoc = SHELL;
  });
}

function anchors(frame) {
  const doc = frame.contentDocument;
  if (!doc || !doc.body) return [];
  const found = [];
  for (const element of doc.querySelectorAll(`[class*="${LINE_ROLE}"]`)) {
    const match = element.className.match(new RegExp(`${LINE_ROLE}(\\d+)`));
    if (match) found.push({ line: Number(match[1]), top: element.getBoundingClientRect().top });
  }
  const offset = doc.defaultView.scrollY;
  return found.map((a) => ({ line: a.line, top: a.top + offset })).sort((a, b) => a.line - b.line);
}

// Scroll the preview so that source `line` sits near the top, interpolating between blocks.
export function syncPreview(frame, line) {
  const marks = anchors(frame);
  if (marks.length === 0) return;
  let before = marks[0];
  let after = null;
  for (const mark of marks) {
    if (mark.line <= line) before = mark;
    else { after = mark; break; }
  }
  let top = before.top;
  if (after && after.line > before.line && line > before.line) {
    top += ((line - before.line) / (after.line - before.line)) * (after.top - before.top);
  }
  frame.contentWindow.scrollTo({ top: Math.max(0, top - 24) });
}
