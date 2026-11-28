'use strict';

const byId = (id) => document.getElementById(id);
const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
const formatNumber = (n) => Number(n || 0).toLocaleString('vi-VN');
const formatBytes = (n) => n >= 1048576
  ? (n / 1048576).toLocaleString('vi-VN', { maximumFractionDigits: 2 }) + ' MB'
  : (n / 1024).toLocaleString('vi-VN', { maximumFractionDigits: 1 }) + ' KB';

const outcomes = {
  nonnegative: {
    title: 'Không phát hiện nội dung tiêu cực',
    detail: 'Bình luận mang sắc thái trung tính, tích cực hoặc không phát hiện phần nào mang cảm xúc tiêu cực.',
    alt: 'Chim xanh xòe cánh.'
  },
  negative: {
    title: 'Có nội dung tiêu cực',
    detail: 'Bình luận chứa ít nhất một phần tiêu cực hoặc thể hiện sắc thái thất vọng, bức xúc, khó chịu, phản đối hay chỉ trích.',
    alt: 'Chim xanh cau mày.'
  }
};
const birdAssets = { nonnegative: 'friendly', negative: 'alert' };
const descriptions = {
  idle: 'Sẵn sàng phân tích',
  ready: 'Sẵn sàng phân tích nội dung',
  work: 'Đang phân tích…',
  sad: 'Không thể xử lý yêu cầu',
  nonnegative: 'Không phát hiện nội dung tiêu cực',
  negative: 'Có nội dung tiêu cực'
};

function appendText(tag, className, content) {
  const el = document.createElement(tag);
  if (className) el.className = className;
  el.textContent = content;
  return el;
}

// ---------- Navigation (5 main areas, no numbers) ----------
const navLinks = Array.from(document.querySelectorAll('.main-nav a[data-nav]'));
function setActiveNav(id) {
  for (const link of navLinks) {
    if (link.dataset.nav === id) link.setAttribute('aria-current', 'location');
    else link.removeAttribute('aria-current');
  }
}
for (const link of document.querySelectorAll('[data-nav], [data-goto]')) {
  link.addEventListener('click', (e) => {
    const targetId = link.dataset.nav || link.dataset.goto;
    const targetEl = byId(targetId);
    if (!targetEl) return;
    e.preventDefault();
    setActiveNav(targetId);
    history.replaceState(null, '', '#' + targetId);
    targetEl.scrollIntoView({ behavior: prefersReducedMotion.matches ? 'auto' : 'smooth', block: 'start' });
  });
}

// ---------- Health & Model Info ----------
async function refreshHealth() {
  const pill = byId('model-state');
  const txt = byId('model-state-text');
  try {
    const res = await fetch('/api/health');
    const data = await res.json();
    const sqlOk = Boolean(data.sql_server?.available);
    if (data.model_present && sqlOk) {
      txt.textContent = 'Hệ thống sẵn sàng';
      pill.dataset.ok = 'true';
      pill.title = 'Mô hình và SQL Server đều sẵn sàng';
    } else if (data.model_present) {
      txt.textContent = 'SQL chưa kết nối';
      pill.dataset.ok = 'false';
      pill.title = data.sql_server?.message || 'Chưa kết nối SQL Server';
    } else {
      txt.textContent = 'Thiếu mô hình';
      pill.dataset.ok = 'false';
    }
  } catch {
    txt.textContent = 'Mất kết nối';
    pill.dataset.ok = 'false';
  }
}
refreshHealth();

// ---------- User Auth (Login / Register / Logout) ----------
const authDialog = byId('auth-dialog');
const authForm = byId('auth-form');
const authTabLogin = byId('auth-tab-login');
const authTabRegister = byId('auth-tab-register');
const authMsg = byId('auth-msg');
let authMode = 'login';
let currentUser = null;

function setAuthMode(mode) {
  authMode = mode;
  const isReg = mode === 'register';
  authTabLogin.setAttribute('aria-selected', String(!isReg));
  authTabRegister.setAttribute('aria-selected', String(isReg));
  byId('auth-displayname-wrap').hidden = !isReg;
  byId('auth-dialog-title').textContent = isReg ? 'Đăng ký tài khoản TextSense' : 'Đăng nhập TextSense';
  byId('auth-submit-btn').textContent = isReg ? 'Tạo tài khoản' : 'Đăng nhập';
  byId('auth-password').autocomplete = isReg ? 'new-password' : 'current-password';
  authMsg.hidden = true;
}

function renderAuthBar(user) {
  currentUser = user || null;
  const openBtn = byId('auth-open-btn');
  const userBox = byId('auth-user-box');
  if (currentUser) {
    openBtn.hidden = true;
    userBox.hidden = false;
    byId('auth-user-name').textContent = currentUser.display_name || currentUser.username;
  } else {
    openBtn.hidden = false;
    userBox.hidden = true;
  }
}

async function refreshAuth() {
  try {
    const res = await fetch('/api/auth/me');
    const data = await res.json().catch(() => ({}));
    renderAuthBar(data.authenticated ? data.user : null);
    const gBtn = byId('auth-google-btn');
    if (gBtn) gBtn.hidden = !data.google_enabled;
  } catch {
    renderAuthBar(null);
  }
}

byId('auth-open-btn').addEventListener('click', () => {
  authForm.reset();
  setAuthMode('login');
  authDialog.showModal();
});
byId('close-auth-dialog').addEventListener('click', () => authDialog.close());
authTabLogin.addEventListener('click', () => setAuthMode('login'));
authTabRegister.addEventListener('click', () => setAuthMode('register'));

authForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  const username = byId('auth-username').value.trim();
  const displayName = byId('auth-displayname').value.trim();
  const password = byId('auth-password').value;
  const btn = byId('auth-submit-btn');
  btn.disabled = true;
  authMsg.hidden = true;
  try {
    const endpoint = authMode === 'register' ? '/api/auth/register' : '/api/auth/login';
    const res = await fetch(endpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, display_name: displayName, password })
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok || !data.user) {
      authMsg.textContent = data.detail || data.message || 'Không thể xác thực tài khoản.';
      authMsg.className = 'report-feedback-msg err';
      authMsg.hidden = false;
      return;
    }
    renderAuthBar(data.user);
    authDialog.close();
    loadHistoryBatches();
    loadHistoryPredictions();
    loadFeedbackList();
    loadStatsFromServer('');
  } catch {
    authMsg.textContent = 'Lỗi kết nối máy chủ.';
    authMsg.className = 'report-feedback-msg err';
    authMsg.hidden = false;
  } finally {
    btn.disabled = false;
  }
});

byId('auth-logout-btn').addEventListener('click', async () => {
  try {
    await fetch('/api/auth/logout', { method: 'POST' });
  } catch {
    // Ignore
  }
  renderAuthBar(null);
  loadHistoryBatches();
  loadHistoryPredictions();
  loadFeedbackList();
  loadStatsFromServer('');
});

refreshAuth();

fetch('/api/model-info').then((r) => (r.ok ? r.json() : null)).then((data) => {
  if (!data) return;
  const setText = (id, val) => {
    const el = byId(id);
    if (el) el.textContent = val;
  };
  const pct = (v) => (Number(v) * 100).toLocaleString('vi-VN', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + '%';
  if (data.accuracy != null) setText('mi-acc', pct(data.accuracy));
  if (data.precision_negative != null) setText('mi-prec', pct(data.precision_negative));
  if (data.recall_negative != null) setText('mi-rec', pct(data.recall_negative));
  if (data.f1_negative != null) setText('mi-f1', pct(data.f1_negative));
  if (data.train_rows) setText('mi-train-rows', formatNumber(data.train_rows));
  if (data.validation_rows) setText('mi-val-rows', formatNumber(data.validation_rows));
  if (data.test_rows) setText('mi-test-rows', formatNumber(data.test_rows));
  const src = data.source_stats || {};
  if (src.unique_trainable_rows) setText('mi-total-rows', formatNumber(src.unique_trainable_rows));
  if (src.source_counts?.['Twitter_Data.csv']) setText('mi-twitter-rows', formatNumber(src.source_counts['Twitter_Data.csv']));
  if (src.source_counts?.['Reddit_Data.csv']) setText('mi-reddit-rows', formatNumber(src.source_counts['Reddit_Data.csv']));
}).catch(() => {});

// ---------- Detail Modal ----------
const detailDialog = byId('detail-dialog');
byId('close-detail-dialog').addEventListener('click', () => detailDialog.close());

function openDetailDialog({ title, labelName, labelCode, timeText, text, sourceInfo }) {
  byId('detail-dialog-title').textContent = title || 'Chi tiết kết quả phân tích';
  const meta = byId('detail-meta');
  meta.replaceChildren();
  const badgeCls = labelCode === 1 ? 'badge badge-neg' : labelCode === 0 ? 'badge badge-nonneg' : 'badge badge-neutral';
  meta.append(appendText('span', badgeCls, labelName || 'Không xác định'));
  if (sourceInfo) meta.append(appendText('span', '', sourceInfo));
  if (timeText) meta.append(appendText('span', '', timeText));
  byId('detail-text').textContent = text || '';
  detailDialog.showModal();
}

// ---------- Section 2: 3 Tabs (Phân tích bình luận | Lịch sử | Báo cáo sai) ----------
const subtabSingle = byId('subtab-single');
const subtabHistory = byId('subtab-history');
const subtabFeedback = byId('subtab-feedback');
const panelSingle = byId('panel-single');
const panelHistory = byId('panel-history');
const panelFeedback = byId('panel-feedback');

function setSection2Tab(tab) {
  subtabSingle.setAttribute('aria-selected', String(tab === 'single'));
  subtabHistory.setAttribute('aria-selected', String(tab === 'history'));
  subtabFeedback.setAttribute('aria-selected', String(tab === 'feedback'));
  panelSingle.hidden = tab !== 'single';
  panelHistory.hidden = tab !== 'history';
  panelFeedback.hidden = tab !== 'feedback';
  if (tab === 'history') {
    loadHistoryBatches();
    loadHistoryPredictions();
  } else if (tab === 'feedback') {
    loadFeedbackList();
  }
}
subtabSingle.addEventListener('click', () => setSection2Tab('single'));
subtabHistory.addEventListener('click', () => setSection2Tab('history'));
subtabFeedback.addEventListener('click', () => setSection2Tab('feedback'));

// ---------- Single Comment Analysis ----------
const form = byId('comment-form');
const input = byId('comment');
const submitBtn = byId('submit');
const retryBtn = byId('retry');
const clearBtn = byId('clear');
const failureBox = byId('failure');
const progressMsg = byId('progress-message');
const resultBox = byId('result');
const resultTitle = byId('result-title');
const mascot = byId('mascot');
const mascotCaption = byId('mascot-caption');
const workspace = byId('workspace');
const TEXT_LIMIT = 2000;
let revision = 0;
let activeController = null;
let lastResult = null;
let resultOrigin = 'single';
let resultAnimation = 0;

function setState(state) {
  workspace.dataset.state = state;
  mascot.src = 'media/' + (birdAssets[state] || state) + '.webp?v=mascot';
  mascot.alt = descriptions[state] || outcomes[state]?.alt || '';
  if (mascotCaption) mascotCaption.textContent = descriptions[state] || '';
}

function renderSentenceBreakdown(analysis) {
  const section = byId('sentence-breakdown');
  const list = byId('sentence-breakdown-list');
  const summaryEl = byId('result-sentence-summary');
  section.hidden = true;
  if (summaryEl) {
    summaryEl.hidden = true;
    summaryEl.textContent = '';
  }
  list.replaceChildren();
  if (!analysis?.available || !Array.isArray(analysis.sentences)) return;

  const negativeCount = Number(analysis.negative_parts);
  const totalParts = Number(analysis.total_parts);
  if (!Number.isSafeInteger(negativeCount) || !Number.isSafeInteger(totalParts) ||
      totalParts < 2 || negativeCount < 1 || negativeCount > totalParts) return;

  if (summaryEl) {
    summaryEl.textContent = `Số câu/phần có nội dung tiêu cực: ${negativeCount} / ${totalParts}`;
    summaryEl.hidden = false;
  }

  byId('sentence-breakdown-title').textContent = analysis.mixed
    ? 'Phân tích từng câu / vế (có sắc thái hỗn hợp)'
    : 'Phân tích từng câu / vế';
  byId('sentence-breakdown-count').textContent =
    `Phát hiện ${negativeCount} / ${totalParts} câu (phần) có nội dung tiêu cực.`;

  for (const [index, item] of analysis.sentences.entries()) {
    const row = document.createElement('li');
    row.className = 'sentence-item' + (item.label === 'negative' ? ' sentence-item-negative' : '');
    const header = document.createElement('div');
    header.className = 'sentence-item-header';
    header.append(appendText('span', 'sentence-number', 'Phần ' + (index + 1)));
    header.append(appendText(
      'strong',
      'sentence-label ' + (item.label === 'negative' ? 'negative' : 'nonnegative'),
      item.label === 'negative' ? 'Có nội dung tiêu cực' : 'Không phát hiện tiêu cực'
    ));
    row.append(header, appendText('p', '', item.text || ''));
    list.append(row);
  }
  section.hidden = list.childElementCount < 2;
}

function showClassification(payload, origin = 'single', rowNumber = 0) {
  const classification = outcomes[payload.label];
  if (!classification) throw new Error('Nhãn dự đoán không hợp lệ');
  resultOrigin = origin;
  lastResult = { ...payload, rowNumber };
  byId('report').hidden = false;
  byId('result-label').textContent = origin === 'batch'
    ? 'Kết quả phân tích hàng loạt · STT ' + formatNumber(rowNumber)
    : 'Kết quả phân loại';
  byId('back-input').hidden = origin === 'batch';
  byId('back-batch').hidden = origin !== 'batch';
  byId('new-comment').hidden = origin === 'batch';
  byId('batch-detail-nav').hidden = origin !== 'batch';
  resultTitle.textContent = classification.title;
  const confEl = byId('result-confidence');
  if (confEl) {
    if (typeof payload.confidence === 'number') {
      confEl.textContent = 'Điểm quyết định: ' + (payload.confidence * 100).toFixed(1) + '%';
      confEl.hidden = false;
    } else {
      confEl.textContent = '';
      confEl.hidden = true;
    }
  }
  byId('result-detail').textContent = classification.detail;
  const ts = payload.analyzed_at ? new Date(payload.analyzed_at) : new Date();
  byId('result-timestamp').textContent = ts.toLocaleString('vi-VN');
  renderSentenceBreakdown(payload.sentence_analysis);
  byId('result-quote').textContent = payload.text;
  byId('history-warning').hidden = origin !== 'single' || payload.history_saved !== false;
  byId('entry').hidden = true;
  resultBox.hidden = false;
  const anim = ++resultAnimation;
  setState('work');
  window.setTimeout(() => {
    if (anim === resultAnimation) setState(payload.label);
  }, prefersReducedMotion.matches ? 0 : 180);
  resultTitle.focus({ preventScroll: true });
  if (origin === 'batch') {
    setSection2Tab('single');
    byId('batch-detail-position').textContent = formatNumber(rowNumber) + ' / ' + formatNumber(batchState?.filteredRows.length || 0);
    const idx = batchState?.filteredRows.findIndex((r) => r.rowNumber === rowNumber) ?? -1;
    byId('batch-detail-prev').disabled = idx <= 0;
    byId('batch-detail-next').disabled = idx < 0 || idx >= (batchState?.filteredRows.length || 0) - 1;
    byId('phan-tich').scrollIntoView({ behavior: prefersReducedMotion.matches ? 'auto' : 'smooth', block: 'start' });
  }
}

function updateInput() {
  resultAnimation += 1;
  revision += 1;
  activeController?.abort();
  activeController = null;
  failureBox.hidden = true;
  retryBtn.hidden = true;
  submitBtn.hidden = false;
  submitBtn.textContent = 'Phân tích';
  progressMsg.textContent = '';
  const trimmed = input.value.trim();
  const len = Array.from(trimmed).length;
  const tooLong = len > TEXT_LIMIT;
  const countEl = byId('count');
  countEl.textContent = len.toLocaleString('vi-VN') + ' / 2.000 ký tự';
  countEl.dataset.invalid = String(tooLong);
  input.setAttribute('aria-invalid', String(tooLong));
  const errEl = byId('input-error');
  errEl.hidden = !tooLong;
  errEl.textContent = tooLong ? 'Nội dung vượt 2.000 ký tự và chưa được gửi. Hãy rút gọn nội dung để tiếp tục.' : '';
  submitBtn.disabled = tooLong || !trimmed;
  clearBtn.hidden = !input.value;
  byId('entry').hidden = false;
  resultBox.hidden = true;
  renderSentenceBreakdown(null);
  byId('history-warning').hidden = true;
  lastResult = null;
  setState(trimmed ? 'ready' : 'idle');
}

function showError(message, detail, retryable = false) {
  setState('sad');
  byId('failure-title').textContent = message;
  byId('failure-detail').textContent = detail || '';
  failureBox.hidden = false;
  retryBtn.hidden = !retryable;
  submitBtn.hidden = retryable;
  submitBtn.disabled = false;
  submitBtn.textContent = 'Phân tích';
  progressMsg.textContent = '';
}

function returnToInput(erase) {
  resultOrigin = 'single';
  if (erase) input.value = '';
  updateInput();
  input.focus();
}

input.addEventListener('input', updateInput);
clearBtn.addEventListener('click', () => returnToInput(true));
byId('new-comment').addEventListener('click', () => returnToInput(true));
byId('back-input').addEventListener('click', () => returnToInput(false));
byId('back-batch').addEventListener('click', () => {
  byId('hang-loat').scrollIntoView({ behavior: prefersReducedMotion.matches ? 'auto' : 'smooth', block: 'start' });
});
retryBtn.addEventListener('click', () => form.requestSubmit());

form.addEventListener('submit', async (event) => {
  event.preventDefault();
  const value = input.value.trim();
  if (!value || submitBtn.disabled) return;
  const req = ++revision;
  activeController = new AbortController();
  failureBox.hidden = true;
  retryBtn.hidden = true;
  submitBtn.hidden = false;
  submitBtn.disabled = true;
  submitBtn.textContent = 'Đang phân tích…';
  progressMsg.textContent = 'Đang phân tích nội dung.';
  setState('work');

  try {
    const response = await fetch('/api/analyze', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ input: value }),
      signal: activeController.signal
    });
    const payload = await response.json().catch(() => null);
    if (req !== revision) return;
    if (!response.ok || !payload || !Object.hasOwn(outcomes, payload.label)) {
      showError(
        payload?.message || 'Không thể phân tích bình luận',
        payload?.detail || 'Vui lòng kiểm tra nội dung hoặc kết nối máy chủ.',
        payload?.retryable ?? true
      );
      return;
    }
    showClassification(payload, 'single');
    progressMsg.textContent = '';
  } catch (err) {
    if (req === revision && err.name !== 'AbortError') {
      showError('Không kết nối được máy chủ TextSense', 'Hãy đảm bảo serve_textsense.py đang chạy.', true);
    }
  } finally {
    if (req === revision) activeController = null;
  }
});

updateInput();

// ---------- Report Wrong Result Dialog ----------
const reportDialog = byId('report-dialog');
const reportForm = byId('report-form');
const reportMsg = byId('report-feedback-msg');
let reportContext = null;

function openReportDialog(ctx) {
  reportContext = ctx;
  reportForm.reset();
  reportMsg.hidden = true;
  reportMsg.textContent = '';
  reportMsg.className = 'report-feedback-msg';
  byId('report-text-preview').textContent = ctx.text || '';
  byId('report-model-label').textContent = ctx.predictionTitle || '';
  byId('report-submit-btn').disabled = false;
  reportDialog.showModal();
}

byId('report').addEventListener('click', () => {
  if (!lastResult) return;
  openReportDialog({
    source: resultOrigin === 'batch' ? 'Tệp dữ liệu' : 'Bình luận riêng lẻ',
    text: lastResult.text,
    predictionTitle: outcomes[lastResult.label]?.title || lastResult.label,
    batchId: resultOrigin === 'batch' ? batchState?.batchId : lastResult.batch_id,
    rowNumber: resultOrigin === 'batch' ? lastResult.rowNumber : 1,
    onSaved: () => {
      if (resultOrigin === 'batch' && batchState && lastResult.rowNumber) {
        batchState.reportedRows.add(lastResult.rowNumber);
        renderBatchPage(batchState.page);
      }
    }
  });
});

byId('cancel-report').addEventListener('click', () => reportDialog.close());

reportForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  if (!reportContext) return;
  const suggestedLabel = byId('report-label').value;
  const reasonCategory = byId('report-reason-cat').value;
  const note = byId('report-reason').value.trim();
  if (!suggestedLabel) return;

  const submitButton = byId('report-submit-btn');
  submitButton.disabled = true;
  submitButton.textContent = 'Đang gửi…';
  reportMsg.hidden = true;

  try {
    const res = await fetch('/api/feedback', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        source: reportContext.source,
        prediction: reportContext.predictionTitle,
        suggested_label: suggestedLabel,
        reason_category: reasonCategory,
        note,
        text: reportContext.text,
        batch_id: reportContext.batchId || null,
        row_number: reportContext.rowNumber || null
      })
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok || !data.feedback_saved) {
      reportMsg.textContent = data.message || 'Không lưu được báo cáo vào SQL Server. Vui lòng kiểm tra kết nối.';
      reportMsg.className = 'report-feedback-msg err';
      reportMsg.hidden = false;
      return;
    }
    reportMsg.textContent = 'Đã gửi báo cáo (Trạng thái: Chờ xem xét).';
    reportMsg.className = 'report-feedback-msg ok';
    reportMsg.hidden = false;
    if (typeof reportContext.onSaved === 'function') reportContext.onSaved();
    window.setTimeout(() => reportDialog.close(), 900);
  } catch {
    reportMsg.textContent = 'Lỗi kết nối máy chủ. Chưa gửi được báo cáo.';
    reportMsg.className = 'report-feedback-msg err';
    reportMsg.hidden = false;
  } finally {
    submitButton.disabled = false;
    submitButton.textContent = 'Gửi báo cáo';
  }
});

// ---------- History & Feedback Tabs ----------
let histPage = 1;
let fbPage = 1;

async function loadHistoryBatches() {
  const histSel = byId('hist-batch-filter');
  const statsSel = byId('stats-batch-select');
  try {
    const res = await fetch('/api/history/batches?limit=50');
    const data = await res.json().catch(() => ({}));
    if (!res.ok || !data.available) {
      statsSel.replaceChildren(new Option('Chưa kết nối SQL Server để xem tệp đã lưu', ''));
      return;
    }
    const prevHist = histSel.value;
    const prevStats = statsSel.value;

    histSel.replaceChildren(new Option('Tất cả phiên phân tích', ''));
    const batches = (data.batches || []).filter((b) => b.source_name !== 'manual_input');
    statsSel.replaceChildren(new Option(
      batches.length ? 'Chọn tập dữ liệu đã lưu…' : 'Chưa có tệp nào được lưu trong SQL Server',
      ''
    ));

    for (const b of data.batches || []) {
      const label = `Phiên #${b.id} · ${b.analysis_type} · ${b.source_name} (${formatNumber(b.row_count)} dòng)`;
      histSel.append(new Option(label, String(b.id)));
      if (b.source_name !== 'manual_input') {
        statsSel.append(new Option(label, String(b.id)));
      }
    }
    if (prevHist) histSel.value = prevHist;
    if (prevStats) statsSel.value = prevStats;
  } catch {
    statsSel.replaceChildren(new Option('Không kết nối được máy chủ', ''));
  }
}

async function loadHistoryPredictions() {
  const statusEl = byId('hist-status');
  const tbody = byId('hist-table-body');
  statusEl.textContent = 'Đang tải lịch sử từ SQL Server…';
  const params = new URLSearchParams({
    page: String(histPage),
    page_size: '15',
    search: byId('hist-search').value.trim(),
    label: byId('hist-label-filter').value,
    batch_id: byId('hist-batch-filter').value,
    date_from: byId('hist-date-from').value,
    date_to: byId('hist-date-to').value
  });
  try {
    const res = await fetch('/api/history/predictions?' + params.toString());
    const data = await res.json().catch(() => ({}));
    tbody.replaceChildren();
    if (!res.ok || !data.available) {
      statusEl.textContent = data.error
        ? `Chưa kết nối được SQL Server (${data.error})`
        : 'Chưa kết nối được SQL Server để đọc lịch sử. Hãy đặt biến TEXTSENSE_SQLSERVER_CONNECTION_STRING trước khi chạy serve_textsense.py.';
      return;
    }
    const items = data.items || [];
    statusEl.textContent = `Hiển thị ${items.length} / ${formatNumber(data.total)} bản ghi.`;
    for (const row of items) {
      const tr = document.createElement('tr');
      const snippet = (row.input_text || '').length > 140 ? row.input_text.slice(0, 140) + '…' : (row.input_text || '');
      tr.append(appendText('td', '', snippet));

      const tdBadge = document.createElement('td');
      const cls = row.predicted_label === 1 ? 'badge badge-neg' : row.predicted_label === 0 ? 'badge badge-nonneg' : 'badge badge-neutral';
      tdBadge.append(appendText('span', cls, row.label_name || row.status || 'Không xác định'));
      tr.append(tdBadge);

      const timeStr = row.created_utc ? new Date(row.created_utc).toLocaleString('vi-VN') : '—';
      tr.append(appendText('td', '', timeStr));

      const tdAct = document.createElement('td');
      const viewBtn = appendText('button', 'text-button', 'Xem chi tiết');
      viewBtn.type = 'button';
      viewBtn.addEventListener('click', () => openDetailDialog({
        title: `Lịch sử phân tích #${row.prediction_id}`,
        labelName: row.label_name || row.status,
        labelCode: row.predicted_label,
        timeText: timeStr,
        sourceInfo: `${row.analysis_type} · Phiên #${row.batch_id}`,
        text: row.input_text
      }));
      tdAct.append(viewBtn);
      tr.append(tdAct);
      tbody.append(tr);
    }
    const maxPage = Math.max(1, Math.ceil((data.total || 0) / 15));
    byId('hist-page-info').textContent = `Trang ${histPage} / ${maxPage}`;
    byId('hist-prev').disabled = histPage <= 1;
    byId('hist-next').disabled = histPage >= maxPage;
  } catch {
    statusEl.textContent = 'Không kết nối được máy chủ.';
  }
}

byId('hist-refresh').addEventListener('click', () => { histPage = 1; loadHistoryPredictions(); });
byId('hist-label-filter').addEventListener('change', () => { histPage = 1; loadHistoryPredictions(); });
byId('hist-batch-filter').addEventListener('change', () => { histPage = 1; loadHistoryPredictions(); });
byId('hist-search').addEventListener('keydown', (e) => { if (e.key === 'Enter') { histPage = 1; loadHistoryPredictions(); } });
byId('hist-prev').addEventListener('click', () => { if (histPage > 1) { histPage--; loadHistoryPredictions(); } });
byId('hist-next').addEventListener('click', () => { histPage++; loadHistoryPredictions(); });

async function loadFeedbackList() {
  const statusEl = byId('fb-status');
  const tbody = byId('fb-table-body');
  statusEl.textContent = 'Đang tải danh sách báo cáo sai…';
  const params = new URLSearchParams({
    page: String(fbPage),
    page_size: '15',
    status: byId('fb-status-filter').value,
    reason: byId('fb-reason-filter').value,
    search: byId('fb-search').value.trim()
  });
  try {
    const res = await fetch('/api/feedback?' + params.toString());
    const data = await res.json().catch(() => ({}));
    tbody.replaceChildren();
    if (!res.ok || !data.available) {
      statusEl.textContent = data.error
        ? `Chưa kết nối được SQL Server (${data.error})`
        : 'Chưa kết nối được SQL Server để đọc phản hồi.';
      return;
    }
    const counts = data.counts || {};
    byId('fb-count-pending').textContent = formatNumber(counts['Chờ xem xét'] || 0);
    byId('fb-count-verified').textContent = formatNumber(counts['Đã xác minh'] || 0);
    byId('fb-count-rejected').textContent = formatNumber(counts['Không chấp nhận'] || 0);

    const items = data.items || [];
    statusEl.textContent = `Tổng ${formatNumber(data.total)} báo cáo.`;
    for (const item of items) {
      const tr = document.createElement('tr');
      tr.append(appendText('td', '', '#' + item.feedback_id));
      const loc = item.batch_id ? `${item.source_name} (Phiên #${item.batch_id}${item.row_number ? ' · STT ' + item.row_number : ''})` : item.source_name;
      tr.append(appendText('td', '', loc));
      tr.append(appendText('td', '', (item.input_text || '(không đính kèm)').slice(0, 120)));
      tr.append(appendText('td', '', item.model_prediction || '—'));
      tr.append(appendText('td', '', item.suggested_label || '—'));
      tr.append(appendText('td', '', (item.reason_category || '') + (item.user_note ? ' — ' + item.user_note : '')));
      tr.append(appendText('td', '', item.review_status || 'Chờ xem xét'));

      const tdAct = document.createElement('td');
      const sel = document.createElement('select');
      for (const st of ['Chờ xem xét', 'Đã xác minh', 'Không chấp nhận']) sel.append(new Option(st, st));
      sel.value = item.review_status || 'Chờ xem xét';
      sel.addEventListener('change', async () => {
        try {
          const upd = await fetch('/api/feedback/status', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ feedback_id: item.feedback_id, review_status: sel.value })
          });
          if (!upd.ok) alert('Không thể cập nhật trạng thái trên SQL Server.');
          loadFeedbackList();
        } catch {
          alert('Lỗi kết nối khi cập nhật trạng thái.');
        }
      });
      tdAct.append(sel);
      tr.append(tdAct);
      tbody.append(tr);
    }
    const maxPage = Math.max(1, Math.ceil((data.total || 0) / 15));
    byId('fb-page-info').textContent = `Trang ${fbPage} / ${maxPage}`;
    byId('fb-prev').disabled = fbPage <= 1;
    byId('fb-next').disabled = fbPage >= maxPage;
  } catch {
    statusEl.textContent = 'Không kết nối được máy chủ.';
  }
}

byId('fb-refresh').addEventListener('click', () => { fbPage = 1; loadFeedbackList(); });
byId('fb-status-filter').addEventListener('change', () => { fbPage = 1; loadFeedbackList(); });
byId('fb-reason-filter').addEventListener('change', () => { fbPage = 1; loadFeedbackList(); });
byId('fb-search').addEventListener('keydown', (e) => { if (e.key === 'Enter') { fbPage = 1; loadFeedbackList(); } });
byId('fb-prev').addEventListener('click', () => { if (fbPage > 1) { fbPage--; loadFeedbackList(); } });
byId('fb-next').addEventListener('click', () => { fbPage++; loadFeedbackList(); });

// ---------- Section 3: Batch Analysis ----------
const csvFile = byId('csv-file');
const csvDropzone = byId('csv-dropzone');
const csvColumn = byId('csv-column');
const sheetSelect = byId('xlsx-sheet');
const batchSubmit = byId('batch-submit');
const batchStatus = byId('batch-status');
const batchResult = byId('batch-result');
const csvConfig = byId('csv-config');
const batchProgress = byId('batch-progress');
const confirmBox = byId('batch-confirm-box');

let maxCsvBytes = 100 * 1024 * 1024;
let maxCsvRows = 300000;
let selectedCsv = null;
let columnsMeta = null;
let csvRevision = 0;
let csvController = null;
let batchController = null;
let resultCsvBlob = null;
let resultDownloadUrl = null;
let batchState = null;
const BATCH_PAGE_SIZE = 10;

function setBatchMascot(state, title, note) {
  const img = byId('batch-mascot');
  if (img) img.src = `media/${state}.webp?v=mascot`;
  if (title) byId('batch-mascot-title').textContent = title;
  if (note) byId('batch-mascot-note').textContent = note;
}

function setPipelineStep(activeIds) {
  for (const id of ['pipe-upload', 'pipe-check', 'pipe-confirm', 'pipe-run', 'pipe-result', 'pipe-export']) {
    byId(id)?.classList.toggle('active', activeIds.includes(id));
  }
}

fetch('/api/config').then((r) => (r.ok ? r.json() : null)).then((data) => {
  if (!data) return;
  if (data.max_csv_bytes > 0) maxCsvBytes = data.max_csv_bytes;
  if (data.max_csv_rows > 0) maxCsvRows = data.max_csv_rows;
  byId('csv-limit-label').textContent = formatBytes(maxCsvBytes);
  byId('csv-rows-label').textContent = formatNumber(maxCsvRows) + ' dòng';
}).catch(() => {});

function decodeSummaryHeader(value) {
  if (!value) return null;
  try {
    const normalized = value.replace(/-/g, '+').replace(/_/g, '/');
    const binary = atob(normalized + '='.repeat((4 - normalized.length % 4) % 4));
    const bytes = Uint8Array.from(binary, (c) => c.charCodeAt(0));
    return JSON.parse(new TextDecoder('utf-8').decode(bytes));
  } catch {
    return null;
  }
}

function setBatchStatus(message, kind = '') {
  batchStatus.textContent = message;
  batchStatus.dataset.error = String(kind === 'error');
  batchStatus.dataset.success = String(kind === 'success');
  batchStatus.dataset.warning = String(kind === 'warning');
}

function setBatchBusy(busy, message = '') {
  batchProgress.hidden = !busy;
  byId('batch-progress-label').textContent = message;
  csvFile.disabled = busy;
  sheetSelect.disabled = busy || byId('sheet-wrap').hidden;
  csvColumn.disabled = busy || !selectedCsv || csvConfig.hidden;
  batchSubmit.disabled = busy || !selectedCsv || csvConfig.hidden || !csvColumn.value;
}

function updateConfirmationBox() {
  const col = csvColumn.value;
  if (!selectedCsv || !columnsMeta || !col) {
    confirmBox.hidden = true;
    return;
  }
  const colStat = columnsMeta.column_stats?.[col] || { valid_rows: columnsMeta.rows, invalid_rows: 0 };
  byId('confirm-filename').textContent = selectedCsv.name;
  byId('confirm-sheet').textContent = columnsMeta.selected_sheet || 'Mặc định (CSV)';
  byId('confirm-column').textContent = col;
  byId('confirm-total').textContent = formatNumber(columnsMeta.rows) + ' dòng';
  byId('confirm-valid').textContent = formatNumber(colStat.valid_rows) + ' dòng';
  byId('confirm-empty').textContent = formatNumber(colStat.invalid_rows ?? colStat.empty_rows ?? 0) + ' dòng';
  confirmBox.hidden = false;
  setPipelineStep(['pipe-upload', 'pipe-check', 'pipe-confirm']);
}

function displayPreview() {
  const col = csvColumn.value;
  const panel = byId('csv-preview');
  const list = byId('csv-preview-list');
  list.replaceChildren();
  const rows = columnsMeta?.preview_rows || [];
  if (!col || !rows.length) { panel.hidden = true; return; }
  for (const sample of rows) {
    const li = document.createElement('li');
    li.textContent = sample[col]?.trim() || '(trống)';
    list.append(li);
  }
  panel.hidden = false;
}

function clearBatchResult() {
  batchState = null;
  batchResult.hidden = true;
  byId('batch-browse').hidden = true;
  byId('batch-table-body').replaceChildren();
  if (resultDownloadUrl) URL.revokeObjectURL(resultDownloadUrl);
  resultDownloadUrl = null;
  resultCsvBlob = null;
  byId('batch-download-xlsx').disabled = true;
}

csvColumn.addEventListener('change', () => {
  displayPreview();
  updateConfirmationBox();
  clearBatchResult();
  batchSubmit.disabled = !selectedCsv || csvConfig.hidden || !csvColumn.value;
});

async function selectCsv(file, requestedSheet = '') {
  const rev = ++csvRevision;
  csvController?.abort();
  batchController?.abort();
  csvController = new AbortController();
  selectedCsv = null;
  columnsMeta = null;
  csvConfig.hidden = true;
  confirmBox.hidden = true;
  csvColumn.replaceChildren(new Option('Tự động nhận diện', ''));
  csvColumn.disabled = true;
  batchSubmit.disabled = true;
  byId('csv-preview').hidden = true;
  byId('sheet-wrap').hidden = true;
  sheetSelect.replaceChildren();
  byId('selected-file').hidden = true;
  setBatchBusy(false);
  clearBatchResult();
  setPipelineStep(['pipe-upload']);

  if (!file) {
    setBatchStatus('Chưa có tệp được chọn.');
    setBatchMascot('idle', 'Sẵn sàng nhận tệp', 'Tải lên tệp CSV hoặc XLSX chứa bình luận tiếng Anh để bắt đầu.');
    return;
  }
  if (!/\.(csv|xlsx)$/i.test(file.name)) {
    setBatchStatus('Định dạng không hợp lệ. Chỉ hỗ trợ tệp CSV hoặc Excel (.xlsx).', 'error');
    setBatchMascot('sad', 'Định dạng chưa đúng', 'Hãy chọn tệp có đuôi .csv hoặc .xlsx.');
    return;
  }
  if (file.size === 0) {
    setBatchStatus('Tệp đang trống.', 'error');
    setBatchMascot('sad', 'Tệp trống', 'Tệp tải lên không có dữ liệu.');
    return;
  }
  if (file.size > maxCsvBytes) {
    setBatchStatus('Tệp vượt giới hạn ' + formatBytes(maxCsvBytes) + '.', 'error');
    setBatchMascot('sad', 'Tệp quá lớn', 'Vui lòng chọn tệp dưới ' + formatBytes(maxCsvBytes) + '.');
    return;
  }

  selectedCsv = file;
  byId('selected-file').hidden = false;
  byId('file-name').textContent = file.name;
  byId('file-metadata').textContent = formatBytes(file.size) + ' · đang kiểm tra…';
  setBatchBusy(true, 'Đang kiểm tra cấu trúc tệp và cột dữ liệu…');
  setBatchMascot('ready', 'Đang nhận và kiểm tra tệp…', 'Đang đọc tiêu đề cột và thống kê dòng hợp lệ.');

  try {
    const url = '/api/columns?filename=' + encodeURIComponent(file.name) + (requestedSheet ? '&sheet=' + encodeURIComponent(requestedSheet) : '');
    const res = await fetch(url, { method: 'POST', headers: { 'content-type': 'application/octet-stream' }, body: file, signal: csvController.signal });
    const data = await res.json().catch(() => null);
    if (rev !== csvRevision) return;
    if (!res.ok || !data || !Array.isArray(data.columns)) {
      setBatchStatus([data?.message || 'Không đọc được tệp.', data?.detail].filter(Boolean).join(' '), 'error');
      setBatchMascot('sad', 'Không đọc được tệp', data?.message || 'Vui lòng kiểm tra định dạng tệp.');
      return;
    }
    columnsMeta = data;
    const sheets = Array.isArray(data.sheets) ? data.sheets : [];
    if (sheets.length > 1) {
      for (const name of sheets) sheetSelect.append(new Option(name, name));
      sheetSelect.value = data.selected_sheet || sheets[0];
      byId('sheet-wrap').hidden = false;
    }
    csvColumn.replaceChildren();
    const initOpt = new Option('Chọn cột bình luận', '');
    initOpt.disabled = true;
    csvColumn.append(initOpt);
    const nonText = new Set([...(data.label_columns || []), ...(data.index_columns || []), ...(data.link_columns || [])]);
    for (const col of data.columns) {
      const opt = new Option(nonText.has(col) ? `${col} (không phải cột nội dung)` : col, col);
      opt.disabled = nonText.has(col);
      csvColumn.append(opt);
    }
    csvColumn.value = data.suggested_column && data.columns.includes(data.suggested_column) ? data.suggested_column : '';
    csvConfig.hidden = false;
    setPipelineStep(['pipe-upload', 'pipe-check']);
    byId('file-metadata').textContent = `${formatBytes(file.size)} · ${formatNumber(data.rows)} dòng · ${data.columns.length} cột`;
    setBatchStatus(data.suggested_column
      ? 'Đã kiểm tra xong. Xác nhận thông tin cột và nhấn bắt đầu phân tích.'
      : 'Vui lòng chọn cột chứa bình luận để tiếp tục.', data.suggested_column ? 'success' : 'warning');
    setBatchMascot('ready', 'Tệp đã sẵn sàng', `Đã đọc ${formatNumber(data.rows)} dòng. Hãy xác nhận cột để phân tích.`);
    displayPreview();
    updateConfirmationBox();
  } catch (err) {
    if (rev === csvRevision && err.name !== 'AbortError') {
      setBatchStatus('Không kết nối được máy chủ TextSense.', 'error');
      setBatchMascot('sad', 'Lỗi kết nối', 'Không thể liên hệ máy chủ cục bộ.');
    }
  } finally {
    if (rev === csvRevision) setBatchBusy(false);
  }
}

sheetSelect.addEventListener('change', () => { if (selectedCsv && sheetSelect.value) selectCsv(selectedCsv, sheetSelect.value); });
csvFile.addEventListener('change', () => selectCsv(csvFile.files?.[0] || null));
byId('file-remove').addEventListener('click', () => { csvFile.value = ''; selectCsv(null); });
for (const ev of ['dragenter', 'dragover']) csvDropzone.addEventListener(ev, (e) => { e.preventDefault(); csvDropzone.classList.add('dragover'); });
for (const ev of ['dragleave', 'drop']) csvDropzone.addEventListener(ev, (e) => { e.preventDefault(); csvDropzone.classList.remove('dragover'); });
csvDropzone.addEventListener('drop', (e) => { const f = e.dataTransfer?.files?.[0]; if (f) selectCsv(f); });

batchSubmit.addEventListener('click', async () => {
  const file = selectedCsv;
  const col = csvColumn.value;
  if (!file || !col || csvConfig.hidden || batchSubmit.disabled) return;
  const rev = csvRevision;
  batchController = new AbortController();
  clearBatchResult();
  setBatchStatus('Đang phân tích dữ liệu…');
  setBatchBusy(true, 'Đang phân loại từng bình luận bằng mô hình…');
  setPipelineStep(['pipe-upload', 'pipe-check', 'pipe-confirm', 'pipe-run']);
  setBatchMascot('work', 'Đang phân tích…', 'Vui lòng giữ trang mở trong khi hệ thống xử lý.');

  try {
    const url = '/api/batch?column=' + encodeURIComponent(col) + '&filename=' + encodeURIComponent(file.name) +
      (sheetSelect.value && !byId('sheet-wrap').hidden ? '&sheet=' + encodeURIComponent(sheetSelect.value) : '');
    const res = await fetch(url, { method: 'POST', headers: { 'content-type': 'application/octet-stream' }, body: file, signal: batchController.signal });
    if (rev !== csvRevision) return;
    if (!res.ok) {
      const err = await res.json().catch(() => null);
      setBatchStatus([err?.message || 'Không phân tích được tệp.', err?.detail].filter(Boolean).join(' '), 'error');
      setBatchMascot('sad', 'Phân tích thất bại', err?.message || 'Vui lòng kiểm tra lại dữ liệu.');
      return;
    }

    const total = Number(res.headers.get('X-Total-Rows')) || 0;
    const valid = Number(res.headers.get('X-Valid-Rows')) || 0;
    const negative = Number(res.headers.get('X-Negative-Rows')) || 0;
    const nonnegative = Number(res.headers.get('X-Nonnegative-Rows')) || 0;
    const invalid = Number(res.headers.get('X-Invalid-Rows')) || 0;
    const historySaved = res.headers.get('X-History-Saved') === 'true';
    const batchIdHeader = res.headers.get('X-Batch-Id');
    const batchId = batchIdHeader && /^\d+$/.test(batchIdHeader) ? Number(batchIdHeader) : null;
    const summary = decodeSummaryHeader(res.headers.get('X-TextSense-Summary'));

    const blob = await res.blob();
    if (rev !== csvRevision) return;
    resultCsvBlob = blob;
    resultDownloadUrl = URL.createObjectURL(blob);

    const originalName = file.name.replace(/\.(csv|xlsx)$/i, '').replace(/[^\p{L}\p{N}_-]/gu, '_').slice(0, 55) || 'binh_luan';
    byId('batch-download').href = resultDownloadUrl;
    byId('batch-download').download = `TextSense_${originalName}_ket_qua.csv`;
    const xlsxBtn = byId('batch-download-xlsx');
    xlsxBtn.disabled = false;
    xlsxBtn.dataset.filename = `TextSense_${originalName}_ket_qua.xlsx`;

    byId('batch-kpi-total').textContent = formatNumber(total);
    byId('batch-kpi-valid').textContent = formatNumber(valid);
    byId('batch-kpi-success').textContent = formatNumber(valid);
    byId('batch-kpi-invalid').textContent = formatNumber(invalid);
    byId('batch-kpi-neg').textContent = formatNumber(negative);
    byId('batch-kpi-nonneg').textContent = formatNumber(nonnegative);
    byId('batch-facts').textContent = `${file.name} · Cột "${col}" · ${formatNumber(valid)}/${formatNumber(total)} dòng hợp lệ`;

    batchResult.hidden = false;
    setPipelineStep(['pipe-upload', 'pipe-check', 'pipe-confirm', 'pipe-run', 'pipe-result', 'pipe-export']);
    setBatchMascot('friendly', 'Hoàn thành phân tích', `Đã phân loại thành công ${formatNumber(valid)} bình luận.`);
    setBatchStatus(
      `Hoàn thành ${formatNumber(valid)}/${formatNumber(total)} dòng.` +
      (historySaved ? ` Đã lưu lịch sử vào SQL Server (Phiên #${batchId}).` : ' Lưu ý: Chưa lưu được vào SQL Server.'),
      historySaved ? 'success' : 'warning'
    );

    if (summary) {
      renderStatsDashboard(summary, `${file.name} (Cột: ${col})`);
      loadHistoryBatches();
    }

    const index = await window.TextSenseCsv.indexBlob(blob);
    if (rev !== csvRevision) return;
    const columns = await window.TextSenseCsv.readRow(blob, index, 0);
    const textColIdx = columns.indexOf(col);
    const resultColIdx = columns.length - 1;
    const allRows = [];
    for (let r = 1; r <= index.rowCount; r++) {
      const rec = await window.TextSenseCsv.readRow(blob, index, r);
      const codeStr = (rec[resultColIdx] || '').trim();
      const labelKey = codeStr === '1' ? 'negative' : codeStr === '0' ? 'nonnegative' : 'invalid';
      allRows.push({ rowNumber: r, text: rec[textColIdx] || '', codeStr, labelKey });
    }
    batchState = { batchId, allRows, filteredRows: [...allRows], page: 0, reportedRows: new Set() };
    byId('batch-browse').hidden = false;
    byId('batch-jump-input').max = String(index.rowCount);
    applyBatchFilters();
  } catch (err) {
    if (rev === csvRevision && err.name !== 'AbortError') {
      setBatchStatus('Lỗi khi xử lý tệp: ' + (err.message || 'Vui lòng thử lại.'), 'error');
      setBatchMascot('sad', 'Có lỗi xảy ra', err.message || 'Không hoàn tất được phân tích.');
    }
  } finally {
    if (rev === csvRevision) setBatchBusy(false);
  }
});

function applyBatchFilters() {
  if (!batchState) return;
  const query = byId('batch-search-input').value.trim().toLowerCase();
  const labelFilter = byId('batch-label-filter').value;
  const sortMode = byId('batch-sort-select').value;

  let rows = batchState.allRows.filter((item) => {
    if (labelFilter === '1' && item.codeStr !== '1') return false;
    if (labelFilter === '0' && item.codeStr !== '0') return false;
    if (labelFilter === 'invalid' && item.labelKey !== 'invalid') return false;
    if (query && !item.text.toLowerCase().includes(query)) return false;
    return true;
  });

  if (sortMode === 'row-desc') rows.sort((a, b) => b.rowNumber - a.rowNumber);
  else if (sortMode === 'label-neg') rows.sort((a, b) => (b.codeStr === '1' ? 1 : 0) - (a.codeStr === '1' ? 1 : 0) || a.rowNumber - b.rowNumber);
  else if (sortMode === 'label-nonneg') rows.sort((a, b) => (b.codeStr === '0' ? 1 : 0) - (a.codeStr === '0' ? 1 : 0) || a.rowNumber - b.rowNumber);
  else rows.sort((a, b) => a.rowNumber - b.rowNumber);

  batchState.filteredRows = rows;
  renderBatchPage(0);
}

function renderBatchPage(page) {
  if (!batchState) return;
  const list = batchState.filteredRows;
  const total = list.length;
  const maxPage = Math.max(0, Math.ceil(total / BATCH_PAGE_SIZE) - 1);
  const current = Math.max(0, Math.min(maxPage, page));
  batchState.page = current;
  const start = current * BATCH_PAGE_SIZE;
  const slice = list.slice(start, start + BATCH_PAGE_SIZE);

  const tbody = byId('batch-table-body');
  tbody.replaceChildren();
  if (!slice.length) {
    const tr = document.createElement('tr');
    const td = appendText('td', '', 'Không có dòng nào phù hợp bộ lọc.');
    td.colSpan = 4;
    tr.append(td);
    tbody.append(tr);
  }

  for (const item of slice) {
    const tr = document.createElement('tr');
    tr.id = 'batch-row-' + item.rowNumber;
    tr.append(appendText('td', '', formatNumber(item.rowNumber)));

    const snippet = item.text.trim() ? (item.text.length > 160 ? item.text.slice(0, 160) + '…' : item.text) : '(Trống)';
    tr.append(appendText('td', '', snippet));

    const tdBadge = document.createElement('td');
    const badgeCls = item.labelKey === 'negative' ? 'badge badge-neg' : item.labelKey === 'nonnegative' ? 'badge badge-nonneg' : 'badge badge-neutral';
    const badgeText = item.labelKey === 'invalid' ? 'Bỏ qua / không hợp lệ' : outcomes[item.labelKey].title;
    tdBadge.append(appendText('span', badgeCls, badgeText));
    tr.append(tdBadge);

    const tdAct = document.createElement('td');
    tdAct.style.whiteSpace = 'nowrap';
    const viewBtn = appendText('button', 'text-button', 'Xem chi tiết');
    viewBtn.type = 'button';
    viewBtn.style.marginRight = '10px';
    viewBtn.addEventListener('click', () => openBatchRow(item));
    tdAct.append(viewBtn);

    if (item.labelKey !== 'invalid') {
      const reported = batchState.reportedRows.has(item.rowNumber);
      const repBtn = appendText('button', 'text-button', reported ? 'Đã báo sai' : 'Báo cáo sai');
      repBtn.type = 'button';
      repBtn.style.color = reported ? 'var(--text-secondary)' : 'var(--danger)';
      repBtn.disabled = reported;
      repBtn.addEventListener('click', () => {
        openReportDialog({
          source: 'Tệp dữ liệu',
          text: item.text,
          predictionTitle: outcomes[item.labelKey].title,
          batchId: batchState.batchId,
          rowNumber: item.rowNumber,
          onSaved: () => {
            batchState.reportedRows.add(item.rowNumber);
            renderBatchPage(batchState.page);
          }
        });
      });
      tdAct.append(repBtn);
    }
    tr.append(tdAct);
    tbody.append(tr);
  }

  byId('batch-page-label').textContent = total
    ? `Hiển thị ${formatNumber(start + 1)}–${formatNumber(start + slice.length)} / ${formatNumber(total)} dòng`
    : '0 dòng';
  byId('batch-page-prev').disabled = current === 0;
  byId('batch-page-next').disabled = current >= maxPage;
}

async function openBatchRow(item) {
  if (!item) return;
  if (item.labelKey === 'invalid') {
    openDetailDialog({
      title: `Dòng STT ${item.rowNumber}`,
      labelName: 'Bỏ qua / không hợp lệ',
      labelCode: null,
      sourceInfo: `Lô #${batchState?.batchId || '—'}`,
      text: item.text || '(Trống)'
    });
    return;
  }
  showClassification({ label: item.labelKey, text: item.text, sentence_analysis: { available: false } }, 'batch', item.rowNumber);
  try {
    const res = await fetch('/api/sentences', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ input: item.text })
    });
    if (res.ok) renderSentenceBreakdown(await res.json());
  } catch {
    // Keep main prediction visible
  }
}

byId('batch-detail-prev').addEventListener('click', () => {
  if (!batchState || !lastResult) return;
  const idx = batchState.filteredRows.findIndex((r) => r.rowNumber === lastResult.rowNumber);
  if (idx > 0) openBatchRow(batchState.filteredRows[idx - 1]);
});
byId('batch-detail-next').addEventListener('click', () => {
  if (!batchState || !lastResult) return;
  const idx = batchState.filteredRows.findIndex((r) => r.rowNumber === lastResult.rowNumber);
  if (idx >= 0 && idx < batchState.filteredRows.length - 1) openBatchRow(batchState.filteredRows[idx + 1]);
});

byId('batch-search-input').addEventListener('input', applyBatchFilters);
byId('batch-label-filter').addEventListener('change', applyBatchFilters);
byId('batch-sort-select').addEventListener('change', applyBatchFilters);
byId('batch-page-prev').addEventListener('click', () => renderBatchPage((batchState?.page || 0) - 1));
byId('batch-page-next').addEventListener('click', () => renderBatchPage((batchState?.page || 0) + 1));
byId('batch-jump-go').addEventListener('click', () => {
  if (!batchState) return;
  const rowNum = Number(byId('batch-jump-input').value);
  const idx = batchState.filteredRows.findIndex((r) => r.rowNumber === rowNum);
  if (idx < 0) return;
  renderBatchPage(Math.floor(idx / BATCH_PAGE_SIZE));
  const rowEl = byId('batch-row-' + rowNum);
  if (rowEl) {
    rowEl.scrollIntoView({ behavior: prefersReducedMotion.matches ? 'auto' : 'smooth', block: 'center' });
    rowEl.classList.add('row-highlight');
    window.setTimeout(() => rowEl.classList.remove('row-highlight'), 2200);
  }
});

byId('batch-download-xlsx').addEventListener('click', async () => {
  if (!resultCsvBlob) return;
  const btn = byId('batch-download-xlsx');
  btn.disabled = true;
  btn.textContent = 'Đang tạo Excel…';
  try {
    const res = await fetch('/api/export-xlsx', {
      method: 'POST', headers: { 'content-type': 'application/octet-stream' }, body: resultCsvBlob
    });
    if (!res.ok) throw new Error('Không tạo được Excel.');
    const excelBlob = await res.blob();
    const url = URL.createObjectURL(excelBlob);
    const a = document.createElement('a');
    a.href = url;
    a.download = btn.dataset.filename || 'TextSense_ket_qua.xlsx';
    document.body.append(a);
    a.click();
    a.remove();
    window.setTimeout(() => URL.revokeObjectURL(url), 60000);
  } catch (e) {
    setBatchStatus(e.message || 'Lỗi xuất Excel.', 'error');
  } finally {
    btn.disabled = false;
    btn.textContent = 'Xuất Excel';
  }
});

// ---------- Section 4: Statistics ----------
let currentStatsSummary = null;

function renderInsightBars(containerId, rows, tone = '') {
  const container = byId(containerId);
  container.replaceChildren();
  if (!Array.isArray(rows) || !rows.length) {
    container.append(appendText('p', 'status-note', 'Không có dữ liệu phù hợp.'));
    return;
  }
  const max = Math.max(1, ...rows.map((r) => Number(r.count) || 0));
  for (const row of rows) {
    const count = Math.max(0, Number(row.count) || 0);
    const wrap = document.createElement('div');
    const head = document.createElement('div');
    head.className = 'insight-bar-head';
    head.append(appendText('span', '', String(row.label ?? row.term ?? '')));
    head.append(appendText('strong', '', formatNumber(count)));
    const track = document.createElement('div');
    track.className = 'insight-bar-track';
    const fill = document.createElement('span');
    fill.className = 'insight-bar-fill ' + tone;
    fill.style.width = (count / max * 100).toFixed(1) + '%';
    track.append(fill);
    wrap.append(head, track);
    container.append(wrap);
  }
}

function renderSuspectTable(terms) {
  const container = byId('dash-suspect-combined');
  container.replaceChildren();
  if (!Array.isArray(terms) || !terms.length) {
    container.append(appendText('p', 'status-note', 'Không ghi nhận từ ngữ nào khớp danh sách tham chiếu.'));
    return;
  }
  const table = document.createElement('table');
  table.className = 'suspect-terms-table';
  const thead = document.createElement('thead');
  const hr = document.createElement('tr');
  for (const h of ['Từ ngữ', 'Tổng số lần', 'Nhóm Tiêu cực', 'Nhóm Không tiêu cực', 'Số bình luận']) {
    hr.append(appendText('th', '', h));
  }
  thead.append(hr);
  const tbody = document.createElement('tbody');
  for (const item of terms) {
    const tr = document.createElement('tr');
    const nonneg = Math.max(0, (item.total_count || 0) - (item.negative_count || 0));
    for (const val of [item.term, formatNumber(item.total_count), formatNumber(item.negative_count), formatNumber(nonneg), formatNumber(item.total_documents)]) {
      tr.append(appendText('td', '', val));
    }
    tbody.append(tr);
  }
  table.append(thead, tbody);
  container.append(table);
}

function renderTermFrequencyExplorer() {
  if (!currentStatsSummary) return;
  const ngram = byId('term-ngram-select').value;
  const label = byId('term-label-select').value;
  const sortBy = byId('term-sort-select').value;
  const limit = Number(byId('term-limit-select').value) || 10;
  const query = byId('term-search-input').value.trim().toLowerCase();

  const keyMap = {
    unigram: { all: 'top_unigrams_all', negative: 'top_unigrams_negative', nonnegative: 'top_unigrams_nonnegative' },
    bigram: { all: 'top_bigrams_all', negative: 'top_bigrams_negative', nonnegative: 'top_bigrams_nonnegative' }
  };
  let list = [...(currentStatsSummary[keyMap[ngram][label]] || [])];
  if (query) list = list.filter((x) => x.term.toLowerCase().includes(query));
  list.sort((a, b) => sortBy === 'documents'
    ? (b.documents - a.documents || b.count - a.count)
    : (b.count - a.count || b.documents - a.documents));
  list = list.slice(0, limit);

  const tbody = byId('term-freq-tbody');
  tbody.replaceChildren();
  if (!list.length) {
    const tr = document.createElement('tr');
    const td = appendText('td', '', 'Không có từ khóa phù hợp.');
    td.colSpan = 5;
    tr.append(td);
    tbody.append(tr);
  }
  for (const item of list) {
    const tr = document.createElement('tr');
    tr.append(appendText('td', '', item.term));
    tr.append(appendText('td', '', formatNumber(item.count)));
    tr.append(appendText('td', '', formatNumber(item.documents ?? item.count)));
    const rate = item.doc_rate != null ? (item.doc_rate * 100).toLocaleString('vi-VN', { maximumFractionDigits: 1 }) + '%' : '—';
    tr.append(appendText('td', '', rate));
    const tdBtn = document.createElement('td');
    const btn = appendText('button', 'text-button', 'Xem bình luận');
    btn.type = 'button';
    btn.addEventListener('click', () => loadCommentsForTerm(item.term, label));
    tdBtn.append(btn);
    tr.append(tdBtn);
    tbody.append(tr);
  }
  renderInsightBars('term-freq-bars', list.map((x) => ({
    label: x.term,
    count: sortBy === 'documents' ? (x.documents ?? x.count) : x.count
  })), label === 'negative' ? 'rose' : label === 'nonnegative' ? 'lime' : '');
}

async function loadCommentsForTerm(term, labelGroup) {
  const box = byId('term-comments-box');
  const list = byId('term-comments-list');
  byId('term-comments-title').textContent = `Bình luận chứa "${term}"`;
  list.replaceChildren(appendText('li', '', 'Đang tải…'));
  box.hidden = false;

  const params = new URLSearchParams({ term });
  if (labelGroup === 'negative') params.set('label', '1');
  else if (labelGroup === 'nonnegative') params.set('label', '0');
  if (currentStatsSummary?.batch_id) params.set('batch_id', String(currentStatsSummary.batch_id));

  try {
    const res = await fetch('/api/stats/term-comments?' + params.toString());
    const data = await res.json().catch(() => ({}));
    list.replaceChildren();
    const comments = data.comments || [];
    if (!comments.length) {
      list.append(appendText('li', '', 'Không tìm thấy bình luận mẫu trong phạm vi hiện tại.'));
      return;
    }
    for (const c of comments) {
      const li = document.createElement('li');
      const badge = appendText('span', c.predicted_label === 1 ? 'badge badge-neg' : 'badge badge-nonneg', c.label_name);
      li.append(badge, document.createTextNode(' ' + c.text));
      list.append(li);
    }
  } catch {
    list.replaceChildren(appendText('li', '', 'Lỗi khi truy xuất bình luận.'));
  }
}

byId('term-comments-close').addEventListener('click', () => { byId('term-comments-box').hidden = true; });
for (const id of ['term-search-input', 'term-ngram-select', 'term-label-select', 'term-sort-select', 'term-limit-select']) {
  byId(id).addEventListener('input', renderTermFrequencyExplorer);
  byId(id).addEventListener('change', renderTermFrequencyExplorer);
}

function renderStatsDashboard(summary, scopeLabel = '') {
  if (!summary) return;
  currentStatsSummary = summary;
  byId('stats-empty').hidden = true;
  byId('batch-dashboard').hidden = false;
  byId('stats-scope-banner').textContent = `Phạm vi dữ liệu: ${scopeLabel || (summary.batch_id ? 'Phiên #' + summary.batch_id : 'Phiên hiện tại')} · ${formatNumber(summary.valid)} dòng hợp lệ / ${formatNumber(summary.total)} tổng số dòng.`;

  const total = summary.total || 0;
  const valid = summary.valid || 0;
  const invalid = summary.invalid || 0;
  const neg = summary.negative || 0;
  const nonneg = summary.nonnegative || 0;
  const pctText = (v, b) => (b > 0 ? (v * 100 / b) : 0).toLocaleString('vi-VN', { minimumFractionDigits: 1, maximumFractionDigits: 1 }) + '%';
  const negPct = valid > 0 ? (neg * 100 / valid) : 0;
  const nonnegPct = valid > 0 ? (nonneg * 100 / valid) : 0;

  byId('dash-total').textContent = formatNumber(total);
  byId('dash-valid').textContent = formatNumber(valid);
  byId('dash-invalid').textContent = formatNumber(invalid);
  byId('dash-analyzed').textContent = formatNumber(valid);
  byId('dash-valid-rate').textContent = pctText(valid, total) + ' tổng dòng';
  byId('dash-invalid-rate').textContent = pctText(invalid, total) + ' tổng dòng';

  byId('donut-total').textContent = formatNumber(valid);
  byId('dash-negative-count').textContent = formatNumber(neg);
  byId('dash-nonnegative-count').textContent = formatNumber(nonneg);
  byId('dash-negative-pct').textContent = pctText(neg, valid);
  byId('dash-nonnegative-pct').textContent = pctText(nonneg, valid);
  byId('batch-donut').style.setProperty('--negative-share', negPct + '%');
  byId('dash-negative-bar').style.width = negPct + '%';
  byId('dash-nonnegative-bar').style.width = nonnegPct + '%';

  const dom = neg > nonneg ? 'Có nội dung tiêu cực' : nonneg > neg ? 'Không phát hiện nội dung tiêu cực' : 'Hai nhóm bằng nhau';
  byId('dash-insight').textContent = valid
    ? `Nhóm chiếm tỷ trọng cao hơn: ${dom} (${Math.max(negPct, nonnegPct).toLocaleString('vi-VN', { maximumFractionDigits: 1 })}%).`
    : 'Không có dòng hợp lệ.';

  byId('dash-avg-words').textContent = Number(summary.avg_words || 0).toLocaleString('vi-VN', { maximumFractionDigits: 1 });
  byId('dash-median-words').textContent = Number(summary.median_words || 0).toLocaleString('vi-VN', { maximumFractionDigits: 1 });
  byId('dash-duplicates').textContent = formatNumber(summary.duplicate_excess || 0);
  renderInsightBars('dash-length-bars', summary.length_buckets, 'lime');
  renderSuspectTable(summary.suspect_terms_combined);
  renderTermFrequencyExplorer();

  const hasSource = Array.isArray(summary.source_distribution) && summary.source_distribution.length > 0;
  const hasMonth = Array.isArray(summary.monthly_distribution) && summary.monthly_distribution.length > 0;
  byId('stats-source-time-block').hidden = !hasSource && !hasMonth;
  byId('dash-source-card').hidden = !hasSource;
  byId('dash-month-card').hidden = !hasMonth;
  if (hasSource) renderInsightBars('dash-source-bars', summary.source_distribution);
  if (hasMonth) renderInsightBars('dash-month-bars', summary.monthly_distribution, 'rose');

  const hasRef = Boolean(summary.reference_evaluation);
  byId('dash-original-card').hidden = !hasRef;
  if (hasRef) {
    const ev = summary.reference_evaluation;
    const fmtP = (v) => (Number(v) * 100).toLocaleString('vi-VN', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + '%';
    const kpis = byId('ref-eval-metrics');
    kpis.replaceChildren();
    for (const [label, val] of [['Accuracy', fmtP(ev.accuracy)], ['Precision (1)', fmtP(ev.precision)], ['Recall (1)', fmtP(ev.recall)], ['F1-score (1)', fmtP(ev.f1)]]) {
      const card = appendText('div', 'kpi-box', '');
      card.append(appendText('span', '', label), appendText('strong', '', val));
      kpis.append(card);
    }
    renderInsightBars('dash-original-bars', summary.original_labels);
    const cm = ev.confusion_matrix || [[0, 0], [0, 0]];
    const cmWrap = byId('ref-confusion-wrap');
    cmWrap.replaceChildren(appendText('h4', 'card-title', 'Ma trận nhầm lẫn (Confusion Matrix)'));
    const tbl = document.createElement('table');
    tbl.className = 'data-table';
    tbl.innerHTML = `<thead><tr><th>Thực tế \\ Dự đoán</th><th>Nhãn 0</th><th>Nhãn 1</th></tr></thead>
      <tbody><tr><td><strong>Tham chiếu 0</strong></td><td>${formatNumber(cm[0][0])} (TN)</td><td>${formatNumber(cm[0][1])} (FP)</td></tr>
      <tr><td><strong>Tham chiếu 1</strong></td><td>${formatNumber(cm[1][0])} (FN)</td><td>${formatNumber(cm[1][1])} (TP)</td></tr></tbody>`;
    cmWrap.append(tbl);
  }
}

async function loadStatsFromServer(batchId = '') {
  if (!batchId) {
    currentStatsSummary = null;
    byId('stats-empty').hidden = false;
    byId('batch-dashboard').hidden = true;
    return;
  }
  try {
    const url = '/api/stats?batch_id=' + encodeURIComponent(batchId);
    const res = await fetch(url);
    const data = await res.json().catch(() => ({}));
    if (res.ok && data.available && data.summary) {
      renderStatsDashboard(data.summary, data.summary.filename || (data.summary.batch_id ? `Phiên phân tích #${data.summary.batch_id}` : 'Phiên hiện tại'));
    }
  } catch {
    // Ignore when empty
  }
}
byId('stats-reload').addEventListener('click', () => loadStatsFromServer(byId('stats-batch-select').value));
byId('stats-batch-select').addEventListener('change', () => loadStatsFromServer(byId('stats-batch-select').value));
loadHistoryBatches();

window.addEventListener('beforeunload', () => {
  if (resultDownloadUrl) URL.revokeObjectURL(resultDownloadUrl);
});
