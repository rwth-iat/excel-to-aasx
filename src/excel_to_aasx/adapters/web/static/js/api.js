// All server calls. Errors carry the server's message.

async function failure(response) {
  let message = `${response.status} ${response.statusText}`;
  try {
    const body = await response.json();
    if (body && body.detail) message = body.detail;
  } catch (_) { /* not JSON */ }
  const error = new Error(message);
  error.status = response.status;
  return error;
}

const base = (id) => `/api/workspaces/${id}`;

export async function upload(file) {
  const form = new FormData();
  form.append("file", file);
  const response = await fetch("/api/workspaces", { method: "POST", body: form });
  if (!response.ok) throw await failure(response);
  return response.json();
}

export async function saveDocument(id, text) {
  const response = await fetch(`${base(id)}/document`, { method: "PUT", body: text });
  if (!response.ok) throw await failure(response);
}

export async function buildPdf(id, text) {
  const response = await fetch(`${base(id)}/pdf`, { method: "POST", body: text });
  if (!response.ok) throw await failure(response);
  const messages = JSON.parse(response.headers.get("X-Build-Messages") || "[]");
  return { pdf: await response.blob(), messages };
}

export async function closeWorkspace(id) {
  await fetch(base(id), { method: "DELETE" });
}

export const packageUrl = (id) => `${base(id)}/package.aasx`;
export const zipUrl = (id) => `${base(id)}/document.zip`;
export const filesUrl = (id) => `${base(id)}/files`;
