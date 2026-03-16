/**
 * PipelineIQ — Frontend SPA
 * Single-page application with routing, API calls, animations, charts
 */

const API = '/api';

// ──────────────────────────────────────────────────────────────────
// STATE
// ──────────────────────────────────────────────────────────────────
const state = {
  currentPage: 'dashboard',
  currentPipeline: null,
  currentRun: null,
  pipelines: [],
  metrics: null,
  runsPage: 1,
  runsFilters: { status: '', pipeline_id: '', search: '' },
  charts: {},
  typewriterTimeout: null,
};

// ──────────────────────────────────────────────────────────────────
// ROUTER
// ──────────────────────────────────────────────────────────────────
const App = {

  /** Navigate to a named page, with optional data */
  navigate(page, data = {}) {
    // Hide all pages
    document.querySelectorAll('.page').forEach(el => el.classList.add('hidden'));

    // Show target page
    const target = document.getElementById(`page-${page}`);
    if (target) {
      target.classList.remove('hidden');
      target.style.animation = 'none';
      target.offsetHeight;
      target.style.animation = '';
    }

    // Update nav active state
    document.querySelectorAll('.nav-link').forEach(link => {
      link.classList.toggle('active', link.dataset.page === page);
    });

    state.currentPage = page;

    // Load page data
    switch (page) {
      case 'dashboard':        App.loadDashboard(); break;
      case 'pipeline-detail':  App.loadPipelineDetail(data.pipelineId, data.runId); break;
      case 'pipelines-list':   App.loadRunsList(); App.loadPipelineFilterOptions(); break;
      case 'metrics':          App.loadMetrics(); break;
      case 'create-pipeline':  App.resetCreateForm(); break;
    }

    window.scrollTo({ top: 0, behavior: 'smooth' });
  },

  // ──────────────────────────────────────────────────────────────
  // DASHBOARD
  // ──────────────────────────────────────────────────────────────

  async loadDashboard() {
    try {
      const [pipelines, metricsData] = await Promise.all([
        fetchAPI('/pipelines/'),
        fetchAPI('/metrics/'),
      ]);

      state.pipelines = pipelines;
      state.metrics = metricsData;

      // Animate stats count-up
      animateCountUp('stat-total',    metricsData.summary.total_pipelines);
      animateCountUp('stat-success',  metricsData.summary.success_rate, '%');
      animateCountUp('stat-avg-time', metricsData.summary.avg_duration, 's');
      animateCountUp('stat-active',   metricsData.summary.active_runs);

      // Render pipeline cards
      renderPipelineGrid(pipelines);

    } catch (err) {
      showToast('Failed to load dashboard data', 'error');
      document.getElementById('pipelineGrid').innerHTML =
        `<div class="empty-state">
          <div class="empty-state-icon">⚠️</div>
          <h3>Could not load pipelines</h3>
          <p>Is the Django server running?</p>
        </div>`;
    }
  },

  // ──────────────────────────────────────────────────────────────
  // PIPELINE DETAIL
  // ──────────────────────────────────────────────────────────────

  async loadPipelineDetail(pipelineId, runId = null) {
    try {
      const pipeline = await fetchAPI(`/pipelines/${pipelineId}/`);
      state.currentPipeline = pipeline;

      document.getElementById('detail-title').textContent = pipeline.name;
      document.getElementById('detail-subtitle').textContent = pipeline.repo_url;

      // Set up trigger button
      const triggerBtn = document.getElementById('triggerBtn');
      triggerBtn.onclick = () => App.triggerRun(pipelineId);

      // Load runs for this pipeline
      const runs = await fetchAPI(`/pipelines/${pipelineId}/runs/?limit=10`);

      // Pick which run to display
      let targetRun = null;
      if (runId) {
        targetRun = await fetchAPI(`/runs/${runId}/`);
      } else if (runs.length > 0) {
        targetRun = await fetchAPI(`/runs/${runs[0].id}/`);
      }

      if (targetRun) {
        state.currentRun = targetRun;
        renderRunDetail(targetRun);
      }

      // Render recent runs list
      renderRecentRuns(runs, pipelineId);

    } catch (err) {
      showToast('Failed to load pipeline detail', 'error');
      console.error(err);
    }
  },

  async triggerRun(pipelineId) {
    try {
      const btn = document.getElementById('triggerBtn');
      btn.textContent = '⏳ Triggering...';
      btn.disabled = true;

      const run = await fetchAPI(`/pipelines/${pipelineId}/trigger/`, 'POST');
      showToast(`✅ Run #${run.run_number} triggered!`, 'success');

      setTimeout(() => App.loadPipelineDetail(pipelineId, run.id), 500);

    } catch (err) {
      showToast('Failed to trigger run', 'error');
    } finally {
      const btn = document.getElementById('triggerBtn');
      if (btn) { btn.textContent = '▶ Trigger Run'; btn.disabled = false; }
    }
  },

  // ──────────────────────────────────────────────────────────────
  // PIPELINE RUNS LIST
  // ──────────────────────────────────────────────────────────────

  async loadRunsList() {
    const tbody = document.getElementById('runsTableBody');
    tbody.innerHTML = `<tr><td colspan="8" class="loading-cell">Loading runs...</td></tr>`;

    try {
      const { status: s, pipeline_id: pid, search } = state.runsFilters;
      const q = new URLSearchParams({
        page: state.runsPage,
        page_size: 15,
        ...(s      && { status: s }),
        ...(pid    && { pipeline_id: pid }),
        ...(search && { search }),
      });

      const data = await fetchAPI(`/runs/?${q}`);
      renderRunsTable(data);

    } catch (err) {
      tbody.innerHTML = `<tr><td colspan="8" class="loading-cell">Error loading runs.</td></tr>`;
    }
  },

  async loadPipelineFilterOptions() {
    try {
      const pipelines = await fetchAPI('/pipelines/');
      const sel = document.getElementById('pipelineFilter');
      sel.innerHTML = '<option value="">All Pipelines</option>';
      pipelines.forEach(p => {
        const opt = document.createElement('option');
        opt.value = p.id;
        opt.textContent = p.name;
        sel.appendChild(opt);
      });
    } catch {}
  },

  // ──────────────────────────────────────────────────────────────
  // CREATE PIPELINE
  // ──────────────────────────────────────────────────────────────

  resetCreateForm() {
    ['f-name', 'f-repo'].forEach(id => { document.getElementById(id).value = ''; });
    document.getElementById('f-branch').value = 'main';
    document.getElementById('f-trigger').value = 'push';
    document.getElementById('f-env').value = 'dev';
    document.getElementById('formSuccess').classList.add('hidden');
    document.getElementById('formError').classList.add('hidden');
  },

  async createPipeline() {
    const name        = document.getElementById('f-name').value.trim();
    const repo_url    = document.getElementById('f-repo').value.trim();
    const branch      = document.getElementById('f-branch').value.trim() || 'main';
    const trigger     = document.getElementById('f-trigger').value;
    const environment = document.getElementById('f-env').value;

    document.getElementById('formSuccess').classList.add('hidden');
    document.getElementById('formError').classList.add('hidden');

    if (!name || !repo_url) {
      document.getElementById('formErrorMsg').textContent = 'Project name and repo URL are required.';
      document.getElementById('formError').classList.remove('hidden');
      return;
    }

    const btn = document.getElementById('createPipelineBtn');
    btn.textContent = 'Creating...';
    btn.disabled = true;

    try {
      const pipeline = await fetchAPI('/pipelines/', 'POST', {
        name, repo_url, branch, trigger, environment
      });
      document.getElementById('formSuccessMsg').textContent =
        `Pipeline "${pipeline.name}" created! ID: ${pipeline.id}`;
      document.getElementById('formSuccess').classList.remove('hidden');
      App.resetCreateForm();
      showToast(`🚀 Pipeline "${pipeline.name}" created!`, 'success');

    } catch (err) {
      document.getElementById('formErrorMsg').textContent =
        'Creation failed. Check the console for details.';
      document.getElementById('formError').classList.remove('hidden');
    } finally {
      btn.textContent = 'Create Pipeline →';
      btn.disabled = false;
    }
  },

  // ──────────────────────────────────────────────────────────────
  // METRICS
  // ──────────────────────────────────────────────────────────────

  async loadMetrics() {
    try {
      const data = await fetchAPI('/metrics/');
      state.metrics = data;
      renderCharts(data);
    } catch (err) {
      showToast('Failed to load metrics', 'error');
    }
  },

};

// ──────────────────────────────────────────────────────────────────
// RENDER FUNCTIONS
// ──────────────────────────────────────────────────────────────────

/** Render the pipeline cards grid on dashboard */
function renderPipelineGrid(pipelines) {
  const grid = document.getElementById('pipelineGrid');

  if (pipelines.length === 0) {
    grid.innerHTML = `
      <div class="empty-state">
        <div class="empty-state-icon">🚀</div>
        <h3>No pipelines yet</h3>
        <p>Create your first pipeline to get started</p>
      </div>`;
    return;
  }

  grid.innerHTML = pipelines.map((p, i) => {
    const run     = p.latest_run;
    const status  = run ? run.status : 'pending';
    const progress = getProgressPercent(run);

    return `
    <div class="pipeline-card"
         onclick="App.navigate('pipeline-detail', {pipelineId: ${p.id}})"
         style="animation-delay: ${i * 0.06}s">
      <div class="pipeline-card-header">
        <div>
          <div class="pipeline-name">${escHtml(p.name)}</div>
          <div class="pipeline-repo">📁 ${escHtml(p.repo_url.replace('https://github.com/', ''))}</div>
        </div>
        ${statusBadge(status)}
      </div>

      <div class="pipeline-progress">
        <div class="pipeline-progress-bar ${status}" style="width: ${progress}%"></div>
      </div>

      <div class="pipeline-meta">
        <span class="meta-item"><span class="meta-icon">🌿</span> ${escHtml(p.branch)}</span>
        <span class="meta-item"><span class="meta-icon">⚡</span> ${escHtml(p.trigger)}</span>
        ${run ? `<span class="meta-item"><span class="meta-icon">⏱</span> ${formatDuration(run.duration)}</span>` : ''}
        ${run ? `<span class="meta-item"><span class="meta-icon">🕒</span> ${timeAgo(run.started_at)}</span>` : ''}
        <span class="meta-item"><span class="meta-icon">✅</span> ${p.success_rate}% success</span>
      </div>
    </div>`;
  }).join('');
}

/** Render the stage visualizer and commit info for a pipeline run */
function renderRunDetail(run) {
  // Commit info bar
  const commitBar = document.getElementById('commitInfoBar');
  commitBar.innerHTML = `
    <span>📝 <strong>${escHtml(run.author || 'unknown')}</strong></span>
    <span class="commit-hash">${run.commit_hash.slice(0, 8)}</span>
    <span style="flex:1;">${escHtml(run.commit_message || '')}</span>
    <span>🌿 ${escHtml(run.pipeline?.branch || state.currentPipeline?.branch || 'main')}</span>
    ${statusBadge(run.status)}
    <span style="color:var(--text-muted);font-size:0.8rem;">${timeAgo(run.started_at)}</span>
  `;

  // Stage icons and labels
  const stageIcons  = { source: '📥', build: '🐳', test: '🧪', push: '📤', deploy: '🚀' };
  const stageLabels = { source: 'Source', build: 'Build', test: 'Test', push: 'Push to ECR', deploy: 'Deploy' };

  const stagesEl = document.getElementById('stagesVisualizer');
  stagesEl.innerHTML = run.stages.map((stage, i) => {
    const statusIcon =
      stage.status === 'success' ? '✓' :
      stage.status === 'failed'  ? '✕' :
      stage.status === 'running' ? ''  :
      stage.status === 'skipped' ? '–' : '○';

    const isLast = i === run.stages.length - 1;
    const stageJson = JSON.stringify(stage).replace(/"/g, '&quot;');

    return `
      <div class="stage-item ${stage.status}" id="stage-${stage.id}"
           onclick="showStageLogs(${stageJson})">
        <div class="stage-icon-wrap">
          ${stageIcons[stage.name] || '⚙️'}
          <div class="stage-spinner"></div>
        </div>
        <div class="stage-name">${stageLabels[stage.name] || stage.name}</div>
        <div class="stage-duration">${stage.duration ? stage.duration + 's' : stage.status === 'running' ? '...' : '-'}</div>
        <div class="stage-status-icon">${statusIcon}</div>
      </div>
      ${!isLast ? '<div class="stage-arrow">→</div>' : ''}
    `;
  }).join('');

  // Auto-show logs of first notable stage
  const notableStage =
    run.stages.find(s => s.status === 'failed' || s.status === 'running') ||
    run.stages[run.stages.length - 1];

  if (notableStage && notableStage.logs) {
    showStageLogs(notableStage);
  }
}

/** Show logs for a stage in the terminal */
function showStageLogs(stage) {
  // Update active stage styling
  document.querySelectorAll('.stage-item').forEach(el => el.classList.remove('active'));
  const el = document.getElementById(`stage-${stage.id}`);
  if (el) el.classList.add('active');

  const body  = document.getElementById('terminalBody');
  const title = document.getElementById('terminalTitle');

  const stageLabels = {
    source: 'Source', build: 'Build', test: 'Test',
    push: 'Push to ECR', deploy: 'Deploy'
  };
  title.textContent = `${stageLabels[stage.name] || stage.name} — ${stage.status}`;

  if (!stage.logs) {
    body.innerHTML = '<span class="terminal-placeholder">No logs available for this stage.</span>';
    return;
  }

  // Color-coded log lines
  const lines = stage.logs.split('\n');
  const html = lines.map(line => {
    const match = line.match(/\] (INFO|SUCCESS|ERROR|FATAL|WARN)\s/);
    const level = match ? match[1] : 'INFO';
    return `<span class="log-line ${level}">${escHtml(line)}</span>`;
  }).join('\n');

  body.innerHTML = html + '\n<span class="log-cursor"></span>';
  body.scrollTop = body.scrollHeight;
}

/** Render the recent runs sidebar list */
function renderRecentRuns(runs, pipelineId) {
  const el = document.getElementById('recentRunsList');

  if (runs.length === 0) {
    el.innerHTML = '<p style="color:var(--text-secondary);font-size:.875rem;">No runs yet.</p>';
    return;
  }

  el.innerHTML = runs.map(run => `
    <div class="run-item" onclick="App.loadPipelineDetail(${pipelineId}, ${run.id})">
      <span class="run-number">#${run.run_number}</span>
      ${statusBadge(run.status)}
      <span class="run-commit">${run.commit_hash.slice(0, 7)}</span>
      <span class="run-msg">${escHtml(run.commit_message || '')}</span>
      <span class="run-meta">${formatDuration(run.duration)} · ${timeAgo(run.started_at)}</span>
    </div>
  `).join('');
}

/** Render the paginated runs table */
function renderRunsTable(data) {
  const tbody = document.getElementById('runsTableBody');

  if (data.results.length === 0) {
    tbody.innerHTML = `<tr><td colspan="8" class="loading-cell">No runs found.</td></tr>`;
    renderPagination(data);
    return;
  }

  tbody.innerHTML = data.results.map(run => `
    <tr>
      <td><strong>${escHtml(run.pipeline_name)}</strong></td>
      <td style="font-family:var(--mono);color:var(--text-secondary);">#${run.run_number}</td>
      <td>${statusBadge(run.status)}</td>
      <td style="color:var(--text-secondary);">${escHtml(run.author || '—')}</td>
      <td class="commit-cell">
        <span class="commit-hash-short">${run.commit_hash.slice(0, 7)}</span>
        <span class="commit-msg">${escHtml(run.commit_message || '')}</span>
      </td>
      <td style="font-family:var(--mono);color:var(--text-secondary);">${formatDuration(run.duration)}</td>
      <td style="color:var(--text-secondary);font-size:0.8rem;">${timeAgo(run.started_at)}</td>
      <td>
        <button class="action-btn"
          onclick="App.navigate('pipeline-detail', {pipelineId: ${run.pipeline}, runId: ${run.id}})">
          View →
        </button>
      </td>
    </tr>
  `).join('');

  renderPagination(data);
}

/** Render pagination controls */
function renderPagination(data) {
  const el = document.getElementById('pagination');
  if (data.total_pages <= 1) { el.innerHTML = ''; return; }

  let html = `<button class="page-btn" onclick="changePage(${data.page - 1})"
    ${data.page <= 1 ? 'disabled' : ''}>← Prev</button>`;

  for (let i = 1; i <= data.total_pages; i++) {
    if (i === 1 || i === data.total_pages || Math.abs(i - data.page) <= 2) {
      html += `<button class="page-btn ${i === data.page ? 'active' : ''}"
        onclick="changePage(${i})">${i}</button>`;
    } else if (Math.abs(i - data.page) === 3) {
      html += `<span style="color:var(--text-muted);padding:0 4px;">…</span>`;
    }
  }

  html += `<button class="page-btn" onclick="changePage(${data.page + 1})"
    ${data.page >= data.total_pages ? 'disabled' : ''}>Next →</button>`;

  el.innerHTML = html;
}

function changePage(page) {
  state.runsPage = page;
  App.loadRunsList();
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

// ──────────────────────────────────────────────────────────────────
// CHARTS (Chart.js)
// ──────────────────────────────────────────────────────────────────

function renderCharts(data) {
  // Destroy existing charts to avoid canvas reuse errors
  Object.values(state.charts).forEach(c => c.destroy());
  state.charts = {};

  Chart.defaults.color = '#94a3b8';
  Chart.defaults.font.family = "'Space Grotesk', sans-serif";

  const gridColor = 'rgba(255,255,255,0.04)';

  // ── 1. Success vs Failure Line Chart ──
  const lineCtx = document.getElementById('chart-success-failure').getContext('2d');
  state.charts.line = new Chart(lineCtx, {
    type: 'line',
    data: {
      labels: data.daily_runs.map(d => d.date.slice(5)),
      datasets: [
        {
          label: 'Success',
          data: data.daily_runs.map(d => d.success),
          borderColor: '#22c55e',
          backgroundColor: 'rgba(34,197,94,0.12)',
          fill: true,
          tension: 0.4,
          borderWidth: 2,
          pointRadius: 3,
        },
        {
          label: 'Failed',
          data: data.daily_runs.map(d => d.failed),
          borderColor: '#ef4444',
          backgroundColor: 'rgba(239,68,68,0.08)',
          fill: true,
          tension: 0.4,
          borderWidth: 2,
          pointRadius: 3,
        },
      ],
    },
    options: {
      responsive: true,
      plugins: { legend: { position: 'top' } },
      scales: {
        x: { grid: { color: gridColor } },
        y: { grid: { color: gridColor }, beginAtZero: true, ticks: { stepSize: 1 } },
      },
    },
  });

  // ── 2. Avg Build Duration Bar Chart ──
  const barCtx = document.getElementById('chart-duration').getContext('2d');
  state.charts.bar = new Chart(barCtx, {
    type: 'bar',
    data: {
      labels: data.pipeline_durations.map(d => d.name),
      datasets: [{
        label: 'Avg Duration (s)',
        data: data.pipeline_durations.map(d => d.avg_duration),
        backgroundColor: [
          'rgba(99,102,241,0.7)',
          'rgba(99,102,241,0.5)',
          'rgba(99,102,241,0.3)',
        ],
        borderColor: '#6366f1',
        borderWidth: 1,
        borderRadius: 6,
      }],
    },
    options: {
      responsive: true,
      plugins: { legend: { display: false } },
      scales: {
        x: { grid: { color: gridColor } },
        y: { grid: { color: gridColor }, beginAtZero: true },
      },
    },
  });

  // ── 3. Deploy Frequency Bar Chart ──
  const freqCtx = document.getElementById('chart-deploy-freq').getContext('2d');
  state.charts.freq = new Chart(freqCtx, {
    type: 'bar',
    data: {
      labels: data.deploy_frequency.map(d => d.date),
      datasets: [{
        label: 'Deployments',
        data: data.deploy_frequency.map(d => d.deploys),
        backgroundColor: 'rgba(34,197,94,0.5)',
        borderColor: '#22c55e',
        borderWidth: 1,
        borderRadius: 4,
      }],
    },
    options: {
      responsive: true,
      plugins: { legend: { display: false } },
      scales: {
        x: {
          grid: { color: gridColor },
          ticks: { maxTicksLimit: 8, maxRotation: 0 },
        },
        y: { grid: { color: gridColor }, beginAtZero: true, ticks: { stepSize: 1 } },
      },
    },
  });

  // ── 4. Failure Stage Doughnut Chart ──
  const pieCtx = document.getElementById('chart-failure-stage').getContext('2d');
  const stageLabels = {
    source: 'Source', build: 'Build', test: 'Test',
    push: 'Push to ECR', deploy: 'Deploy'
  };

  state.charts.pie = new Chart(pieCtx, {
    type: 'doughnut',
    data: {
      labels: data.failure_stages.map(s => stageLabels[s.stage] || s.stage),
      datasets: [{
        data: data.failure_stages.map(s => s.count),
        backgroundColor: [
          'rgba(239,68,68,0.8)',
          'rgba(245,158,11,0.8)',
          'rgba(99,102,241,0.8)',
          'rgba(34,197,94,0.8)',
          'rgba(148,163,184,0.5)',
        ],
        borderWidth: 2,
        borderColor: '#111827',
      }],
    },
    options: {
      responsive: true,
      plugins: {
        legend: { position: 'bottom', labels: { padding: 16, boxWidth: 12 } },
      },
      cutout: '65%',
    },
  });
}

// ──────────────────────────────────────────────────────────────────
// UTILITY FUNCTIONS
// ──────────────────────────────────────────────────────────────────

/** Generic API fetch wrapper */
async function fetchAPI(path, method = 'GET', body = null) {
  const opts = {
    method,
    headers: { 'Content-Type': 'application/json' },
  };
  if (body) opts.body = JSON.stringify(body);

  const res = await fetch(API + path, opts);
  if (!res.ok) {
    const err = await res.text();
    throw new Error(`API ${method} ${path} failed: ${res.status} ${err}`);
  }
  return res.json();
}

/** Returns a colored status badge HTML string */
function statusBadge(status) {
  return `<span class="status-badge ${status}">
    <span class="status-dot"></span>${status}
  </span>`;
}

/** Escape HTML special characters */
function escHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

/** Format duration in seconds to a readable string */
function formatDuration(seconds) {
  if (!seconds) return '—';
  if (seconds < 60) return `${seconds}s`;
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m}m ${s}s`;
}

/** Relative time (e.g. "2 hours ago") */
function timeAgo(dateStr) {
  if (!dateStr) return '—';
  const diff = Date.now() - new Date(dateStr).getTime();
  const s = Math.floor(diff / 1000);
  if (s < 60)    return `${s}s ago`;
  if (s < 3600)  return `${Math.floor(s / 60)}m ago`;
  if (s < 86400) return `${Math.floor(s / 3600)}h ago`;
  return `${Math.floor(s / 86400)}d ago`;
}

/** Returns progress percentage for a run's progress bar */
function getProgressPercent(run) {
  if (!run) return 0;
  if (run.status === 'success') return 100;
  if (run.status === 'failed')  return 60;
  if (run.status === 'running') return 45;
  return 0;
}

/** Animate a numeric counter from 0 to target */
function animateCountUp(elementId, target, suffix = '') {
  const el = document.getElementById(elementId);
  if (!el) return;
  const duration = 1000;
  const start = Date.now();

  function update() {
    const elapsed  = Date.now() - start;
    const progress = Math.min(elapsed / duration, 1);
    const eased    = 1 - Math.pow(1 - progress, 3);
    const current  = Math.round(target * eased);
    el.textContent = current + suffix;
    if (progress < 1) requestAnimationFrame(update);
  }

  requestAnimationFrame(update);
}

/** Show a toast notification */
function showToast(message, type = 'success') {
  const toast = document.getElementById('toast');
  toast.textContent = message;
  toast.className = `toast ${type}`;
  setTimeout(() => { toast.classList.add('hidden'); }, 3500);
}

// ──────────────────────────────────────────────────────────────────
// EVENT LISTENERS
// ──────────────────────────────────────────────────────────────────

/** Wire up all nav links */
document.querySelectorAll('[data-page]').forEach(el => {
  el.addEventListener('click', e => {
    e.preventDefault();
    const page = el.dataset.page;
    if (page) App.navigate(page);
    document.getElementById('mobileMenu').classList.remove('open');
  });
});

/** Mobile hamburger toggle */
document.getElementById('mobileToggle').addEventListener('click', () => {
  document.getElementById('mobileMenu').classList.toggle('open');
});

/** Runs list status filter */
document.getElementById('statusFilter').addEventListener('change', e => {
  state.runsFilters.status = e.target.value;
  state.runsPage = 1;
});

/** Runs list pipeline filter */
document.getElementById('pipelineFilter').addEventListener('change', e => {
  state.runsFilters.pipeline_id = e.target.value;
  state.runsPage = 1;
});

/** Debounced search input */
let searchTimer;
document.getElementById('searchInput').addEventListener('input', e => {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(() => {
    state.runsFilters.search = e.target.value.trim();
    state.runsPage = 1;
    if (state.currentPage === 'pipelines-list') App.loadRunsList();
  }, 350);
});

// ──────────────────────────────────────────────────────────────────
// INIT — Boot the app
// ──────────────────────────────────────────────────────────────────
App.navigate('dashboard');