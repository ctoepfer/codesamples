import { LoadConfig, GetConfig, DiscoverDevices, Install } from './wailsjs/go/gui/App.js';

// ---- State ----
let selectedIP = null;
let appConfig = null;

// ---- Helpers ----
function show(id) {
  document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
  document.getElementById(id).classList.add('active');
}

function setStatus(id, html) {
  const el = document.getElementById(id);
  if (el) el.innerHTML = html;
}

// ---- Screen: Config ----
document.getElementById('btn-open-config').addEventListener('click', async () => {
  const result = await LoadConfig('');
  if (!result.ok) {
    alert(result.error || 'Could not load config file.');
    return;
  }
  appConfig = result;
  applyConfig(result);
  show('screen-devmode');
});

function applyConfig(cfg) {
  // App name headings
  document.querySelectorAll('[id^="app-name"]').forEach(el => { el.textContent = cfg.appName || 'Roku Beta Loader'; });

  // Developer mode intro
  const introEl = document.getElementById('devmode-intro');
  if (cfg.developerModeIntro) {
    introEl.textContent = cfg.developerModeIntro;
    introEl.style.display = '';
  } else {
    introEl.style.display = 'none';
  }

  // Developer mode image
  const imgEl = document.getElementById('devmode-image');
  if (cfg.developerModeImage) {
    imgEl.src = cfg.developerModeImage;
    imgEl.style.display = '';
  } else {
    imgEl.style.display = 'none';
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

// ---- Screen: Developer Mode ----
document.getElementById('btn-ready').addEventListener('click', () => {
  show('screen-discover');
  startDiscovery();
});

// ---- Screen: Discovery ----
async function startDiscovery() {
  const statusEl = document.getElementById('discover-status');
  const listEl = document.getElementById('device-list');
  const errorEl = document.getElementById('discover-error');

  statusEl.style.display = 'flex';
  statusEl.innerHTML = '<span class="spinner"></span> Looking for Roku devices&hellip;';
  listEl.style.display = 'none';
  errorEl.style.display = 'none';
  selectedIP = null;

  let devices;
  try {
    devices = await DiscoverDevices();
  } catch (e) {
    devices = [];
  }

  statusEl.style.display = 'none';

  if (!devices || devices.length === 0) {
    errorEl.style.display = '';
    return;
  }

  // Render device buttons
  const devicesEl = document.getElementById('devices');
  devicesEl.innerHTML = '';
  devices.forEach(d => {
    const btn = document.createElement('button');
    btn.className = 'device-btn';
    btn.dataset.ip = d.ip;
    btn.innerHTML = `<div class="device-name">${escapeHtml(d.name || 'Roku')}</div><div class="device-ip">${escapeHtml(d.ip)}</div>`;
    btn.addEventListener('click', () => selectDevice(d.ip, d.name || d.ip));
    devicesEl.appendChild(btn);
  });

  listEl.style.display = '';
}

function selectDevice(ip, label) {
  selectedIP = ip;
  document.querySelectorAll('.device-btn').forEach(b => {
    b.classList.toggle('selected', b.dataset.ip === ip);
  });
  // Brief delay then advance
  setTimeout(() => advanceToInstall(ip, label), 300);
}

function advanceToInstall(ip, label) {
  document.getElementById('selected-device-label').textContent = label + ' (' + ip + ')';
  document.getElementById('input-password').value = '';
  document.getElementById('install-status').style.display = 'none';
  show('screen-install');
}

// Manual IP from discovery screen
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
  const ip = selectedIP;
  const password = document.getElementById('input-password').value;

  if (!ip) { alert('No Roku selected.'); return; }
  if (!password) { alert('Please enter the Roku developer password.'); return; }

  const btnInstall = document.getElementById('btn-install');
  const statusEl = document.getElementById('install-status');

  btnInstall.disabled = true;
  statusEl.style.display = 'flex';

  const steps = [
    { msg: 'Downloading the beta…', delay: 0 },
    { msg: 'Checking the download…', delay: 4000 },
    { msg: 'Installing on your Roku…', delay: 7000 },
  ];
  steps.forEach(({ msg, delay }) => {
    setTimeout(() => {
      if (btnInstall.disabled) {
        statusEl.innerHTML = `<span class="spinner"></span> ${msg}`;
      }
    }, delay);
  });

  let result;
  try {
    result = await Install(ip, password);
  } catch (e) {
    result = { ok: false, error: 'Something went wrong. Please try again.' };
  }

  btnInstall.disabled = false;
  statusEl.style.display = 'none';

  if (result.ok) {
    const versionEl = document.getElementById('success-version');
    versionEl.textContent = result.version ? 'Version ' + result.version + ' installed.' : '';

    const postMsg = appConfig && appConfig.postInstallMessage;
    const postEl = document.getElementById('post-install-msg');
    if (postMsg) {
      postEl.textContent = postMsg;
      postEl.style.display = '';
    } else {
      postEl.style.display = 'none';
    }
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
  return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

// ---- Boot: auto-load config if previously loaded ----
(async () => {
  try {
    const cfg = await GetConfig();
    if (cfg.ok) {
      appConfig = cfg;
      applyConfig(cfg);
      show('screen-devmode');
      return;
    }
  } catch (_) {}
  show('screen-config');
})();
