// Project IYAL Admin Portal Logic (/admin)

let currentAdminUser = null;
let adminToken = localStorage.getItem("iyal_admin_jwt") || null;

document.addEventListener("DOMContentLoaded", async () => {
  await checkAuthConfig();
  await tryRestoreSession();
});

function showAdminAlert(msg, type = "info") {
  const el = document.getElementById("admin-alert");
  el.className = `alert alert-${type}`;
  el.textContent = msg;
  el.style.display = "block";
  setTimeout(() => {
    el.style.display = "none";
  }, 6000);
}

function authHeaders() {
  const h = { "Content-Type": "application/json" };
  if (adminToken) {
    h["Authorization"] = `Bearer ${adminToken}`;
  }
  return h;
}

function switchAuthSubtab(panelId, btn) {
  document.querySelectorAll(".auth-subpanel").forEach((p) => (p.style.display = "none"));
  document.querySelectorAll("#login-view .tab-btn").forEach((b) => b.classList.remove("active"));
  document.getElementById(panelId).style.display = "block";
  btn.classList.add("active");
}

function switchAdminTab(panelId, btn) {
  document.querySelectorAll("#dashboard-view .tab-panel").forEach((p) => p.classList.remove("active"));
  document.querySelectorAll("#dashboard-view .tab-btn").forEach((b) => b.classList.remove("active"));
  document.getElementById(panelId).classList.add("active");
  btn.classList.add("active");

  if (panelId === "admin-feedback-tab") loadAdminFeedback();
  if (panelId === "admin-models-tab") loadAdminModels();
  if (panelId === "admin-users-tab" && currentAdminUser?.role === "superadmin") loadAdminUsers();
  if (panelId === "admin-corpus-tab") loadAdminCorpus();
  if (panelId === "admin-observability-tab") loadObservability();
}

async function checkAuthConfig() {
  try {
    const res = await fetch("/api/v1/auth/config");
    const cfg = await res.json();
    const statusBox = document.getElementById("google-oauth-status");
    if (cfg.google_oauth_enabled && cfg.google_client_id && window.google) {
      statusBox.textContent = "Google OAuth 2.0 is active. Click the button above to sign in with your invited Gmail.";
      window.google.accounts.id.initialize({
        client_id: cfg.google_client_id,
        callback: handleGoogleCredentialResponse,
      });
      window.google.accounts.id.renderButton(
        document.getElementById("google-signin-button-container"),
        { theme: "outline", size: "large" }
      );
    } else {
      statusBox.innerHTML =
        "<strong>Hybrid Gmail Auth Mode:</strong> <code>GOOGLE_CLIENT_ID</code> is not set in <code>.env</code> yet (common on raw university IP servers). Invited Gmail admins can sign in immediately via the <strong>Password Login</strong> or <strong>Accept Gmail Invite</strong> tabs, or set <code>GOOGLE_CLIENT_ID</code> in <code>.env</code> to enable 1-click Google OAuth.";
    }
  } catch (e) {
    console.warn("Could not check auth config:", e);
  }
}

async function handleGoogleCredentialResponse(response) {
  try {
    const res = await fetch("/api/v1/auth/google", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ id_token: response.credential }),
    });
    const data = await res.json();
    if (!res.ok) {
      showAdminAlert(data.detail || "Google Sign-In failed.", "danger");
      return;
    }
    onLoginSuccess(data);
  } catch (e) {
    showAdminAlert(`Google login error: ${e.message}`, "danger");
  }
}

async function tryRestoreSession() {
  try {
    const res = await fetch("/api/v1/auth/me", { headers: authHeaders() });
    if (res.ok) {
      const user = await res.json();
      currentAdminUser = user;
      enterDashboard();
    } else {
      localStorage.removeItem("iyal_admin_jwt");
      adminToken = null;
    }
  } catch (e) {
    // Stay on login view
  }
}

async function submitPasswordLogin() {
  const identifier = document.getElementById("login-identifier").value.trim();
  const password = document.getElementById("login-password").value;
  try {
    const res = await fetch("/api/v1/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ identifier, password }),
    });
    const data = await res.json();
    if (!res.ok) {
      showAdminAlert(data.detail || "Login failed.", "danger");
      return;
    }
    onLoginSuccess(data);
  } catch (err) {
    showAdminAlert(`Login error: ${err.message}`, "danger");
  }
}

async function submitAcceptInvite() {
  const email = document.getElementById("invite-email").value.trim();
  const invite_token = document.getElementById("invite-token").value.trim();
  const new_password = document.getElementById("invite-new-password").value;

  try {
    const res = await fetch("/api/v1/auth/accept-invite", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, invite_token, new_password }),
    });
    const data = await res.json();
    if (!res.ok) {
      showAdminAlert(data.detail || "Invitation activation failed.", "danger");
      return;
    }
    showAdminAlert("Account activated! Welcome to the Admin Portal.", "success");
    onLoginSuccess(data);
  } catch (err) {
    showAdminAlert(`Error: ${err.message}`, "danger");
  }
}

function onLoginSuccess(data) {
  adminToken = data.access_token;
  localStorage.setItem("iyal_admin_jwt", adminToken);
  currentAdminUser = data.user;
  enterDashboard();
}

function enterDashboard() {
  document.getElementById("login-view").style.display = "none";
  document.getElementById("dashboard-view").style.display = "block";

  const pill = document.getElementById("admin-user-pill");
  pill.textContent = `${currentAdminUser.email} (${currentAdminUser.role.toUpperCase()})`;
  pill.style.display = "inline-flex";
  document.getElementById("logout-btn").style.display = "inline-flex";

  // Enforce Superadmin vs Admin UI visibility
  if (currentAdminUser.role === "superadmin") {
    document.getElementById("non-superadmin-notice").style.display = "none";
    document.getElementById("superadmin-users-content").style.display = "block";
  } else {
    document.getElementById("non-superadmin-notice").style.display = "block";
    document.getElementById("superadmin-users-content").style.display = "none";
  }

  loadAdminFeedback();
  loadAdminModels();
}

async function logoutAdmin() {
  await fetch("/api/v1/auth/logout", { method: "POST" });
  localStorage.removeItem("iyal_admin_jwt");
  adminToken = null;
  currentAdminUser = null;
  document.getElementById("dashboard-view").style.display = "none";
  document.getElementById("login-view").style.display = "block";
  document.getElementById("admin-user-pill").style.display = "none";
  document.getElementById("logout-btn").style.display = "none";
}

// =====================================================================
// 1. Feedback Management
// =====================================================================
async function loadAdminFeedback() {
  const statusFilter = document.getElementById("fb-filter-status").value;
  const res = await fetch(`/api/v1/admin/feedback?status_filter=${encodeURIComponent(statusFilter)}`, {
    headers: authHeaders(),
  });
  if (!res.ok) return;
  const data = await res.json();

  document.getElementById("fb-stat-total").textContent = data.summary.total;
  document.getElementById("fb-stat-new").textContent = data.summary.new;
  document.getElementById("fb-stat-resolved").textContent = data.summary.resolved;

  const tbody = document.getElementById("admin-feedback-tbody");
  if (!data.items.length) {
    tbody.innerHTML = `<tr><td colspan="6" style="text-align:center; color:var(--text-muted);">No feedback entries found.</td></tr>`;
    return;
  }

  tbody.innerHTML = data.items
    .map(
      (item) => `
      <tr>
        <td>#${item.id}</td>
        <td style="font-size:0.8rem; color:var(--text-muted);">${new Date(item.created_at).toLocaleString()}</td>
        <td>
          <span class="badge badge-en_tamil">${esc(item.category)}</span>
          ${item.rating ? `<div style="margin-top:0.2rem;">${"⭐".repeat(item.rating)}</div>` : ""}
        </td>
        <td style="max-width:420px;">
          ${item.input_text ? `<div style="font-size:0.8rem; color:var(--text-muted);"><strong>Input:</strong> ${esc(item.input_text)}</div>` : ""}
          <div style="margin-top:0.25rem;"><strong>Feedback:</strong> ${esc(item.feedback)}</div>
          <details style="margin-top:0.3rem; font-size:0.78rem;">
            <summary style="cursor:pointer; color:var(--primary);">Inspect Output JSON</summary>
            <pre style="background:var(--bg-subtle); padding:0.5rem; border-radius:6px; overflow-x:auto; margin-top:0.25rem;">${esc(JSON.stringify(item.output, null, 2))}</pre>
          </details>
        </td>
        <td>
          <span class="badge ${item.status === "resolved" ? "badge-raw_tamil" : item.status === "reviewed" ? "badge-en_tamil" : "badge-Legacy"}">
            ${esc(item.status)}
          </span>
        </td>
        <td>
          <div style="display:flex; gap:0.35rem; flex-wrap:wrap;">
            <button class="btn btn-secondary btn-sm" onclick="updateFeedbackStatus(${item.id}, 'reviewed')">Mark Reviewed</button>
            <button class="btn btn-success btn-sm" onclick="updateFeedbackStatus(${item.id}, 'resolved')">Resolve</button>
            <button class="btn btn-danger btn-sm" onclick="deleteFeedback(${item.id})">Delete</button>
          </div>
        </td>
      </tr>
    `
    )
    .join("");
}

async function updateFeedbackStatus(id, status) {
  const res = await fetch(`/api/v1/admin/feedback/${id}`, {
    method: "PATCH",
    headers: authHeaders(),
    body: JSON.stringify({ status }),
  });
  if (res.ok) {
    loadAdminFeedback();
  }
}

async function deleteFeedback(id) {
  const res = await fetch(`/api/v1/admin/feedback/${id}`, {
    method: "DELETE",
    headers: authHeaders(),
  });
  if (res.ok) {
    loadAdminFeedback();
  }
}

// =====================================================================
// 2. Dual Model Management
// =====================================================================
function toggleCustomModelFields(prefix) {
  const mode = document.getElementById(`${prefix}-mode`).value;
  document.getElementById(`${prefix}-custom-fields`).style.display = mode === "custom" ? "block" : "none";
}

async function loadAdminModels() {
  const res = await fetch("/api/v1/admin/models", { headers: authHeaders() });
  if (!res.ok) return;
  const data = await res.json();

  renderModelCard("clf", data.classifier);
  renderModelCard("std", data.standardizer);
}

function renderModelCard(prefix, info) {
  if (!info) return;
  document.getElementById(`${prefix}-status-badge`).textContent = `${info.status} (${info.mode})`;
  document.getElementById(`${prefix}-mode`).value = info.mode || "default";
  document.getElementById(`${prefix}-custom-url`).value = info.custom_url || "";
  toggleCustomModelFields(prefix);

  document.getElementById(`${prefix}-meta`).innerHTML = `
    <div><strong>Active Source:</strong> <code>${esc(info.active_source)}</code></div>
    <div><strong>Default Repo:</strong> <code>${esc(info.default_model_name)}</code> | <strong>Device:</strong> <code>${esc(info.device)}</code></div>
    <div><strong>Total Inferences:</strong> ${info.total_calls} | <strong>Avg Latency:</strong> ${info.avg_latency_ms} ms</div>
    ${info.updated_by ? `<div><strong>Last Updated By:</strong> ${esc(info.updated_by)}</div>` : ""}
    ${info.last_error ? `<div style="color:var(--danger);"><strong>Last Error:</strong> ${esc(info.last_error)}</div>` : ""}
  `;
}

async function saveModelConfig(modelKey, prefix) {
  const mode = document.getElementById(`${prefix}-mode`).value;
  const custom_url = document.getElementById(`${prefix}-custom-url`).value.trim();
  const api_key = document.getElementById(`${prefix}-api-key`).value.trim();

  if (mode === "custom" && !custom_url) {
    showAdminAlert("Please enter a custom model URL or HuggingFace repo when selecting Custom mode.", "warning");
    return;
  }

  showAdminAlert(`Updating ${modelKey} configuration...`, "info");
  const res = await fetch(`/api/v1/admin/models/${modelKey}`, {
    method: "PUT",
    headers: authHeaders(),
    body: JSON.stringify({
      mode,
      custom_url: mode === "custom" ? custom_url : null,
      api_key: api_key || null,
    }),
  });
  const data = await res.json();
  if (!res.ok) {
    showAdminAlert(data.detail || "Failed to update model configuration.", "danger");
    return;
  }
  showAdminAlert(`Model '${modelKey}' updated to '${mode}' mode!`, "success");
  await loadAdminModels();
}

async function resetModelToDefault(modelKey) {
  const prefix = modelKey === "classifier" ? "clf" : "std";
  document.getElementById(`${prefix}-mode`).value = "default";
  toggleCustomModelFields(prefix);
  await saveModelConfig(modelKey, prefix);
}

async function runModelTest(modelKey, inputId, outputId) {
  const sample_input = document.getElementById(inputId).value.trim();
  const outEl = document.getElementById(outputId);
  outEl.textContent = "Running inference...";
  const res = await fetch(`/api/v1/admin/models/${modelKey}/test`, {
    method: "POST",
    headers: authHeaders(),
    body: JSON.stringify({ sample_input }),
  });
  const data = await res.json();
  if (res.ok) {
    outEl.innerHTML = `Result: <strong>${esc(data.sample_output)}</strong> (${data.info.last_latency_ms} ms)`;
    loadAdminModels();
  } else {
    outEl.textContent = `Error: ${data.detail}`;
  }
}

// =====================================================================
// 3. Superadmin User Management (Gmail Invitations & RBAC)
// =====================================================================
async function loadAdminUsers() {
  const res = await fetch("/api/v1/admin/users", { headers: authHeaders() });
  if (!res.ok) return;
  const data = await res.json();
  const tbody = document.getElementById("admin-users-tbody");

  tbody.innerHTML = (data.users || [])
    .map(
      (u) => `
      <tr>
        <td>
          <strong>${esc(u.email)}</strong>
          <div style="font-size:0.78rem; color:var(--text-muted);">@${esc(u.username)}</div>
          ${
            u.invite_token
              ? `<div style="font-size:0.75rem; color:var(--warning);">Invite Token: <code>${esc(u.invite_token)}</code></div>`
              : ""
          }
        </td>
        <td>
          <span class="badge ${u.role === "superadmin" ? "badge-Romanized" : "badge-en_tamil"}">${esc(u.role)}</span>
        </td>
        <td>
          <span class="badge ${u.is_active ? "badge-raw_tamil" : "badge-Legacy"}">${u.is_active ? "Active" : "Disabled"}</span>
        </td>
        <td>
          ${
            u.id === currentAdminUser.id
              ? `<span style="font-size:0.8rem; color:var(--text-muted);">Current Session</span>`
              : `<div style="display:flex; gap:0.35rem; flex-wrap:wrap;">
                   <button class="btn btn-secondary btn-sm" onclick="toggleAdminActive(${u.id}, ${!u.is_active})">
                     ${u.is_active ? "Deactivate" : "Activate"}
                   </button>
                   <button class="btn btn-danger btn-sm" onclick="deleteAdminUser(${u.id})">Delete</button>
                 </div>`
          }
        </td>
      </tr>
    `
    )
    .join("");
}

async function inviteAdminByGmail() {
  const email = document.getElementById("new-admin-email").value.trim();
  const username = document.getElementById("new-admin-username").value.trim();
  const role = document.getElementById("new-admin-role").value;
  const temporary_password = document.getElementById("new-admin-password").value.trim();

  const res = await fetch("/api/v1/admin/users/invite", {
    method: "POST",
    headers: authHeaders(),
    body: JSON.stringify({
      email,
      username: username || null,
      role,
      temporary_password: temporary_password || null,
    }),
  });
  const data = await res.json();
  if (!res.ok) {
    showAdminAlert(data.detail || "Failed to invite admin.", "danger");
    return;
  }

  const box = document.getElementById("invite-result-box");
  box.style.display = "block";
  box.innerHTML = `
    <strong>✅ Invited ${esc(data.user.email)} (${esc(data.user.role)})!</strong><br/>
    • <strong>Option 1 (Google OAuth):</strong> They can click "Sign in with Google" using <code>${esc(data.user.email)}</code>.<br/>
    • <strong>Option 2 (Invite Token):</strong> Email: <code>${esc(data.user.email)}</code> | Invite Token: <code>${esc(data.user.invite_token)}</code><br/>
    • <strong>Option 3 (Temporary Password):</strong> <code>${esc(data.user.temporary_password)}</code>
  `;

  document.getElementById("new-admin-email").value = "";
  document.getElementById("new-admin-username").value = "";
  document.getElementById("new-admin-password").value = "";
  loadAdminUsers();
}

async function toggleAdminActive(userId, newState) {
  await fetch(`/api/v1/admin/users/${userId}`, {
    method: "PATCH",
    headers: authHeaders(),
    body: JSON.stringify({ is_active: newState }),
  });
  loadAdminUsers();
}

async function deleteAdminUser(userId) {
  await fetch(`/api/v1/admin/users/${userId}`, {
    method: "DELETE",
    headers: authHeaders(),
  });
  loadAdminUsers();
}

// =====================================================================
// 4. Protected English Corpus Manager
// =====================================================================
async function loadAdminCorpus() {
  const res = await fetch("/api/v1/protected-words");
  if (!res.ok) return;
  const data = await res.json();
  const tbody = document.getElementById("admin-corpus-tbody");
  if (!data.words.length) {
    tbody.innerHTML = `<tr><td colspan="5" style="text-align:center; color:var(--text-muted);">No global protected words stored yet.</td></tr>`;
    return;
  }
  tbody.innerHTML = data.words
    .map(
      (w) => `
      <tr>
        <td>#${w.id}</td>
        <td><strong>${esc(w.word)}</strong></td>
        <td>${esc(w.added_by)}</td>
        <td>${w.created_at ? new Date(w.created_at).toLocaleString() : "-"}</td>
        <td>
          <button class="btn btn-danger btn-sm" onclick="adminDeleteProtectedWord(${w.id})">Remove</button>
        </td>
      </tr>
    `
    )
    .join("");
}

async function adminAddProtectedWord() {
  const inp = document.getElementById("admin-new-protected-word");
  const word = inp.value.trim();
  if (!word) return;
  const res = await fetch("/api/v1/protected-words", {
    method: "POST",
    headers: authHeaders(),
    body: JSON.stringify({ word, skip_translation: true }),
  });
  if (res.ok) {
    inp.value = "";
    loadAdminCorpus();
  } else {
    const err = await res.json();
    showAdminAlert(err.detail || "Could not add word", "warning");
  }
}

async function adminDeleteProtectedWord(id) {
  await fetch(`/api/v1/admin/protected-words/${id}`, {
    method: "DELETE",
    headers: authHeaders(),
  });
  loadAdminCorpus();
}

// =====================================================================
// 5. Observability, Security & Live Logs
// =====================================================================
async function loadObservability() {
  const level = document.getElementById("obs-log-level").value;
  const res = await fetch(`/api/v1/admin/observability?log_level=${encodeURIComponent(level)}`, {
    headers: authHeaders(),
  });
  if (!res.ok) return;
  const data = await res.json();

  document.getElementById("obs-uptime").textContent = `${data.system.uptime_seconds}s`;
  document.getElementById("obs-memory").textContent = `${data.system.process_memory_mb} MB`;
  document.getElementById("obs-ratelimited").textContent =
    data.security.total_rate_limited + data.security.total_blocked_requests;
  document.getElementById("obs-bruteforce").textContent = data.security.total_brute_force_blocks;

  // Render Security Bans & Lockouts
  const bansEl = document.getElementById("security-bans-container");
  const bans = data.security.active_ip_bans || [];
  const lockouts = data.security.active_login_lockouts || [];

  bansEl.innerHTML = `
    <div style="margin-bottom:0.6rem;">
      <strong>Tracked Client IPs:</strong> ${data.security.tracked_ips} |
      <strong>Tier Limits:</strong> General=${data.security.limits.general_per_min}/min,
      Inference=${data.security.limits.inference_per_min}/min,
      Feedback=${data.security.limits.feedback_per_min}/min
    </div>
    <div style="margin-bottom:0.5rem;">
      <strong>Active Auto-Banned IPs (${bans.length}):</strong>
      ${
        bans.length
          ? bans
              .map(
                (b) => `
              <div style="display:flex; justify-content:space-between; align-items:center; padding:0.3rem 0;">
                <code>${esc(b.ip)} (${b.seconds_remaining}s remaining)</code>
                <button class="btn btn-secondary btn-sm" onclick="unbanIp('${esc(b.ip)}')">Unban IP</button>
              </div>`
              )
              .join("")
          : `<span style="color:var(--success);">None</span>`
      }
    </div>
    <div>
      <strong>Active Login Brute-Force Lockouts (${lockouts.length}):</strong>
      ${
        lockouts.length
          ? lockouts.map((l) => `<div><code>${esc(l.target)}</code> (${l.failures} failures, ${l.seconds_remaining}s left)</div>`).join("")
          : `<span style="color:var(--success);">None</span>`
      }
    </div>
  `;

  // Audit Logs
  const auditTbody = document.getElementById("audit-logs-tbody");
  auditTbody.innerHTML = (data.audit_logs || [])
    .map(
      (a) => `
      <tr>
        <td style="font-size:0.76rem; white-space:nowrap;">${new Date(a.timestamp).toLocaleTimeString()}</td>
        <td><span class="badge ${a.level === "SECURITY" || a.level === "WARNING" ? "badge-Legacy" : "badge-en"}">${esc(a.level)}</span></td>
        <td><code>${esc(a.event_type)}</code></td>
        <td style="font-size:0.8rem;"><strong>${esc(a.actor)}:</strong> ${esc(a.details)}</td>
      </tr>
    `
    )
    .join("");

  // Application Log Ring Buffer
  const term = document.getElementById("app-log-terminal");
  term.innerHTML = (data.app_logs || [])
    .map(
      (l) => `
      <div class="log-line">
        <span style="color:#94a3b8;">[${esc(l.timestamp)}]</span>
        <span style="color:${l.level === "ERROR" ? "#f87171" : l.level === "WARNING" ? "#fbbf24" : "#38bdf8"}; font-weight:700;">
          ${esc(l.level)}
        </span>
        <span style="color:#a78bfa;">${esc(l.logger)}:</span>
        <span>${esc(l.message)}</span>
      </div>
    `
    )
    .join("");
}

async function unbanIp(ip) {
  await fetch("/api/v1/admin/security/unban-ip", {
    method: "POST",
    headers: authHeaders(),
    body: JSON.stringify({ ip }),
  });
  loadObservability();
}

function esc(str) {
  return String(str ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

