'use strict';
const leads = ['I', 'II', 'III', 'aVR', 'aVL', 'aVF', 'V1', 'V2', 'V3', 'V4', 'V5', 'V6'];
const tileOrder = ['I', 'V1', 'II', 'V2', 'III', 'V3', 'aVR', 'V4', 'aVL', 'V5', 'aVF', 'V6'];
let sample = 1, selectedLead = 'II';
const annotations = new Map();
let activeBox = 0, drag = null;
const clamp = (value, min, max) => Math.max(min, Math.min(max, value));
function boxes(lead = selectedLead) {
  const key = `${sample}:${lead}`;
  if (!annotations.has(key)) {
    const period = [0.86, 0.73, 1.02][sample - 1];
    const spans = [];
    for (let beat = 0; beat < 10; beat += period) {
      const start = beat + 0.35;
      if (start + 0.32 <= 10) spans.push({start, end: start + 0.32, top: 0, bottom: 1});
      if ((lead === 'II' || lead === 'aVR') && start + 0.68 <= 10) {
        spans.push({start: start + 0.35, end: start + 0.68, top: 0, bottom: 1, rhythm: true});
      }
    }
    annotations.set(key, spans);
  }
  return annotations.get(key);
}
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
  let content = `<defs><pattern id="${prefix}-small" width="8" height="8" patternUnits="userSpaceOnUse"><path d="M8 0H0V8" fill="none" stroke="#edaaaa" stroke-width="0.7"/></pattern><pattern id="${prefix}-big" width="40" height="40" patternUnits="userSpaceOnUse"><rect width="40" height="40" fill="url(#${prefix}-small)"/><path d="M40 0H0V40" fill="none" stroke="#d96a6a" stroke-width="1"/></pattern></defs><rect width="${width}" height="${height}" fill="url(#${prefix}-big)"/>`;
  content += `<path d="${waveform(lead, width, height * 0.6, height * 0.39)}" fill="none" stroke="#39434c" stroke-width="${detail ? 1.8 : 1.3}" stroke-linejoin="round"/>`;
  if (byId('annotations').checked) {
    boxes(lead).forEach((box, index) => {
      const x = 20 + (width - 40) * box.start / 10, right = 20 + (width - 40) * box.end / 10;
      const plotHeight = height - (detail ? 25 : 0), y = box.top * plotHeight, bottom = box.bottom * plotHeight;
      const color = box.rhythm ? '#e000df' : '#ef4444';
      content += `<rect class="annotation-box" data-box="${index}" data-handle="move" x="${x}" y="${y}" width="${right-x}" height="${bottom-y}" fill="${color}" fill-opacity="0.24" stroke="${color}" stroke-width="${detail ? 2 : 1}"/>`;
      if (detail) {
        [['w',x,(y+bottom)/2],['e',right,(y+bottom)/2]].forEach(([handle,hx,hy]) => {
          content += `<rect class="box-handle ${handle}" data-box="${index}" data-handle="${handle}" x="${hx-6}" y="${hy-6}" width="12" height="12" rx="2" fill="#fff" stroke="${color}" stroke-width="2"/>`;
        });
      }
    });
  }
  if (detail) {
    for (let t = 0; t <= 10; t++) content += `<text x="${20 + (width - 40) * t / 10}" y="${height - 5}" text-anchor="middle" fill="#65756b" font-size="12">${t}s</text>`;
  }
  return content;
}
function renderDetail() {
  byId('detail-title').textContent = `Lead ${selectedLead}`;
  byId('detail').setAttribute('aria-label', `Synthetic lead ${selectedLead} waveform, 0 to 10 seconds`);
  byId('detail').innerHTML = svgContent(selectedLead, 1000, 200, true);
  byId('box-status').textContent = 'Drag inside a colored box to move it horizontally. Drag its left or right handle to change its width.';
}
function render() {
  const grid = byId('lead-grid');
  if (!grid.children.length) {
    tileOrder.forEach(lead => {
      const button = document.createElement('button');
      button.className = 'lead-tile'; button.dataset.lead = lead;
      button.setAttribute('aria-label', `Inspect lead ${lead}`);
      button.addEventListener('click', () => { selectedLead = lead; activeBox = 0; render(); });
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
byId('previous').addEventListener('click', () => { sample = Math.max(1, sample - 1); activeBox = 0; render(); });
byId('next').addEventListener('click', () => { sample = Math.min(3, sample + 1); activeBox = 0; render(); });
byId('annotations').addEventListener('change', render);
render();

function pointerPosition(event) {
  const svg = byId('detail'), point = svg.createSVGPoint();
  point.x = event.clientX; point.y = event.clientY;
  return point.matrixTransform(svg.getScreenCTM().inverse());
}
byId('detail').addEventListener('pointerdown', event => {
  const target = event.target.closest('[data-box]');
  if (!target || event.button !== 0) return;
  event.preventDefault();
  activeBox = Number(target.dataset.box);
  drag = {id: event.pointerId, handle: target.dataset.handle, origin: pointerPosition(event), box: {...boxes()[activeBox]}};
  byId('detail').setPointerCapture(event.pointerId);
  renderDetail();
});
byId('detail').addEventListener('pointermove', event => {
  if (!drag || event.pointerId !== drag.id) return;
  const pos = pointerPosition(event), original = drag.box, box = boxes()[activeBox];
  const dt = (pos.x - drag.origin.x) / 96;
  if (drag.handle === 'move') {
    box.start = clamp(original.start + dt, 0, 10 - (original.end - original.start));
    box.end = box.start + original.end - original.start;
  } else {
    if (drag.handle.includes('w')) box.start = clamp(original.start + dt, 0, box.end - 0.1);
    if (drag.handle.includes('e')) box.end = clamp(original.end + dt, box.start + 0.1, 10);
  }
  render();
});
function endDrag(event) {
  if (!drag || event.pointerId !== drag.id) return;
  drag = null;
  if (byId('detail').hasPointerCapture(event.pointerId)) byId('detail').releasePointerCapture(event.pointerId);
}
byId('detail').addEventListener('pointerup', endDrag);
byId('detail').addEventListener('pointercancel', endDrag);
byId('detail').addEventListener('lostpointercapture', () => { drag = null; });
