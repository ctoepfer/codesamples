import { LoadConfig, DiscoverDevices, Install } from './wailsjs/go/gui/App.js';

// ---- Persistent storage keys ----
const KEYS = {
  configPath: 'rbl:configPath',
  lastIP:     'rbl:lastIP',
};

// ---- In-memory state ----
let selectedIP  = null;
let appConfig   = null;

// ---- Screen helpers ----
function show(id) {
  document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
  document.getElementById(id).classList.add('active');
}

// ---- Config application ----
function applyConfig(cfg) {
  document.querySelectorAll('[id^="app-name"]').forEach(el => {
    el.textContent = cfg.appName || 'Roku Beta Loader';
  });

  const introEl = document.getElementById('devmode-intro');
  if (cfg.developerModeIntro) {
    introEl.textContent = cfg.developerModeIntro;
    introEl.style.display = '';
  } else {
    introEl.style.display = 'none';
  }

  const imgEl = document.getElementById('devmode-image');
  if (cfg.developerModeImage) {
    imgEl.src = cfg.developerModeImage;
    imgEl.style.display = '';
  } else {
    imgEl.style.display = 'none';
  }

  // Dev-mode reminder on discover screen (for returning users)
  const reminderIntro = document.getElementById('devmode-reminder-intro');
  const reminderImg   = document.getElementById('devmode-reminder-image');
  const reminderSection = document.getElementById('devmode-reminder');
  if (cfg.developerModeIntro || cfg.developerModeImage) {
    reminderSection.style.display = '';
    reminderIntro.textContent = cfg.developerModeIntro || '';
    reminderIntro.style.display = cfg.developerModeIntro ? '' : 'none';
    if (cfg.developerModeImage) {
      reminderImg.src = cfg.developerModeImage;
      reminderImg.style.display = '';
    } else {
      reminderImg.style.display = 'none';
    }
  } else {
    reminderSection.style.display = 'none';
  }

  // Manual IP help text
  const helpText = cfg.manualIpHelp || '';
  ['manual-ip-help', 'manual-ip-help-fallback'].forEach(id => {
    const el = document.getElementById(id);
    if (el) { el.textContent = helpText; el.style.display = helpText ? '' : 'none'; }
  });

  // Install button label
  const label = cfg.installButtonLabel || 'Install Beta';
  const btnInstall = document.getElementById('btn-install');
  if (btnInstall) btnInstall.textContent = label;
}

// Pre-fill the last-used IP into all manual-IP inputs
function prefillLastIP() {
  const last = localStorage.getItem(KEYS.lastIP);
  if (!last) return;
  ['input-ip', 'input-ip-fallback'].forEach(id => {
    const el = document.getElementById(id);
    if (el && !el.value) el.value = last;
  });
}

// ---- "Use different config" — clear storage and restart ----
function clearAndReset() {
  localStorage.removeItem(KEYS.configPath);
  localStorage.removeItem(KEYS.lastIP);
  appConfig   = null;
  selectedIP  = null;
  show('screen-config');
}

['btn-clear-from-devmode', 'btn-clear-from-discover',
 'btn-clear-from-install',  'btn-clear-from-success'].forEach(id => {
  document.getElementById(id)?.addEventListener('click', clearAndReset);
});

// ---- Screen: Config ----
document.getElementById('btn-open-config').addEventListener('click', async () => {
  const result = await LoadConfig('');
  if (!result.ok) {
    alert(result.error || 'Could not load config file.');
    return;
  }
  appConfig = result;
  if (result.path) localStorage.setItem(KEYS.configPath, result.path);
  applyConfig(result);
  show('screen-devmode');
});

// ---- Screen: Developer Mode ----
document.getElementById('btn-ready').addEventListener('click', () => {
  show('screen-discover');
  startDiscovery();
});

// ---- Screen: Discovery ----
async function startDiscovery() {
  const statusEl = document.getElementById('discover-status');
  const listEl   = document.getElementById('device-list');
  const errorEl  = document.getElementById('discover-error');

  statusEl.style.display = 'flex';
  statusEl.innerHTML = '<span class="spinner"></span> Looking for Roku devices&hellip;';
  listEl.style.display  = 'none';
  errorEl.style.display = 'none';
  selectedIP = null;

  let devices;
  try { devices = await DiscoverDevices(); }
  catch (_) { devices = []; }

  statusEl.style.display = 'none';

  if (!devices || devices.length === 0) {
    errorEl.style.display = '';
    prefillLastIP();
    return;
  }

  const devicesEl = document.getElementById('devices');
  devicesEl.innerHTML = '';
  devices.forEach(d => {
    const btn = document.createElement('button');
    btn.className = 'device-btn';
    btn.dataset.ip = d.ip;
    btn.innerHTML = `<div class="device-name">${escapeHtml(d.name || 'Roku')}</div>`
                  + `<div class="device-ip">${escapeHtml(d.ip)}</div>`;
    btn.addEventListener('click', () => selectDevice(d.ip, d.name || d.ip));
    devicesEl.appendChild(btn);
  });

  listEl.style.display = '';
  prefillLastIP();
}

function selectDevice(ip, label) {
  document.querySelectorAll('.device-btn').forEach(b => {
    b.classList.toggle('selected', b.dataset.ip === ip);
  });
  setTimeout(() => advanceToInstall(ip, label), 300);
}

// ---- advanceToInstall: FIX — always sets selectedIP ----
function advanceToInstall(ip, label) {
  selectedIP = ip;
  localStorage.setItem(KEYS.lastIP, ip);
  document.getElementById('selected-device-label').textContent = label + ' (' + ip + ')';
  document.getElementById('input-password').value = '';
  document.getElementById('install-status').style.display = 'none';
  show('screen-install');
}

document.getElementById('btn-use-manual-ip').addEventListener('click', () => {
  const ip = document.getElementById('input-ip').value.trim();
  if (!ip) { alert('Please enter an IP address.'); return; }
  advanceToInstall(ip, ip);
});
document.getElementById('btn-use-fallback-ip').addEventListener('click', () => {
  const ip = document.getElementById('input-ip-fallback').value.trim();
  if (!ip) { alert('Please enter an IP address.'); return; }
  advanceToInstall(ip, ip);
});
document.getElementById('btn-retry-discover').addEventListener('click', startDiscovery);

// ---- Screen: Install ----
document.getElementById('btn-toggle-password').addEventListener('click', () => {
  const input = document.getElementById('input-password');
  input.type = input.type === 'password' ? 'text' : 'password';
});

document.getElementById('btn-back-to-discover').addEventListener('click', () => {
  show('screen-discover');
});

document.getElementById('btn-install').addEventListener('click', async () => {
  if (!selectedIP) { alert('No Roku selected.'); return; }
  const password = document.getElementById('input-password').value;
  if (!password) { alert('Please enter the Roku developer password.'); return; }

  const btnInstall = document.getElementById('btn-install');
  const statusEl   = document.getElementById('install-status');

  btnInstall.disabled = true;
  statusEl.style.display = 'flex';

  const steps = [
    { msg: 'Downloading the beta…',       delay: 0 },
    { msg: 'Checking the download…',       delay: 4000 },
    { msg: 'Installing on your Roku…',     delay: 7000 },
  ];
  steps.forEach(({ msg, delay }) => {
    setTimeout(() => {
      if (btnInstall.disabled) {
        statusEl.innerHTML = `<span class="spinner"></span> ${msg}`;
      }
    }, delay);
  });

  let result;
  try { result = await Install(selectedIP, password); }
  catch (_) { result = { ok: false, error: 'Something went wrong. Please try again.' }; }

  btnInstall.disabled = false;
  statusEl.style.display = 'none';

  if (result.ok) {
    const versionEl = document.getElementById('success-version');
    versionEl.textContent = result.version ? 'Version ' + result.version + ' installed.' : '';
    const postEl = document.getElementById('post-install-msg');
    const postMsg = appConfig && appConfig.postInstallMessage;
    if (postMsg) { postEl.textContent = postMsg; postEl.style.display = ''; }
    else { postEl.style.display = 'none'; }
    show('screen-success');
  } else {
    document.getElementById('failure-msg').textContent = result.error || 'Something went wrong.';
    show('screen-failure');
  }
});

// ---- Screen: Success ----
document.getElementById('btn-install-another').addEventListener('click', () => {
  selectedIP = null;
  show('screen-discover');
  startDiscovery();
});

// ---- Screen: Failure ----
document.getElementById('btn-try-again').addEventListener('click', () => {
  show('screen-install');
});

// ---- Utility ----
function escapeHtml(str) {
  return str.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

// ---- Boot ----
(async () => {
  const storedPath = localStorage.getItem(KEYS.configPath);
  if (storedPath) {
    try {
      const cfg = await LoadConfig(storedPath);
      if (cfg.ok) {
        appConfig = cfg;
        // Don't re-store path on auto-load (it's already stored)
        applyConfig(cfg);
        // Returning user: skip devmode instructions, go straight to discovery
        show('screen-discover');
        startDiscovery();
        return;
      }
    } catch (_) {}
    // Stored path is stale (file moved/deleted) — clear it and show config screen
    localStorage.removeItem(KEYS.configPath);
  }
  show('screen-config');
})();
