const $ = (id) => document.getElementById(id);

function showError(err) {
  const box = $("errorBox");
  box.textContent = typeof err === "string" ? err : String(err);
  box.classList.remove("hidden");
}

function clearError() {
  $("errorBox").classList.add("hidden");
  $("errorBox").textContent = "";
}

async function requestStatus() {
  const res = await fetch("/cgi-bin/api.cgi?action=status", { cache: "no-store" });
  if (!res.ok) throw new Error(`status request failed: ${res.status}`);
  return await res.json();
}

function fillForm(data) {
  const cfg = data.config || {};
  const status = data.status || {};
  const interfaces = data.interfaces || [];

  $("enabled").checked = !!cfg.enabled;
  $("rx").value = cfg.rx_threshold ?? 0;
  $("tx").value = cfg.tx_threshold ?? 1024;
  $("poll").value = cfg.poll_interval ?? 30;
  $("cooldown").value = cfg.cooldown ?? 300;
  $("bootDelay").value = cfg.boot_delay ?? 120;
  $("restartDelay").value = cfg.restart_delay ?? 5;
  $("bind").value = cfg.http_bind ?? "0.0.0.0";
  $("httpPort").value = cfg.http_port ?? 18088;

  const iface = $("iface");
  const current = cfg.wg_interface || "Wireguard0";
  iface.innerHTML = "";
  for (const name of interfaces) {
    const opt = document.createElement("option");
    opt.value = name;
    opt.textContent = name;
    if (name === current) opt.selected = true;
    iface.appendChild(opt);
  }

  $("rxValue").textContent = status.rxbytes ?? "-";
  $("txValue").textContent = status.txbytes ?? "-";
  $("handshake").textContent = status.last_handshake ?? "-";
  $("ifaceState").textContent = status.interface_status || "-";
  $("serviceBadge").textContent = cfg.enabled ? "enabled" : "disabled";
  $("lastUpdate").textContent = `Updated ${new Date().toLocaleTimeString()}`;

  const chips = $("ifaceList");
  chips.innerHTML = "";
  for (const name of interfaces) {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "chip" + (name === current ? " active" : "");
    btn.textContent = name;
    btn.addEventListener("click", () => {
      $("iface").value = name;
      [...chips.children].forEach((node) => node.classList.remove("active"));
      btn.classList.add("active");
    });
    chips.appendChild(btn);
  }
}

async function refresh() {
  clearError();
  try {
    const data = await requestStatus();
    fillForm(data);
  } catch (err) {
    showError(err);
  }
}

async function postAction(action, extra = {}) {
  clearError();
  const body = new URLSearchParams();
  body.set("action", action);
  for (const [key, value] of Object.entries(extra)) {
    body.set(key, value);
  }
  const res = await fetch("/cgi-bin/api.cgi", {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body,
  });
  if (!res.ok) throw new Error(`action ${action} failed: ${res.status}`);
  const data = await res.json();
  fillForm(data);
}

async function saveConfig() {
  clearError();
  const body = new URLSearchParams();
  body.set("action", "save");
  body.set("ENABLED", $("enabled").checked ? "1" : "");
  body.set("WG_INTERFACE", $("iface").value);
  body.set("RX_THRESHOLD", $("rx").value || "0");
  body.set("TX_THRESHOLD", $("tx").value || "1024");
  body.set("POLL_INTERVAL", $("poll").value || "30");
  body.set("COOLDOWN", $("cooldown").value || "300");
  body.set("BOOT_DELAY", $("bootDelay").value || "120");
  body.set("RESTART_DELAY", $("restartDelay").value || "5");
  body.set("HTTP_BIND", $("bind").value || "0.0.0.0");
  body.set("HTTP_PORT", $("httpPort").value || "18088");

  const res = await fetch("/cgi-bin/api.cgi", {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body,
  });
  if (!res.ok) throw new Error(`save failed: ${res.status}`);
  const data = await res.json();
  fillForm(data);
}

window.addEventListener("DOMContentLoaded", () => {
  $("saveBtn").addEventListener("click", (ev) => {
    ev.preventDefault();
    saveConfig().catch(showError);
  });
  $("toggleBtn").addEventListener("click", () => {
    postAction("toggle").catch(showError);
  });
  $("bounceBtn").addEventListener("click", () => {
    postAction("bounce").catch(showError);
  });
  $("reloadBtn").addEventListener("click", refresh);
  $("cfgForm").addEventListener("submit", (ev) => {
    ev.preventDefault();
    saveConfig().catch(showError);
  });
  refresh();
  setInterval(refresh, 10000);
});
