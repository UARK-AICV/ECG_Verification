'use strict';
const leads = ['I', 'II', 'III', 'aVR', 'aVL', 'aVF', 'V1', 'V2', 'V3', 'V4', 'V5', 'V6'];
const tileOrder = ['I', 'V1', 'II', 'V2', 'III', 'V3', 'aVR', 'V4', 'aVL', 'V5', 'aVF', 'V6'];
let sample = 1, selectedLead = 'II', measuring = false, points = [];
const byId = id => document.getElementById(id);
const gaussian = (x, center, width) => Math.exp(-((x - center) ** 2) / (2 * width ** 2));
function signal(t, lead) {
  const index = leads.indexOf(lead), period = [0.86, 0.73, 1.02][sample - 1];
  const phase = (t + 0.23) % period;
  const amplitude = [0.65, 1, 0.6, -0.7, 0.45, 0.85, -0.45, 0.65, 0.9, 1.1, 0.85, 0.7][index];
  return amplitude * (0.12 * gaussian(phase, period * 0.18, 0.028) - 0.16 * gaussian(phase, period * 0.36, 0.012) + gaussian(phase, period * 0.4, 0.013) - 0.23 * gaussian(phase, period * 0.44, 0.018) + 0.24 * gaussian(phase, period * 0.68, 0.05)) + 0.025 * Math.sin(t * 3 + index);
}
function waveform(lead, width, baseline, amplitude) {
  let d = '';
  for (let i = 0; i <= 1500; i++) {
    const x = 20 + (width - 40) * i / 1500;
    const y = baseline - signal(10 * i / 1500, lead) * amplitude;
    d += `${i ? 'L' : 'M'}${x.toFixed(2)},${y.toFixed(2)} `;
  }
  return d;
}
function svgContent(lead, width, height, detail = false) {
  const prefix = `${detail ? 'detail' : 'tile'}-${lead}`;
  let content = `<defs><pattern id="${prefix}-small" width="8" height="8" patternUnits="userSpaceOnUse"><path d="M8 0H0V8" fill="none" stroke="#f5d5d5" stroke-width="0.6"/></pattern><pattern id="${prefix}-big" width="40" height="40" patternUnits="userSpaceOnUse"><rect width="40" height="40" fill="url(#${prefix}-small)"/><path d="M40 0H0V40" fill="none" stroke="#df9b9b" stroke-width="0.7"/></pattern></defs><rect width="${width}" height="${height}" fill="url(#${prefix}-big)"/>`;
  if (byId('annotations').checked) {
    [2.4, 5.8].forEach(t => { content += `<rect x="${20 + (width - 40) * t / 10}" y="0" width="${(width - 40) * 0.28 / 10}" height="${height - (detail ? 25 : 0)}" fill="#99bd76" opacity="0.3"/>`; });
  }
  content += `<path d="${waveform(lead, width, height * 0.6, height * 0.39)}" fill="none" stroke="#254b40" stroke-width="${detail ? 1.8 : 1.3}" stroke-linejoin="round"/>`;
  if (detail) {
    for (let t = 0; t <= 10; t++) content += `<text x="${20 + (width - 40) * t / 10}" y="${height - 5}" text-anchor="middle" fill="#65756b" font-size="12">${t}s</text>`;
    points.forEach(t => { const x = 20 + (width - 40) * t / 10; content += `<line x1="${x}" x2="${x}" y1="8" y2="${height - 25}" stroke="#245749" stroke-width="2" stroke-dasharray="5 4"/><circle cx="${x}" cy="10" r="4" fill="#245749"/>`; });
    if (points.length === 2) {
      const first = 20 + (width - 40) * Math.min(...points) / 10, last = 20 + (width - 40) * Math.max(...points) / 10;
      content += `<line x1="${first}" x2="${last}" y1="26" y2="26" stroke="#245749" stroke-width="2"/><text x="${(first + last) / 2}" y="20" fill="#153e35" font-size="13" text-anchor="middle">Δt = ${Math.abs(points[1] - points[0]).toFixed(3)}s</text>`;
    }
  }
  return content;
}
function renderDetail() {
  byId('detail-title').textContent = `Lead ${selectedLead}`;
  byId('detail').setAttribute('aria-label', `Synthetic lead ${selectedLead} waveform, 0 to 10 seconds`);
  byId('detail').innerHTML = svgContent(selectedLead, 1000, 200, true);
  byId('measurement').textContent = points.length === 2
    ? `t₁ = ${points[0].toFixed(3)}s · t₂ = ${points[1].toFixed(3)}s · Δt = ${Math.abs(points[1] - points[0]).toFixed(3)}s`
    : points.length === 1 ? `First point: ${points[0].toFixed(3)}s. Choose a second point.`
    : measuring ? 'Choose two points on the waveform, or enter times below.' : 'Select “Measure interval”, then choose two points on the waveform.';
}
function render() {
  const grid = byId('lead-grid');
  if (!grid.children.length) {
    tileOrder.forEach(lead => {
      const button = document.createElement('button');
      button.className = 'lead-tile'; button.dataset.lead = lead;
      button.setAttribute('aria-label', `Inspect lead ${lead}`);
      button.addEventListener('click', () => { selectedLead = lead; points = []; render(); });
      grid.appendChild(button);
    });
  }
  Array.from(grid.children).forEach(button => {
    const lead = button.dataset.lead;
    button.setAttribute('aria-pressed', String(lead === selectedLead));
    button.innerHTML = `<span class="lead-label">${lead}</span><svg viewBox="0 0 480 90" aria-hidden="true" preserveAspectRatio="none">${svgContent(lead, 480, 90)}</svg>`;
  });
  byId('sample-number').textContent = sample;
  byId('previous').disabled = sample === 1; byId('next').disabled = sample === 3;
  renderDetail();
}
byId('previous').addEventListener('click', () => { sample = Math.max(1, sample - 1); points = []; render(); });
byId('next').addEventListener('click', () => { sample = Math.min(3, sample + 1); points = []; render(); });
byId('annotations').addEventListener('change', render);
byId('measure').addEventListener('click', () => {
  measuring = !measuring; points = [];
  byId('measure').setAttribute('aria-pressed', String(measuring));
  byId('accessible-measure').hidden = !measuring;
  document.body.classList.toggle('measuring', measuring); renderDetail();
});
byId('detail').addEventListener('click', event => {
  if (!measuring) return;
  const point = byId('detail').createSVGPoint(); point.x = event.clientX; point.y = event.clientY;
  const mapped = point.matrixTransform(byId('detail').getScreenCTM().inverse());
  const t = Math.max(0, Math.min(10, (mapped.x - 20) / 960 * 10));
  if (points.length === 2) points = [];
  points.push(t); renderDetail();
});
byId('reset').addEventListener('click', () => { points = []; renderDetail(); });
byId('calculate').addEventListener('click', () => {
  const values = [byId('point-one'), byId('point-two')];
  if (!values.every(input => input.reportValidity())) return;
  if (values.some(input => input.value === '')) { byId('measurement').textContent = 'Enter both times to calculate the interval.'; return; }
  points = values.map(input => Number(input.value)); renderDetail();
});
const setup = {
  mac: '<h3>Open the macOS app</h3><ol><li>Obtain the packaged macOS ZIP from the project maintainer or a published release.</li><li>Extract it into a writable folder.</li><li>Keep <code>sample/</code> beside <code>ECGVerification.app</code>, then open the app.</li></ol>',
  windows: '<h3>Open the Windows app</h3><ol><li>Obtain the packaged Windows ZIP from the project maintainer or a published release.</li><li>Extract the entire folder before running it.</li><li>Open <code>ECGVerification.exe</code>. Keep <code>_internal/</code> and <code>sample/</code> beside it.</li></ol>',
  source: '<h3>Run from the project folder</h3><p>Install Python 3.12 and keep the supplied sample folder in place. In an activated virtual environment:</p><pre><code>python -m pip install -r requirements.txt\npython main.py</code></pre>'
};
const tabs = Array.from(document.querySelectorAll('[role="tab"]'));
function selectPlatform(tab) {
  tabs.forEach(item => { const active = item === tab; item.setAttribute('aria-selected', String(active)); item.tabIndex = active ? 0 : -1; });
  byId('setup-panel').innerHTML = setup[tab.dataset.platform];
  byId('setup-panel').setAttribute('aria-labelledby', tab.id);
}
tabs.forEach((tab, index) => {
  tab.addEventListener('click', () => selectPlatform(tab));
  tab.addEventListener('keydown', event => {
    let target;
    if (event.key === 'ArrowRight') target = tabs[(index + 1) % tabs.length];
    if (event.key === 'ArrowLeft') target = tabs[(index + tabs.length - 1) % tabs.length];
    if (event.key === 'Home') target = tabs[0];
    if (event.key === 'End') target = tabs[tabs.length - 1];
    if (target) { event.preventDefault(); selectPlatform(target); target.focus(); }
  });
});
// GitHub project Pages provide the owner and repository through the URL.
if (location.hostname.endsWith('.github.io')) {
  const owner = location.hostname.slice(0, -10);
  const repo = location.pathname.split('/').filter(Boolean)[0] || `${owner}.github.io`;
  const link = byId('repository-link');
  link.href = `https://github.com/${encodeURIComponent(owner)}/${encodeURIComponent(repo)}`;
  link.hidden = false;
}
selectPlatform(tabs[0]); render();
