// MedLens Core Application Logic

let currentPatient = null;
let currentRecord = null;
let trendChartInstance = null;
let selectedFile = null;

document.addEventListener('DOMContentLoaded', () => {
  lucide.createIcons();
  setupDropZone();
  // Automatically check if demo patient exists or load default dashboard
  fetchPatients().then(patients => {
    if (patients.length === 0) {
      loadDemoMode();
    } else {
      selectPatient(patients[0].id);
    }
  });
});

// ----------------------------
// Navigation Handler
// ----------------------------
function navigateTo(pageId) {
  document.querySelectorAll('.page-view').forEach(el => el.classList.add('hidden'));
  const targetPage = document.getElementById(`page-${pageId}`);
  if (targetPage) {
    targetPage.classList.remove('hidden');
  }

  // Active state styling for nav buttons
  document.querySelectorAll('.nav-btn').forEach(btn => {
    btn.classList.remove('bg-slate-800', 'text-white', 'text-teal-400');
  });

  if (pageId === 'dashboard') {
    renderDashboard();
  } else if (pageId === 'record') {
    renderPatientRecord();
  } else if (pageId === 'conflicts') {
    renderConflicts();
  } else if (pageId === 'timeline') {
    renderTimeline();
  } else if (pageId === 'comparison') {
    renderComparison();
  }
}

// ----------------------------
// Toast Notifications
// ----------------------------
function showToast(title, message, type = 'info') {
  const banner = document.getElementById('toast-banner');
  const iconBox = document.getElementById('toast-icon');
  const titleEl = document.getElementById('toast-title');
  const msgEl = document.getElementById('toast-message');

  titleEl.textContent = title;
  msgEl.textContent = message;

  if (type === 'success') {
    iconBox.className = 'p-1 rounded-lg bg-emerald-500/20 text-emerald-400';
    iconBox.innerHTML = '<i data-lucide="check-circle" class="h-5 w-5"></i>';
  } else if (type === 'error') {
    iconBox.className = 'p-1 rounded-lg bg-red-500/20 text-red-400';
    iconBox.innerHTML = '<i data-lucide="alert-circle" class="h-5 w-5"></i>';
  } else {
    iconBox.className = 'p-1 rounded-lg bg-teal-500/20 text-teal-400';
    iconBox.innerHTML = '<i data-lucide="info" class="h-5 w-5"></i>';
  }

  lucide.createIcons();
  banner.classList.remove('hidden');
  setTimeout(() => closeToast(), 4000);
}

function closeToast() {
  document.getElementById('toast-banner').classList.add('hidden');
}

// ----------------------------
// API Service Calls
// ----------------------------
async function fetchPatients() {
  try {
    const res = await fetch('/api/patients');
    return await res.json();
  } catch (err) {
    showToast('Error', 'Failed to connect to MedLens API server', 'error');
    return [];
  }
}

async function selectPatient(patientId) {
  try {
    const res = await fetch(`/api/patients/${patientId}/record`);
    if (!res.ok) throw new Error('Patient record not found');
    currentRecord = await res.json();
    currentPatient = currentRecord.patient;
    
    // Update active navbar badges
    const unresolvedCount = currentRecord.conflicts.filter(c => c.status === 'Unresolved').length;
    const badge = document.getElementById('nav-conflict-badge');
    if (unresolvedCount > 0) {
      badge.textContent = unresolvedCount;
      badge.classList.remove('hidden');
    } else {
      badge.classList.add('hidden');
    }

    renderPatientRecord();
    renderDashboard();
  } catch (err) {
    console.error(err);
  }
}

async function loadDemoMode() {
  showToast('Initializing Demo', 'Loading synthetic multi-report clinical dataset...', 'info');
  try {
    const res = await fetch('/api/demo/seed', { method: 'POST' });
    const data = await res.json();
    await selectPatient(data.patient_id);
    navigateTo('record');
    showToast('Demo Ready', 'Loaded synthetic patient Jane Doe with 5 reports & active conflicts!', 'success');
  } catch (err) {
    showToast('Demo Error', 'Could not seed demo data', 'error');
  }
}

// ----------------------------
// Dashboard Renderer
// ----------------------------
async function renderDashboard() {
  const patients = await fetchPatients();
  document.getElementById('stat-patients').textContent = patients.length;
  
  if (currentRecord) {
    document.getElementById('stat-documents').textContent = currentRecord.documents.length;
    document.getElementById('stat-labs').textContent = currentRecord.lab_results.length;
    const unresolved = currentRecord.conflicts.filter(c => c.status === 'Unresolved');
    document.getElementById('stat-conflicts').textContent = unresolved.length;
    
    document.getElementById('dash-active-name').textContent = currentPatient.display_name;
    document.getElementById('dash-active-meta').textContent = `ID: ${currentPatient.patient_id_code} | Age: ${currentPatient.age || 'N/A'} | Sex: ${currentPatient.sex || 'N/A'}`;
    
    if (currentRecord.summary) {
      document.getElementById('dash-summary-text').textContent = currentRecord.summary.text_summary;
    }
  }

  // Render patient directory list
  const listEl = document.getElementById('dashboard-patient-list');
  listEl.innerHTML = patients.map(p => `
    <div onclick="selectPatient(${p.id}); navigateTo('record');" class="p-3 rounded-xl glass-card hover:border-teal-500/50 cursor-pointer transition flex items-center justify-between">
      <div>
        <h4 class="text-xs font-bold text-white">${p.display_name}</h4>
        <p class="text-[11px] text-slate-400 font-mono">${p.patient_id_code} • Age ${p.age || 'N/A'}</p>
      </div>
      <i data-lucide="chevron-right" class="h-4 w-4 text-slate-500"></i>
    </div>
  `).join('');
  
  lucide.createIcons();
}

// ----------------------------
// Patient Record Renderer (Centerpiece)
// ----------------------------
function renderPatientRecord() {
  if (!currentRecord) return;
  const p = currentRecord.patient;

  document.getElementById('rec-name').textContent = p.display_name;
  document.getElementById('rec-id-badge').textContent = p.patient_id_code;
  document.getElementById('rec-demographics').textContent = `Age: ${p.age || 'N/A'} yrs | Sex: ${p.sex || 'N/A'} | History: ${p.medical_history || 'Standard review'}`;

  // Intake Cards
  renderTagList('rec-symptoms', p.symptoms);
  renderTagList('rec-conditions', p.conditions);
  renderTagList('rec-allergies', p.allergies);
  renderTagList('rec-medications', p.medications, true);

  // AI Summary Panel
  if (currentRecord.summary) {
    document.getElementById('rec-summary-body').textContent = currentRecord.summary.text_summary;
    document.getElementById('rec-summary-disclaimer').textContent = currentRecord.summary.disclaimer;
  } else {
    document.getElementById('rec-summary-body').textContent = 'Upload a document or create intake to generate AI summary.';
  }

  // Lab Results Table
  filterLabResults();
}

function renderTagList(containerId, items, isMedication = false) {
  const container = document.getElementById(containerId);
  if (!items || items.length === 0) {
    container.innerHTML = '<span class="text-slate-500 italic">None documented</span>';
    return;
  }
  container.innerHTML = items.map(item => {
    const label = isMedication ? `${item.name} (${item.dose || 'dose N/A'})` : (item.name || item);
    return `<span class="px-2 py-0.5 rounded bg-slate-800 border border-slate-700 text-slate-200">${label}</span>`;
  }).join(' ');
}

// ----------------------------
// Filter & Render Lab Results
// ----------------------------
function filterLabResults() {
  if (!currentRecord) return;
  const searchTerm = document.getElementById('lab-search').value.toLowerCase();
  const filterStatus = document.getElementById('lab-filter-status').value;

  const tbody = document.getElementById('lab-table-body');
  const filtered = currentRecord.lab_results.filter(lab => {
    const matchesSearch = lab.test_name.toLowerCase().includes(searchTerm) || (lab.test_date && lab.test_date.includes(searchTerm));
    const matchesStatus = (filterStatus === 'ALL') || (lab.status === filterStatus);
    return matchesSearch && matchesStatus;
  });

  if (filtered.length === 0) {
    tbody.innerHTML = `<tr><td colspan="9" class="py-8 text-center text-slate-500">No lab results match current filter.</td></tr>`;
    return;
  }

  tbody.innerHTML = filtered.map(lab => {
    let statusBadgeClass = 'bg-slate-800 text-slate-400 border-slate-700';
    if (lab.status === 'LOW' || lab.status === 'HIGH') {
      statusBadgeClass = 'bg-red-950/60 text-red-400 border-red-800/80 font-bold';
    } else if (lab.status === 'NORMAL') {
      statusBadgeClass = 'bg-emerald-950/60 text-emerald-400 border-emerald-800/80 font-bold';
    } else if (lab.status === 'UNKNOWN') {
      statusBadgeClass = 'bg-amber-950/60 text-amber-300 border-amber-800/80 font-semibold';
    }

    let verBadge = `<span class="px-2 py-0.5 rounded text-[10px] bg-slate-800 text-slate-400 border border-slate-700">AI Extracted</span>`;
    if (lab.verification_status === 'User Verified') {
      verBadge = `<span class="px-2 py-0.5 rounded text-[10px] bg-emerald-950 text-emerald-300 border border-emerald-800 flex items-center gap-1"><i data-lucide="check" class="h-3 w-3"></i> Verified</span>`;
    } else if (lab.verification_status === 'User Edited') {
      verBadge = `<span class="px-2 py-0.5 rounded text-[10px] bg-cyan-950 text-cyan-300 border border-cyan-800 flex items-center gap-1"><i data-lucide="edit-3" class="h-3 w-3"></i> User Edited</span>`;
    }

    const rangeDisplay = (lab.reference_range && lab.reference_range !== 'Not provided in source')
      ? `<span class="font-mono text-teal-300">${lab.reference_range}</span>`
      : `<span class="text-amber-400 italic">Not provided in source</span>`;

    return `
      <tr class="hover:bg-slate-900/80 transition">
        <td class="py-3 px-4 font-semibold text-white">${lab.test_name}</td>
        <td class="py-3 px-4 font-bold text-slate-100">${lab.value}</td>
        <td class="py-3 px-4 text-slate-400 font-mono">${lab.unit || '-'}</td>
        <td class="py-3 px-4">${rangeDisplay}</td>
        <td class="py-3 px-4"><span class="px-2.5 py-0.5 rounded-full text-[11px] border ${statusBadgeClass}">${lab.status}</span></td>
        <td class="py-3 px-4 text-slate-400">${lab.test_date || 'N/A'}</td>
        <td class="py-3 px-4">
          <button onclick="openProvenanceModal(${lab.id})" class="px-2.5 py-1 rounded bg-slate-900 hover:bg-slate-800 border border-slate-700 text-[11px] text-teal-400 font-medium flex items-center gap-1">
            <i data-lucide="git-commit" class="h-3.5 w-3.5"></i>
            <span>${lab.source_document_name || 'Document'}</span>
          </button>
        </td>
        <td class="py-3 px-4">${verBadge}</td>
        <td class="py-3 px-4 text-right">
          <button onclick="openVerifyModal(${lab.id})" class="p-1.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white" title="Verify or edit result">
            <i data-lucide="edit-2" class="h-4 w-4"></i>
          </button>
        </td>
      </tr>
    `;
  }).join('');

  lucide.createIcons();
}

// ----------------------------
// Side-by-Side Source & Provenance Viewer
// ----------------------------
function openProvenanceModal(labId) {
  const lab = currentRecord.lab_results.find(l => l.id === labId);
  if (!lab) return;

  document.getElementById('prov-doc-name').textContent = lab.source_document_name || 'Document Source';
  document.getElementById('prov-snippet-box').textContent = lab.text_snippet || `Original source line: "${lab.test_name}: ${lab.value} ${lab.unit || ''} (Ref: ${lab.reference_range || 'Not provided'})"`;

  document.getElementById('prov-test-title').textContent = lab.test_name;
  document.getElementById('prov-val').textContent = `${lab.value} ${lab.unit || ''}`;
  document.getElementById('prov-unit').textContent = lab.unit || 'N/A';
  document.getElementById('prov-range').textContent = lab.reference_range || 'Not provided in source';
  document.getElementById('prov-date').textContent = lab.test_date || 'N/A';
  document.getElementById('prov-confidence').textContent = lab.confidence || 'High';

  const badge = document.getElementById('prov-status-badge');
  badge.textContent = lab.status;
  badge.className = `px-2.5 py-0.5 rounded-full text-xs font-bold ${
    lab.status === 'NORMAL' ? 'bg-emerald-950 text-emerald-400 border border-emerald-800' :
    (lab.status === 'LOW' || lab.status === 'HIGH' ? 'bg-red-950 text-red-400 border border-red-800' : 'bg-amber-950 text-amber-400 border border-amber-800')
  }`;

  document.getElementById('modal-provenance').classList.remove('hidden');
}

function closeProvenanceModal() {
  document.getElementById('modal-provenance').classList.add('hidden');
}

// ----------------------------
// Human Verification Modal
// ----------------------------
function openVerifyModal(labId) {
  const lab = currentRecord.lab_results.find(l => l.id === labId);
  if (!lab) return;

  document.getElementById('edit-lab-id').value = lab.id;
  document.getElementById('edit-test-name').value = lab.test_name;
  document.getElementById('edit-value').value = lab.value;
  document.getElementById('edit-unit').value = lab.unit || '';
  document.getElementById('edit-range').value = lab.reference_range || '';

  document.getElementById('modal-verify').classList.remove('hidden');
}

function closeVerifyModal() {
  document.getElementById('modal-verify').classList.add('hidden');
}

async function saveVerification(isEdit) {
  const labId = document.getElementById('edit-lab-id').value;
  const payload = {
    test_name: document.getElementById('edit-test-name').value,
    value: document.getElementById('edit-value').value,
    unit: document.getElementById('edit-unit').value,
    reference_range: document.getElementById('edit-range').value,
    verification_status: isEdit ? 'User Edited' : 'User Verified'
  };

  try {
    const res = await fetch(`/api/lab-results/${labId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    if (!res.ok) throw new Error('Update failed');
    closeVerifyModal();
    showToast('Success', isEdit ? 'Lab result updated & re-evaluated' : 'Lab result marked verified', 'success');
    await selectPatient(currentPatient.id);
  } catch (err) {
    showToast('Error', 'Failed to update lab result', 'error');
  }
}

// ----------------------------
// Inconsistency & Conflict Radar
// ----------------------------
function renderConflicts() {
  if (!currentRecord) return;
  const container = document.getElementById('conflict-radar-container');
  const conflicts = currentRecord.conflicts;

  if (conflicts.length === 0) {
    container.innerHTML = `
      <div class="p-8 rounded-2xl glass-panel text-center text-slate-400 space-y-2">
        <i data-lucide="check-circle" class="h-10 w-10 text-emerald-400 mx-auto"></i>
        <h4 class="text-base font-bold text-white">No Active Record Conflicts Flagged</h4>
        <p class="text-xs text-slate-500">MedLens conflict radar found no inconsistencies across patient documents and intake.</p>
      </div>
    `;
    lucide.createIcons();
    return;
  }

  container.innerHTML = conflicts.map(c => `
    <div class="glass-panel p-5 rounded-2xl border-l-4 ${c.status === 'Resolved' ? 'border-l-slate-600 opacity-60' : 'border-l-amber-500'} space-y-3">
      <div class="flex items-center justify-between">
        <div class="flex items-center gap-2">
          <span class="px-2.5 py-0.5 rounded text-xs font-bold bg-amber-950 text-amber-300 border border-amber-800">${c.conflict_type}</span>
          <h4 class="text-sm font-bold text-white">${c.field_name}</h4>
        </div>
        <span class="text-xs font-mono ${c.status === 'Resolved' ? 'text-emerald-400 font-semibold' : 'text-amber-400 font-bold'}">${c.status}</span>
      </div>

      <p class="text-xs text-slate-300">${c.description}</p>

      <div class="grid grid-cols-1 md:grid-cols-2 gap-3 p-3 rounded-xl bg-slate-900/90 border border-slate-800 text-xs">
        <div class="border-r border-slate-800/80 pr-2">
          <span class="text-slate-500 font-semibold">Source A (${c.source_a_name}):</span>
          <p class="font-bold text-white mt-0.5">${c.source_a_value}</p>
        </div>
        <div>
          <span class="text-slate-500 font-semibold">Source B (${c.source_b_name}):</span>
          <p class="font-bold text-white mt-0.5">${c.source_b_value}</p>
        </div>
      </div>

      ${c.status === 'Unresolved' ? `
        <div class="flex justify-end pt-1">
          <button onclick="resolveConflict(${c.id})" class="px-3.5 py-1.5 rounded-lg bg-amber-500 hover:bg-amber-400 text-slate-950 text-xs font-bold transition">
            Mark Conflict Resolved
          </button>
        </div>
      ` : ''}
    </div>
  `).join('');

  lucide.createIcons();
}

async function resolveConflict(conflictId) {
  try {
    const res = await fetch(`/api/patients/${currentPatient.id}/conflicts/${conflictId}/resolve`, { method: 'POST' });
    if (!res.ok) throw new Error('Resolution failed');
    showToast('Resolved', 'Conflict marked as resolved by clinician', 'success');
    await selectPatient(currentPatient.id);
    renderConflicts();
  } catch (err) {
    showToast('Error', 'Failed to resolve conflict', 'error');
  }
}

// ----------------------------
// Timeline Renderer
// ----------------------------
function renderTimeline() {
  if (!currentRecord) return;
  const container = document.getElementById('timeline-container');
  const events = currentRecord.timeline;

  if (events.length === 0) {
    container.innerHTML = '<p class="text-xs text-slate-500 pl-4">No timeline events recorded.</p>';
    return;
  }

  container.innerHTML = events.map(e => `
    <div class="relative pl-6">
      <div class="absolute -left-[9px] top-1.5 h-4 w-4 rounded-full bg-teal-500 border-4 border-slate-950"></div>
      <div class="glass-card p-4 rounded-xl space-y-1">
        <div class="flex items-center justify-between text-xs">
          <span class="font-bold text-teal-400 font-mono">${e.event_date}</span>
          <span class="px-2 py-0.5 rounded bg-slate-800 text-slate-300 font-mono">${e.event_type}</span>
        </div>
        <h4 class="text-sm font-bold text-white">${e.title}</h4>
        <p class="text-xs text-slate-300">${e.description || ''}</p>
        ${e.source_document_name ? `<p class="text-[11px] text-slate-500 font-mono mt-1">Source: ${e.source_document_name}</p>` : ''}
      </div>
    </div>
  `).join('');
}

// ----------------------------
// Report Comparison Trends Chart (Chart.js)
// ----------------------------
async function renderComparison() {
  if (!currentPatient) return;
  const res = await fetch(`/api/patients/${currentPatient.id}/trends`);
  const trendData = await res.json();

  const select = document.getElementById('trend-test-select');
  const tests = Object.keys(trendData);

  if (tests.length === 0) {
    select.innerHTML = '<option>No trend data available</option>';
    return;
  }

  select.innerHTML = tests.map(t => `<option value="${t}">${t} (${trendData[t].length} reports)</option>`).join('');
  renderTrendChartData(trendData, tests[0]);
}

function renderTrendChart() {
  if (!currentPatient) return;
  const testName = document.getElementById('trend-test-select').value;
  fetch(`/api/patients/${currentPatient.id}/trends`).then(r => r.json()).then(trendData => {
    renderTrendChartData(trendData, testName);
  });
}

function renderTrendChartData(trendData, testName) {
  const points = trendData[testName] || [];
  const dates = points.map(p => p.date);
  const values = points.map(p => p.numeric_value);

  const ctx = document.getElementById('trendChartCanvas').getContext('2d');
  if (trendChartInstance) trendChartInstance.destroy();

  trendChartInstance = new Chart(ctx, {
    type: 'line',
    data: {
      labels: dates,
      datasets: [{
        label: `${testName} (${points[0]?.unit || ''})`,
        data: values,
        borderColor: '#2dd4bf',
        backgroundColor: 'rgba(45, 212, 191, 0.15)',
        borderWidth: 3,
        fill: true,
        tension: 0.3,
        pointBackgroundColor: points.map(p => p.status === 'NORMAL' ? '#10b981' : (p.status === 'UNKNOWN' ? '#f59e0b' : '#ef4444')),
        pointRadius: 6
      }]
    },
    options: {
      responsive: true,
      plugins: {
        legend: { labels: { color: '#cbd5e1', font: { family: 'Inter' } } }
      },
      scales: {
        x: { ticks: { color: '#94a3b8' }, grid: { color: 'rgba(51, 65, 85, 0.3)' } },
        y: { ticks: { color: '#94a3b8' }, grid: { color: 'rgba(51, 65, 85, 0.3)' } }
      }
    }
  });

  // Neutral trend summary phrasing (Medically compliant!)
  const summaryBox = document.getElementById('trend-neutral-summary');
  if (points.length > 1) {
    const firstP = points[0];
    const lastP = points[points.length - 1];
    summaryBox.innerHTML = `
      <p class="font-bold text-white">Neutral Longitudinal Observation:</p>
      <p class="mt-1">${testName} was reported as <b>${firstP.value} ${firstP.unit}</b> on ${firstP.date} (${firstP.status}) and was subsequently reported as <b>${lastP.value} ${lastP.unit}</b> on ${lastP.date} (${lastP.status}).</p>
      <p class="text-[11px] text-slate-500 italic mt-1 font-mono">Reference range provided in latest report: ${lastP.reference_range}</p>
    `;
  } else if (points.length === 1) {
    summaryBox.innerHTML = `<p>${testName} has 1 documented report value of <b>${points[0].value} ${points[0].unit}</b> on ${points[0].date} (${points[0].status}).</p>`;
  }
}

// ----------------------------
// PDF Export Trigger
// ----------------------------
function exportPdfReport() {
  if (!currentPatient) return;
  window.open(`/api/patients/${currentPatient.id}/export`, '_blank');
}

// ----------------------------
// Modals Control & Document Upload
// ----------------------------
function openNewPatientModal() {
  document.getElementById('modal-new-patient').classList.remove('hidden');
}
function closeNewPatientModal() {
  document.getElementById('modal-new-patient').classList.add('hidden');
}

async function submitNewPatient() {
  const code = document.getElementById('new-pat-code').value || `PAT-${Date.now().toString().slice(-4)}`;
  const name = document.getElementById('new-pat-name').value;
  if (!name) return showToast('Input Required', 'Please provide a patient display name', 'error');

  const age = parseInt(document.getElementById('new-pat-age').value) || null;
  const sex = document.getElementById('new-pat-sex').value;
  const syms = document.getElementById('new-pat-symptoms').value.split(',').map(s => ({ name: s.trim(), source: 'USER_PROVIDED' })).filter(s => s.name);
  const conds = document.getElementById('new-pat-conditions').value.split(',').map(c => ({ name: c.trim(), source: 'USER_PROVIDED' })).filter(c => c.name);

  try {
    const res = await fetch('/api/patients', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        patient_id_code: code,
        display_name: name,
        age: age,
        sex: sex,
        symptoms: syms,
        conditions: conds
      })
    });
    if (!res.ok) throw new Error('Patient creation failed');
    const newP = await res.json();
    closeNewPatientModal();
    showToast('Patient Created', `Created intake for ${name}`, 'success');
    await selectPatient(newP.id);
    navigateTo('record');
  } catch (err) {
    showToast('Error', 'Patient ID code already exists or invalid input', 'error');
  }
}

function openUploadModal() {
  document.getElementById('modal-upload').classList.remove('hidden');
}
function closeUploadModal() {
  document.getElementById('modal-upload').classList.add('hidden');
}

function setupDropZone() {
  const dz = document.getElementById('drop-zone');
  const input = document.getElementById('upload-file-input');
  if (!dz) return;
  dz.onclick = () => input.click();
}

function handleFileSelected(event) {
  if (event.target.files.length > 0) {
    selectedFile = event.target.files[0];
    const nameEl = document.getElementById('upload-file-name');
    nameEl.textContent = `Selected: ${selectedFile.name} (${Math.round(selectedFile.size / 1024)} KB)`;
    nameEl.classList.remove('hidden');
  }
}

async function submitUpload() {
  if (!selectedFile) return showToast('File Required', 'Please select a PDF or image medical report first', 'error');
  if (!currentPatient) return showToast('Select Patient', 'Please select or create a patient first', 'error');

  const btn = document.getElementById('btn-submit-upload');
  btn.disabled = true;
  btn.innerHTML = `<span>Processing AI Pipeline...</span>`;

  const formData = new FormData();
  formData.append('file', selectedFile);

  try {
    const res = await fetch(`/api/patients/${currentPatient.id}/documents`, {
      method: 'POST',
      body: formData
    });
    if (!res.ok) throw new Error('Upload failed');
    const data = await res.json();
    closeUploadModal();
    showToast('Extraction Complete', `Extracted ${data.extracted_count} structured lab results from report!`, 'success');
    await selectPatient(currentPatient.id);
    navigateTo('record');
  } catch (err) {
    showToast('Pipeline Error', 'Failed to extract structured data from document', 'error');
  } finally {
    btn.disabled = false;
    btn.innerHTML = `<span>Run AI Pipeline</span><i data-lucide="arrow-right" class="h-4 w-4"></i>`;
    lucide.createIcons();
  }
}
