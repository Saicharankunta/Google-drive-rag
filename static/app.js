const API = '/api';

const state = { config: null };

if (typeof marked !== 'undefined') {
  marked.setOptions({ breaks: true, gfm: true });
}

function renderMarkdown(text) {
  if (!text) return '';
  const html = marked.parse(text);
  return typeof DOMPurify !== 'undefined' ? DOMPurify.sanitize(html) : html;
}

async function api(method, path, body) {
  const opts = { method, headers: {} };
  if (body) {
    opts.headers['Content-Type'] = 'application/json';
    opts.body = JSON.stringify(body);
  }
  const res = await fetch(API + path, opts);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, c => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
  }[c]));
}

function toast(msg, type = 'success') {
  const container = document.getElementById('toast-container');
  const el = document.createElement('div');
  el.className = `toast ${type}`;
  el.innerHTML = msg;
  container.appendChild(el);
  setTimeout(() => {
    el.style.opacity = '0';
    el.style.transition = 'opacity 0.3s';
    setTimeout(() => el.remove(), 300);
  }, 4000);
}

function setStatus(working, label) {
  const ind = document.getElementById('status-indicator');
  const text = ind.querySelector('.status-text');
  const footer = document.getElementById('footer-status');
  if (working) {
    ind.classList.add('working');
    text.textContent = label || 'WORKING';
    footer.textContent = (label || 'working').toLowerCase();
  } else {
    ind.classList.remove('working');
    text.textContent = 'IDLE';
    footer.textContent = 'ready';
  }
}

document.querySelectorAll('.tab').forEach(tab => {
  tab.addEventListener('click', () => {
    const target = tab.dataset.tab;
    document.querySelectorAll('.tab').forEach(t => {
      t.classList.toggle('active', t.dataset.tab === target);
    });
    document.querySelectorAll('.pane').forEach(p => {
      p.classList.toggle('active', p.dataset.pane === target);
    });
  });
});

document.getElementById('query-top-k').addEventListener('input', e => {
  document.getElementById('query-top-k-val').textContent = e.target.value;
});

function renderConfig(config) {
  const rows = [
    ['LLM provider', config.llm_provider],
    ['LLM model', config.llm_model],
    ['Embed model', config.embed_model],
    ['Indexed chunks', String(config.chunk_count)],
    ['Drive authenticated', config.authenticated ? 'yes' : 'no'],
    ['Drive folder', config.drive_folder_id || 'all files'],
    ['Default top-k', String(config.top_k)],
  ];

  document.getElementById('config-list').innerHTML = rows.map(([key, val]) => `
    <div class="config-row">
      <span class="config-key">${escapeHtml(key)}</span>
      <span class="config-val">${escapeHtml(val)}</span>
    </div>
  `).join('');

  document.getElementById('index-chunk-count').textContent = config.chunk_count;
  document.getElementById('index-auth-status').textContent = config.authenticated ? 'yes' : 'no';
  document.getElementById('hero-sub').textContent =
    `DRIVE-RAG · ${config.llm_provider.toUpperCase()} · CHROMADB · ${config.chunk_count} CHUNKS`;
  document.getElementById('model-pill-text').textContent =
    `MODEL · ${config.llm_model.toUpperCase()} · RETRIEVAL`;
}

async function loadConfig() {
  state.config = await api('GET', '/config');
  renderConfig(state.config);
  if (state.config.top_k) {
    document.getElementById('query-top-k').value = state.config.top_k;
    document.getElementById('query-top-k-val').textContent = state.config.top_k;
  }
}

document.getElementById('query-submit').addEventListener('click', async () => {
  const question = document.getElementById('query-question').value.trim();
  if (!question) return toast('Question is empty', 'error');

  const btn = document.getElementById('query-submit');
  btn.disabled = true;
  btn.querySelector('.btn-label').textContent = 'Thinking…';
  setStatus(true, 'QUERYING');

  const empty = document.getElementById('query-empty');
  const output = document.getElementById('query-output');
  empty.classList.remove('hidden');
  output.classList.add('hidden');

  try {
    const topK = parseInt(document.getElementById('query-top-k').value, 10);
    const result = await api('POST', '/query', { question, top_k: topK });

    empty.classList.add('hidden');
    output.classList.remove('hidden');
    output.innerHTML = `
      <div class="output-item">
        <div class="output-item-header">
          <div class="output-item-title">Answer · ${escapeHtml(result.provider)}</div>
        </div>
        <div class="answer-text markdown-body">${renderMarkdown(result.answer)}</div>
        <div class="source-list">
          <h4>Sources</h4>
          ${result.sources.map(s => `
            <span class="source-chip">
              ${escapeHtml(s.file_name)} · chunk ${s.chunk_index}
            </span>
          `).join('')}
        </div>
      </div>
    `;
    toast('Answer ready');
  } catch (e) {
    toast(`Failed: ${escapeHtml(e.message)}`, 'error');
  } finally {
    btn.disabled = false;
    btn.querySelector('.btn-label').textContent = 'Ask';
    setStatus(false);
  }
});

let indexPollTimer = null;

function showIndexResult(stats, error) {
  const empty = document.getElementById('index-empty');
  const output = document.getElementById('index-output');
  empty.classList.add('hidden');
  output.classList.remove('hidden');

  if (error) {
    output.innerHTML = `
      <div class="output-item">
        <div class="output-item-title">Index failed</div>
        <div class="answer-text" style="color:#991b1b">${escapeHtml(error)}</div>
      </div>
    `;
    return;
  }

  output.innerHTML = `
    <div class="output-item">
      <div class="output-item-title">Index complete</div>
      <div class="answer-text">
        Files found: ${stats.files_found}
        Files indexed: ${stats.files_indexed}
        Chunks indexed: ${stats.chunks_indexed}
        Total chunks: ${stats.total_chunks}
      </div>
    </div>
  `;
}

function pollIndexStatus() {
  indexPollTimer = setInterval(async () => {
    try {
      const status = await api('GET', '/index/status');
      if (status.status === 'running') return;

      clearInterval(indexPollTimer);
      indexPollTimer = null;

      const btn = document.getElementById('index-start');
      btn.disabled = false;
      btn.querySelector('.btn-label').textContent = 'Index Drive';
      setStatus(false);

      if (status.status === 'error') {
        showIndexResult(null, status.error);
        toast(`Index failed: ${escapeHtml(status.error)}`, 'error');
      } else {
        showIndexResult(status.stats);
        toast(`Indexed ${status.stats.files_indexed} files`);
        await loadConfig();
      }
    } catch (e) {
      clearInterval(indexPollTimer);
      indexPollTimer = null;
      toast(`Poll failed: ${escapeHtml(e.message)}`, 'error');
      setStatus(false);
    }
  }, 1500);
}

document.getElementById('index-start').addEventListener('click', async () => {
  const btn = document.getElementById('index-start');
  btn.disabled = true;
  btn.querySelector('.btn-label').textContent = 'Indexing…';
  setStatus(true, 'INDEXING');

  document.getElementById('index-empty').classList.remove('hidden');
  document.getElementById('index-output').classList.add('hidden');

  try {
    await api('POST', '/index');
    pollIndexStatus();
  } catch (e) {
    btn.disabled = false;
    btn.querySelector('.btn-label').textContent = 'Index Drive';
    setStatus(false);
    toast(`Failed: ${escapeHtml(e.message)}`, 'error');
  }
});

async function init() {
  try {
    await loadConfig();
  } catch (e) {
    toast(`Init failed: ${escapeHtml(e.message)}`, 'error');
  }
}

init();
