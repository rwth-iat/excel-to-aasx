import { basicSetup, EditorView } from "/static/vendor/codemirror.js";
import * as api from "./api.js";
import { renderPreview, syncPreview } from "./preview.js";

const $ = (id) => document.getElementById(id);
let workspace = null;
let editor = null;
let pdfUrl = null;
let previewTimer = null;
let saveTimer = null;

function showError(message) {
  $("error").textContent = message;
  $("error").hidden = false;
}

function setStatus(text) {
  $("status").textContent = text;
}

function listIssues(issues) {
  const errors = issues.filter((i) => i.severity === "error").length;
  $("issues-summary").textContent =
    `${errors} error(s), ${issues.length - errors} warning(s) while preparing the document`;
  const list = $("issues-list");
  list.replaceChildren(...issues.map((issue) => {
    const item = document.createElement("li");
    item.className = issue.severity;
    item.textContent = `${issue.severity} ${issue.location}: ${issue.message}`;
    return item;
  }));
  $("issues").hidden = issues.length === 0;
}

const cursorLine = () => editor.state.doc.lineAt(editor.state.selection.main.head).number;

function follow(line) {
  if ($("sync").checked && !$("preview").hidden) syncPreview($("preview"), line);
}

function topLine() {
  const block = editor.lineBlockAtHeight(editor.scrollDOM.scrollTop);
  return editor.state.doc.lineAt(block.from).number;
}

function onEdit() {
  clearTimeout(previewTimer);
  previewTimer = setTimeout(async () => {
    await renderPreview($("preview"), text(), api.filesUrl(workspace));
    follow(cursorLine());
  }, 300);
  clearTimeout(saveTimer);
  saveTimer = setTimeout(() => api.saveDocument(workspace, text()).catch((e) => setStatus(e.message)), 1500);
}

const text = () => editor.state.doc.toString();

function openWorkspace(result) {
  workspace = result.id;
  $("start").hidden = true;
  $("workspace").hidden = false;
  $("actions").hidden = false;
  $("doc-name").textContent = result.document.name;
  $("download-aasx").href = api.packageUrl(workspace);
  $("download-zip").href = api.zipUrl(workspace);
  listIssues(result.issues);
  editor = new EditorView({
    doc: result.document.text,
    extensions: [
      basicSetup,
      EditorView.cspNonce.of(document.querySelector('meta[name="csp-nonce"]').content),
      EditorView.lineWrapping,
      EditorView.updateListener.of((u) => {
        if (u.docChanged) onEdit();
        else if (u.selectionSet) follow(cursorLine());
      }),
    ],
    parent: $("editor"),
  });
  editor.scrollDOM.addEventListener("scroll", () => follow(topLine()), { passive: true });
  renderPreview($("preview"), result.document.text, api.filesUrl(workspace));
}

async function handleFile(file) {
  if (!file) return;
  $("error").hidden = true;
  $("drop").classList.add("busy");
  $("drop").querySelector("span").textContent = `Preparing ${file.name} …`;
  try {
    openWorkspace(await api.upload(file));
  } catch (error) {
    showError(error.message);
    $("drop").querySelector("span").textContent = "Drop a .xlsx or .aasx file here, or click to choose one";
  } finally {
    $("drop").classList.remove("busy");
  }
}

function showTab(which) {
  const pdf = which === "pdf";
  $("preview").hidden = pdf;
  $("pdf").hidden = !pdf;
  $("tab-html").classList.toggle("active", !pdf);
  $("tab-pdf").classList.toggle("active", pdf);
}

async function buildPdf() {
  const button = $("build-pdf");
  button.disabled = true;
  setStatus("Building PDF … (about 10 s)");
  try {
    const { pdf, messages } = await api.buildPdf(workspace, text());
    if (pdfUrl) URL.revokeObjectURL(pdfUrl);
    pdfUrl = URL.createObjectURL(pdf);
    $("pdf").src = pdfUrl;
    $("tab-pdf").disabled = false;
    showTab("pdf");
    setStatus(messages.length ? `PDF built with ${messages.length} message(s)` : "PDF built");
  } catch (error) {
    setStatus(error.message);
  } finally {
    button.disabled = false;
  }
}

$("file").addEventListener("change", (e) => handleFile(e.target.files[0]));
$("drop").addEventListener("dragover", (e) => { e.preventDefault(); $("drop").classList.add("over"); });
$("drop").addEventListener("dragleave", () => $("drop").classList.remove("over"));
$("drop").addEventListener("drop", (e) => {
  e.preventDefault();
  $("drop").classList.remove("over");
  handleFile(e.dataTransfer.files[0]);
});
$("try-example").addEventListener("click", async () => {
  const button = $("try-example");
  button.disabled = true;
  try {
    const response = await fetch("/static/examples/demo-level-sensor.xlsx");
    if (!response.ok) throw new Error(`example not available (${response.status})`);
    await handleFile(new File([await response.blob()], "demo-level-sensor.xlsx"));
  } catch (error) {
    showError(error.message);
  } finally {
    button.disabled = false;
  }
});
$("build-pdf").addEventListener("click", buildPdf);

// Two clicks instead of a dialog: the session and unsaved edits are discarded.
let confirmTimer = null;
$("new-file").addEventListener("click", async () => {
  const button = $("new-file");
  if (!button.classList.contains("confirm")) {
    button.classList.add("confirm");
    button.textContent = "Click again to discard";
    confirmTimer = setTimeout(() => {
      button.classList.remove("confirm");
      button.textContent = "New file";
    }, 4000);
    return;
  }
  clearTimeout(confirmTimer);
  await api.closeWorkspace(workspace).catch(() => {});
  location.reload();
});
$("tab-html").addEventListener("click", () => showTab("html"));
$("tab-pdf").addEventListener("click", () => showTab("pdf"));
