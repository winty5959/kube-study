"use strict";

const PAGE_SIZE = 24;
const POLL_MS = 2000;
const MAX_BYTES = 10 * 1024 * 1024;
const $ = (id) => document.getElementById(id);

let page = 1;
let pollTimer = null;
let currentId = null;

// Show which api Pod / version answered, to see load balancing and rollouts happen.
function trackServer(res) {
  const by = res.headers.get("X-Served-By");
  const ver = res.headers.get("X-App-Version");
  if (by) $("served-by").textContent = by;
  if (ver) $("app-version").textContent = ver;
}

async function api(path, options = {}) {
  const res = await fetch(path, options);
  trackServer(res);
  if (!res.ok && res.status !== 204) {
    let detail = res.statusText;
    try { detail = (await res.json()).detail || detail; } catch { /* non-JSON error */ }
    throw new Error(`${res.status} ${detail}`);
  }
  return res.status === 204 ? null : res.json();
}

function el(tag, attrs = {}, ...children) {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === "class") node.className = v;
    else node.setAttribute(k, v);
  }
  node.append(...children);
  return node;
}

function statusBadge(status) {
  return el("span", { class: `status status-${status}` }, status);
}

function card(photo) {
  const thumb = el("div", { class: "thumb" });
  if (photo.thumb_small_url) {
    thumb.append(el("img", { src: photo.thumb_small_url, alt: photo.filename, loading: "lazy" }));
  } else {
    thumb.append(statusBadge(photo.status));
  }
  const info = el("div", { class: "info" },
    el("div", { class: "name", title: photo.filename }, photo.filename),
    statusBadge(photo.status),
    photo.processed_by ? el("div", { class: "meta", title: "processed_by" }, photo.processed_by) : "",
  );
  const li = el("li", { class: "card" }, thumb, info);
  li.addEventListener("click", () => openDetail(photo.id));
  return li;
}

async function loadGallery() {
  clearTimeout(pollTimer);
  try {
    const data = await api(`/api/photos?page=${page}&size=${PAGE_SIZE}`);
    const pages = Math.max(1, Math.ceil(data.total / PAGE_SIZE));
    if (page > pages) { page = pages; return loadGallery(); }
    $("grid").replaceChildren(...data.items.map(card));
    $("empty").hidden = data.total > 0;
    $("total").textContent = `총 ${data.total}장`;
    $("page-label").textContent = `${page} / ${pages}`;
    $("prev").disabled = page <= 1;
    $("next").disabled = page >= pages;
    // Keep polling while any photo on this page is still being processed
    if (data.items.some((p) => p.status === "PENDING" || p.status === "PROCESSING")) {
      pollTimer = setTimeout(loadGallery, POLL_MS);
    }
  } catch (e) {
    $("total").textContent = `목록을 불러오지 못했습니다: ${e.message}`;
    pollTimer = setTimeout(loadGallery, POLL_MS * 2);
  }
}

function logLine(text, isError = false) {
  const li = el("li", isError ? { class: "err" } : {}, text);
  $("upload-log").prepend(li);
}

$("upload-form").addEventListener("submit", async (ev) => {
  ev.preventDefault();
  const files = [...$("files").files];
  if (!files.length) return;
  const button = ev.submitter;
  button.disabled = true;
  for (const file of files) {
    if (file.size > MAX_BYTES) { logLine(`${file.name}: 10MB 초과`, true); continue; }
    const body = new FormData();
    body.append("file", file);
    try {
      const res = await api("/api/photos", { method: "POST", body });
      logLine(`${file.name}: ${res.status} (${res.id.slice(0, 8)})`);
    } catch (e) {
      logLine(`${file.name}: ${e.message}`, true);
    }
  }
  button.disabled = false;
  $("files").value = "";
  page = 1;
  loadGallery();
});

$("prev").addEventListener("click", () => { page -= 1; loadGallery(); });
$("next").addEventListener("click", () => { page += 1; loadGallery(); });

async function openDetail(id) {
  currentId = id;
  const p = await api(`/api/photos/${id}`);
  const img = $("detail-img");
  img.hidden = !p.thumb_medium_url;
  if (p.thumb_medium_url) { img.src = p.thumb_medium_url; img.alt = p.filename; }
  const rows = [
    ["파일명", p.filename],
    ["상태", p.status],
    ["크기", `${(p.size_bytes / 1024).toFixed(1)} KB`],
    ["처리 Pod", p.processed_by || "-"],
    ["재시도", String(p.retry_count)],
    ["업로드", new Date(p.created_at).toLocaleString()],
    ["처리 완료", p.processed_at ? new Date(p.processed_at).toLocaleString() : "-"],
  ];
  $("detail-meta").replaceChildren(...rows.flatMap(([k, v]) => [el("dt", {}, k), el("dd", {}, v)]));
  $("detail-download").href = p.original_url;
  $("detail").showModal();
}

$("detail-delete").addEventListener("click", async () => {
  if (!currentId || !confirm("이 사진을 삭제할까요?")) return;
  try {
    await api(`/api/photos/${currentId}`, { method: "DELETE" });
    $("detail").close();
    loadGallery();
  } catch (e) {
    alert(`삭제 실패: ${e.message}`);
  }
});

loadGallery();
