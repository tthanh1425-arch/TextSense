'use strict';

// Giữ lối thông báo và biểu cảm chim của TextSense gốc; mô hình thực tế chỉ phân loại cảm xúc.
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
const birdAssets = {nonnegative:'friendly',negative:'alert'};
const descriptions = {
  idle: 'Chim xanh ngồi thư thái.',
  ready: 'Chim xanh cầm mẩu bình luận.',
  work: 'Chim xanh đang gõ laptop.',
  sad: 'Chim xanh cúi đầu.'
};

const byId = (id) => document.getElementById(id);
const form = byId('comment-form');
const input = byId('comment');
const submit = byId('submit');
const retry = byId('retry');
const clear = byId('clear');
const failure = byId('failure');
const progress = byId('progress-message');
const result = byId('result');
const resultTitle = byId('result-title');
const mascot = byId('mascot');
const workspace = byId('workspace');
const reportDialog = byId('report-dialog');
const reportForm = byId('report-form');
const limit = 2000;
let revision = 0;
let active;
let lastResult;
let resultAnimation = 0;
let resultOrigin = 'single';

function setState(state) {
  workspace.dataset.state = state;
  mascot.src = 'media/' + (birdAssets[state] || state) + '.webp?v=mascot';
  mascot.alt = descriptions[state] || outcomes[state]?.alt || '';
  // Cho phep hieu ung cua mascot khoi chay lai khi xem hai ket qua cung nhan.
  mascot.style.animation = 'none';
  void mascot.offsetWidth;
  mascot.style.animation = '';
}

function renderSentenceBreakdown(analysis) {
  const section = byId('sentence-breakdown');
  const list = byId('sentence-breakdown-list');
  section.hidden = true;
  list.replaceChildren();
  if (!analysis?.available || !Array.isArray(analysis.sentences)) return;

  const negativeCount = Number(analysis.negative_parts);
  const totalParts = Number(analysis.total_parts);
  if (!Number.isSafeInteger(negativeCount) || !Number.isSafeInteger(totalParts) ||
      totalParts < 2 || negativeCount < 1 || negativeCount > totalParts) return;

  byId('sentence-breakdown-title').textContent = analysis.mixed
    ? 'Các sắc thái trong bình luận' : 'Những phần mang sắc thái tiêu cực';
  byId('sentence-breakdown-description').textContent =
    'Phân tích chi tiết từng phần; nếu có ít nhất một phần tiêu cực thì bình luận được xác định là có nội dung tiêu cực.';
  byId('sentence-breakdown-count').textContent =
    'Phát hiện ' + negativeCount + ' phần tiêu cực trong ' + totalParts + ' phần được phân loại.';

  for (const [index, item] of analysis.sentences.entries()) {
    const row = document.createElement('li');
    row.className = 'sentence-item' + (item.label === 'negative' ? ' sentence-item-negative' : '');
    const header = document.createElement('div');
    header.className = 'sentence-item-header';
    const number = document.createElement('span');
    number.className = 'sentence-number';
    number.textContent = 'Phần ' + (index + 1);
    const tag = document.createElement('strong');
    tag.className = 'sentence-label ' + (item.label === 'negative' ? 'negative' : item.label === 'nonnegative' ? 'nonnegative' : 'unknown');
    tag.textContent = item.label === 'negative' ? 'Tiêu cực' :
      item.label === 'nonnegative' ? 'Không tiêu cực' : 'Chưa xác định';
    const content = document.createElement('p');
    content.textContent = item.text || '';
    header.append(number, tag);
    row.append(header, content);
    list.append(row);
  }
  section.hidden = list.childElementCount < 2;
}

async function loadBatchSentenceBreakdown(text, shownAnimation, rowNumber = 0) {
  if (!text || !/[,，;；:：.!?。！？…—–\n\r]/u.test(text)) return;
  try {
    const response = await fetch('/api/sentences', {
      method: 'POST', headers: {'content-type':'application/json'},
      body: JSON.stringify({input: text})
    });
    if (!response.ok) return;
    const analysis = await response.json();
    if (shownAnimation === resultAnimation && resultOrigin === 'batch') {
      renderSentenceBreakdown(analysis);
      if (analysis.negative_parts > 0 && lastResult?.label !== 'negative') {
        showClassification({label: 'negative', text, sentence_analysis: analysis}, 'batch', rowNumber);
      }
    }
  } catch {
    // The overall prediction already exists; keep it visible on failure.
  }
}

function showClassification(payload, origin = 'single', rowNumber = 0) {
  const classification = outcomes[payload.label];
  if (!classification) throw new Error('Nhan du doan khong hop le');
  resultOrigin = origin;
  lastResult = payload;
  byId('report').hidden = false;
  byId('result-label').textContent = origin === 'batch'
    ? 'Kết quả · Bình luận số ' + formatNumber(rowNumber)
    : 'Kết quả phân loại';
  byId('back-input').hidden = origin === 'batch';
  byId('back-batch').hidden = origin !== 'batch';
  byId('new-comment').hidden = origin === 'batch';
  byId('batch-detail-nav').hidden = origin !== 'batch';
  resultTitle.textContent = classification.title;
  byId('result-detail').textContent = classification.detail;
  renderSentenceBreakdown(payload.sentence_analysis);
  byId('result-quote').textContent = payload.text;
  byId('history-warning').hidden = origin !== 'single' || payload.history_saved !== false;
  byId('entry').hidden = true;
  result.hidden = false;
  const animation = ++resultAnimation;
  setState('work');
  window.setTimeout(() => {
    if (animation === resultAnimation) setState(payload.label);
  }, prefersReducedMotion.matches ? 0 : 200);
  resultTitle.focus({preventScroll: true});
  if (origin === 'batch') {
    setMode('single');
    byId('batch-detail-position').textContent = formatNumber(rowNumber) + ' / ' + formatNumber(batchCsv?.rowCount || 0);
    byId('batch-detail-prev').disabled = rowNumber <= 1;
    byId('batch-detail-next').disabled = rowNumber >= (batchCsv?.rowCount || 0);
  }
  requestAnimationFrame(() => byId('result').scrollIntoView({behavior: prefersReducedMotion.matches ? 'auto' : 'smooth', block: 'start'}));
}

function updateInput() {
  resultAnimation += 1;
  revision += 1;
  active?.abort();
  active = undefined;
  failure.hidden = true;
  retry.hidden = true;
  submit.hidden = false;
  submit.firstChild.textContent = 'Phân tích ';
  progress.textContent = '';
  const text = input.value.trim();
  const length = Array.from(text).length;
  const tooLong = length > limit;
  const count = byId('count');
  count.textContent = length.toLocaleString('vi-VN') + ' / 2.000 ký tự';
  count.dataset.invalid = String(tooLong);
  input.setAttribute('aria-invalid', String(tooLong));
  const error = byId('input-error');
  error.hidden = !tooLong;
  error.textContent = tooLong ? 'Nội dung vượt 2.000 ký tự và chưa được gửi. Hãy rút gọn nội dung để tiếp tục.' : '';
  submit.disabled = tooLong || !input.value.trim();
  clear.hidden = !input.value;
  byId('entry').hidden = false;
  result.hidden = true;
  renderSentenceBreakdown(null);
  byId('history-warning').hidden = true;
  lastResult = undefined;
  setState(input.value.trim() ? 'ready' : 'idle');
}

function showError(message, detail, retryable = false) {
  setState('sad');
  byId('failure-title').textContent = message;
  byId('failure-detail').textContent = detail;
  failure.hidden = false;
  retry.hidden = !retryable;
  submit.hidden = retryable;
  submit.disabled = false;
  submit.firstChild.textContent = 'Phân tích ';
  progress.textContent = '';
  if (retryable) retry.focus();
}


function returnToInput(erase) {
  resultOrigin = 'single';
  if (erase) input.value = '';
  updateInput();
  input.focus();
}

input.addEventListener('input', updateInput);
clear.addEventListener('click', () => returnToInput(true));
byId('new-comment').addEventListener('click', () => returnToInput(true));
byId('back-input').addEventListener('click', () => returnToInput(false));
byId('back-batch').addEventListener('click', () => returnToBatch());
byId('batch-detail-prev').addEventListener('click', () => openBatchRow((batchCsv?.openRow || 1) - 1));
byId('batch-detail-next').addEventListener('click', () => openBatchRow((batchCsv?.openRow || 0) + 1));
retry.addEventListener('click', () => form.requestSubmit());

form.addEventListener('submit', async (event) => {
  event.preventDefault();
  const value = input.value.trim();
  if (!value || submit.disabled) return;
  const request = ++revision;
  active = new AbortController();
  failure.hidden = true;
  retry.hidden = true;
  submit.hidden = false;
  submit.disabled = true;
  submit.firstChild.textContent = 'Đang phân tích… ';
  progress.textContent = 'Đang phân tích nội dung.';
  setState('work');

  try {
    const response = await fetch('/api/analyze', {
      method: 'POST',
      headers: {'content-type': 'application/json'},
      body: JSON.stringify({input: value}),
      signal: active.signal
    });
    const payload = await response.json().catch(() => null);
    if (request !== revision) return;
    const exactCode = ({negative: 1, nonnegative: 0})[payload?.label];
    if (!response.ok || !payload || !Object.hasOwn(outcomes, payload.label) || payload.code !== exactCode || typeof payload.text !== 'string') {
      showError(payload?.message || 'Máy chủ không trả được kết quả',
        payload?.detail || 'Nội dung vẫn ở ô nhập.', payload?.retryable ?? true);
      return;
    }
    showClassification(payload, 'single');
    progress.textContent = '';
  } catch {
    if (request === revision) {
      showError('Không kết nối được với TextSense', 'Hãy kiểm tra ứng dụng trong Terminal rồi thử lại.', true);
    }
  } finally {
    if (request === revision) active = undefined;
  }
});

byId('report').addEventListener('click', () => {
  reportForm.reset();
  reportDialog.showModal();
});
byId('cancel-report').addEventListener('click', () => reportDialog.close());
reportForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  if (!lastResult) return;
  const suggestedLabel = outcomes[byId('report-label').value]?.title || byId('report-label').value;
  const note = byId('report-reason').value.trim();
  const text = byId('report-include').checked ? lastResult.text : null;
  const source = resultOrigin === 'batch' ? 'Tệp dữ liệu' : 'Bình luận riêng lẻ';
  const prediction = outcomes[lastResult.label]?.title || lastResult.label;

  const submitBtn = reportForm.querySelector('button[type="submit"]');
  if (submitBtn) submitBtn.disabled = true;

  try {
    const res = await fetch('/api/feedback', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        source,
        prediction,
        suggested_label: suggestedLabel,
        note,
        text
      })
    });
    const data = await res.json();
    if (data.feedback_saved) {
      alert('Đã ghi nhận báo cáo vào SQL Server (dbo.UserFeedback) thành công!');
    } else {
      alert('Đã gửi phản hồi. Lưu ý: ' + (data.message || 'Chưa thể lưu vào SQL Server.'));
    }
  } catch (err) {
    alert('Không thể kết nối đến máy chủ để lưu phản hồi: ' + err.message);
  } finally {
    if (submitBtn) submitBtn.disabled = false;
    reportDialog.close();
  }
});

updateInput();

// Navigation must open the desired mode and always scroll to usable controls.
const singleTab = byId('tab-single');
const batchTab = byId('tab-batch');
const batchPanel = byId('hang-loat');
const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
function setMode(mode, shouldFocus = false) {
  const batch = mode === 'batch';
  workspace.hidden = batch;
  batchPanel.hidden = !batch;
  singleTab.setAttribute('aria-selected', String(!batch));
  batchTab.setAttribute('aria-selected', String(batch));
  singleTab.tabIndex = batch ? -1 : 0;
  batchTab.tabIndex = batch ? 0 : -1;
  if (shouldFocus) (batch ? batchTab : singleTab).focus({preventScroll: true});
}
function navigateToMode(mode, focusField = false) {
  if (mode === 'single' && resultOrigin === 'batch') returnToInput(false);
  setMode(mode);
  const isBatch = mode === 'batch';
  const target = isBatch ? batchPanel : byId('entry');
  history.replaceState(null, '', isBatch ? '#hang-loat' : '#phan-tich');
  requestAnimationFrame(() => {
    target.scrollIntoView({
      behavior: prefersReducedMotion.matches ? 'auto' : 'smooth',
      block: 'start'
    });
    if (focusField && !isBatch) input.focus({preventScroll: true});
  });
}
singleTab.addEventListener('click', () => navigateToMode('single'));
batchTab.addEventListener('click', () => navigateToMode('batch'));
for (const tab of [singleTab, batchTab]) {
  tab.addEventListener('keydown', (e) => {
    if (e.key !== 'ArrowRight' && e.key !== 'ArrowLeft') return;
    e.preventDefault();
    const mode = tab === singleTab ? 'batch' : 'single';
    navigateToMode(mode);
    (mode === 'batch' ? batchTab : singleTab).focus({preventScroll: true});
  });
}
for (const link of document.querySelectorAll('a[href="#phan-tich"]')) {
  link.addEventListener('click', (event) => {
    event.preventDefault();
    navigateToMode('single', link.classList.contains('primary'));
  });
}
for (const link of document.querySelectorAll('[data-open-batch]')) {
  link.addEventListener('click', (event) => {
    event.preventDefault();
    navigateToMode('batch');
  });
}
window.addEventListener('hashchange', () => {
  if (location.hash === '#hang-loat') navigateToMode('batch');
  else if (location.hash === '#phan-tich') navigateToMode('single');
});
if (location.hash === '#hang-loat') navigateToMode('batch');
else if (location.hash === '#phan-tich') navigateToMode('single');

// Show truthful model file availability. Full compatibility is checked on use.
fetch('/api/health').then(r => r.json()).then(data => {
  const status = byId('model-state');
  status.hidden = Boolean(data.model_present);
  status.textContent = data.model_present ? '' : 'Chưa thể phân tích. Hãy kiểm tra cài đặt mô hình.';
  status.dataset.ok = String(Boolean(data.model_present));
}).catch(() => {
  const status = byId('model-state');
  status.hidden = false;
  status.textContent = 'Không thể kết nối máy chủ. Hãy kiểm tra ứng dụng.';
});

const csvFile = byId('csv-file');
const csvDropzone = byId('csv-dropzone');
const csvColumn = byId('csv-column');
const batchSubmit = byId('batch-submit');
const batchStatus = byId('batch-status');
const batchResult = byId('batch-result');
const csvConfig = byId('csv-config');
const batchProgress = byId('batch-progress');
let maxCsvBytes = 100 * 1024 * 1024;
let maxCsvRows = 300000;
let selectedCsv = null;
let resultCsvBlob = null;
const sheetSelect = byId('xlsx-sheet');
let csvRevision = 0;
let csvController;
let batchController;
let csvPreviewRows = [];
let resultDownloadUrl = null;
let batchCsv = null;
let browseRevision = 0;
const PAGE_SIZE = 8;

const formatNumber = (n) => Number(n).toLocaleString('vi-VN');
const formatBytes = (n) => n >= 1048576
  ? (n / 1048576).toLocaleString('vi-VN', {maximumFractionDigits: 2}) + ' MB'
  : (n / 1024).toLocaleString('vi-VN', {maximumFractionDigits: 1}) + ' KB';

function decodeSummaryHeader(value) {
  if (!value) return null;
  try {
    // Accept both regular and URL-safe base64 from the Python server.
    // The previous version passed '-' and '_' to atob(), silently dropping
    // ALL advanced dashboard statistics for some uploads.
    const normalized = value.replace(/-/g, '+').replace(/_/g, '/');
    const binary = atob(normalized + '='.repeat((4 - normalized.length % 4) % 4));
    const bytes = Uint8Array.from(binary, (char) => char.charCodeAt(0));
    return JSON.parse(new TextDecoder('utf-8').decode(bytes));
  } catch {
    return null;
  }
}

function renderInsightBars(containerId, rows, tone = 'lime') {
  const container = byId(containerId);
  container.replaceChildren();
  if (!Array.isArray(rows) || !rows.length) {
    container.append(appendText('p', 'insight-empty', 'Không có dữ liệu phù hợp trong tệp.'));
    return;
  }
  const max = Math.max(1, ...rows.map((row) => Number(row.count) || 0));
  for (const row of rows) {
    const count = Math.max(0, Number(row.count) || 0);
    const line = document.createElement('div');
    line.className = 'insight-bar-row';
    const head = document.createElement('div');
    head.className = 'insight-bar-head';
    head.append(appendText('span', 'insight-bar-label', String(row.label ?? 'Không xác định')));
    head.append(appendText('strong', 'insight-bar-count', formatNumber(count)));
    const track = document.createElement('div');
    track.className = 'insight-bar-track';
    const fill = document.createElement('span');
    fill.className = 'insight-bar-fill ' + tone;
    fill.style.width = (count / max * 100).toFixed(2) + '%';
    track.append(fill);
    line.append(head, track);
    container.append(line);
  }
}

function renderSourceDistribution(rows) {
  const container = byId('dash-source-bars');
  container.replaceChildren();
  if (!Array.isArray(rows) || !rows.length) {
    container.append(appendText('p', 'insight-empty', 'Tệp không có thông tin nguồn.'));
    return;
  }
  for (const row of rows) {
    const total = Math.max(0, Number(row.count) || 0);
    const negative = Math.max(0, Number(row.negative) || 0);
    const nonnegative = Math.max(0, Number(row.nonnegative) || 0);
    const item = document.createElement('div');
    item.className = 'source-bar-item';
    const head = document.createElement('div');
    head.className = 'insight-bar-head';
    head.append(appendText('span', 'insight-bar-label', String(row.label ?? 'Không xác định')));
    head.append(appendText('strong', 'insight-bar-count', formatNumber(total) + ' dòng'));
    const track = document.createElement('div');
    track.className = 'source-stacked-track';
    const neg = document.createElement('span');
    neg.className = 'source-stacked-negative';
    neg.style.width = (total ? negative / total * 100 : 0) + '%';
    const nonneg = document.createElement('span');
    nonneg.className = 'source-stacked-nonnegative';
    nonneg.style.width = (total ? nonnegative / total * 100 : 0) + '%';
    track.append(neg, nonneg);
    const legend = document.createElement('p');
    legend.className = 'source-stacked-legend';
    legend.textContent = 'Có nội dung tiêu cực: ' + formatNumber(negative) + ' · Không phát hiện nội dung tiêu cực: ' + formatNumber(nonnegative);
    item.append(head, track, legend);
    container.append(item);
  }
}

function renderTermList(containerId, terms) {
  const container = byId(containerId);
  container.replaceChildren();
  if (!Array.isArray(terms) || !terms.length) {
    container.append(appendText('p', 'insight-empty', 'Chưa có từ khóa phù hợp.'));
    return;
  }
  for (const item of terms) {
    const chip = document.createElement('span');
    chip.className = 'term-chip';
    chip.append(appendText('b', '', String(item.term ?? '')));
    chip.append(appendText('small', '', formatNumber(Number(item.count) || 0)));
    container.append(chip);
  }
}


function renderSuspectTermTable(containerId, terms) {
  const container = byId(containerId);
  container.replaceChildren();
  if (!Array.isArray(terms) || !terms.length) {
    container.append(appendText('p', 'insight-empty', 'Không tìm thấy từ ngữ phù hợp trong tệp này.'));
    return;
  }
  const table = document.createElement('table');
  table.className = 'suspect-terms-table';
  const thead = document.createElement('thead');
  const header = document.createElement('tr');
  for (const title of ['Từ ngữ', 'Tổng số lần', 'Nhóm Tiêu cực', 'Nhóm Không tiêu cực', 'Tỷ lệ trong nhóm Tiêu cực', 'Số bình luận chứa từ']) {
    header.append(appendText('th', '', title));
  }
  thead.append(header);
  const tbody = document.createElement('tbody');
  for (const item of terms) {
    const all = Math.max(0, Number(item.total_count) || 0);
    const negative = Math.max(0, Number(item.negative_count) || 0);
    const nonnegative = Math.max(0, all - negative);
    const percent = all ? (negative / all * 100).toLocaleString('vi-VN', {maximumFractionDigits: 1}) + '%' : '—';
    const row = document.createElement('tr');
    for (const cell of [String(item.term ?? ''), formatNumber(all), formatNumber(negative), formatNumber(nonnegative), percent, formatNumber(Number(item.total_documents) || 0)]) {
      row.append(appendText('td', '', cell));
    }
    tbody.append(row);
  }
  table.append(thead, tbody);
  container.append(table);
}

function renderDatasetInsights(summary) {
  if (!summary || typeof summary !== 'object') return;
  byId('dash-avg-words').textContent = Number(summary.avg_words || 0).toLocaleString('vi-VN', {maximumFractionDigits: 1});
  byId('dash-median-words').textContent = Number(summary.median_words || 0).toLocaleString('vi-VN', {maximumFractionDigits: 1});
  byId('dash-duplicates').textContent = formatNumber(summary.duplicate_excess || 0);
  renderInsightBars('dash-length-bars', summary.length_buckets, 'lime');

  const sourceCard = byId('dash-source-card');
  sourceCard.hidden = !Array.isArray(summary.source_distribution) || !summary.source_distribution.length;
  if (!sourceCard.hidden) renderSourceDistribution(summary.source_distribution);

  const originalCard = byId('dash-original-card');
  originalCard.hidden = !Array.isArray(summary.original_labels) || !summary.original_labels.length;
  if (!originalCard.hidden) {
    renderInsightBars('dash-original-bars', summary.original_labels, 'blue');
    const agreement = summary.proxy_agreement;
    const note = byId('dash-proxy-agreement');
    note.hidden = !agreement;
    if (agreement) {
      note.textContent = 'Mức khớp với nhãn cảm xúc gốc: ' + (Number(agreement.rate) * 100).toLocaleString('vi-VN', {maximumFractionDigits: 1}) + '% (' + formatNumber(agreement.count) + ' dòng). Đây không phải độ chính xác khi nhận diện lời lẽ xúc phạm.';
    }
  }

  renderTermList('dash-top-terms', summary.top_terms);
  renderTermList('dash-top-negative-terms', summary.top_negative_terms);
  renderSuspectTermTable('dash-suspect-combined', summary.suspect_terms_combined);
  const monthCard = byId('dash-month-card');
  monthCard.hidden = !Array.isArray(summary.monthly_distribution) || !summary.monthly_distribution.length;
  if (!monthCard.hidden) renderInsightBars('dash-month-bars', summary.monthly_distribution, 'rose');
}

fetch('/api/config').then((res) => res.ok ? res.json() : null).then((data) => {
  if (!data) return;
  if (Number.isSafeInteger(data.max_csv_bytes) && data.max_csv_bytes > 0) maxCsvBytes = data.max_csv_bytes;
  if (Number.isSafeInteger(data.max_csv_rows) && data.max_csv_rows > 0) maxCsvRows = data.max_csv_rows;
  byId('csv-limit-label').textContent = formatBytes(maxCsvBytes);
  byId('csv-rows-label').textContent = formatNumber(maxCsvRows) + ' dòng';
}).catch(() => {});

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
  batchSubmit.textContent = busy ? 'Đang phân loại…' : 'Phân tích toàn bộ tệp →';
  batchPanel.setAttribute('aria-busy', String(busy));
}
function clearBatchResult() {
  browseRevision += 1;
  batchCsv = null;
  byId('batch-browse').hidden = true;
  byId('batch-rows').replaceChildren();
  batchResult.hidden = true;
  // Xóa dashboard cũ khi người dùng chọn tệp khác hoặc chạy lại.
  ['dash-total','dash-valid','dash-invalid','dash-valid-rate','dash-invalid-rate','donut-total','dash-negative-count','dash-nonnegative-count','dash-negative-pct','dash-nonnegative-pct'].forEach((id) => { const node = byId(id); if (node) node.textContent = '—'; });
  byId('batch-donut')?.style.setProperty('--negative-share', '0%');
  byId('dash-negative-bar')?.style.setProperty('width', '0%');
  byId('dash-nonnegative-bar')?.style.setProperty('width', '0%');
  if (byId('dash-insight')) byId('dash-insight').textContent = 'Chưa có dữ liệu phân tích.';
  ['dash-source-card','dash-original-card','dash-month-card'].forEach((id) => { if (byId(id)) byId(id).hidden = true; });
  ['dash-length-bars','dash-source-bars','dash-original-bars','dash-top-terms','dash-top-negative-terms','dash-suspect-combined','dash-month-bars'].forEach((id) => { if (byId(id)) byId(id).replaceChildren(); });
  ['dash-avg-words','dash-median-words','dash-duplicates'].forEach((id) => { if (byId(id)) byId(id).textContent = '—'; });
  if (byId('dash-proxy-agreement')) byId('dash-proxy-agreement').hidden = true;
  if (resultDownloadUrl) URL.revokeObjectURL(resultDownloadUrl);
  resultDownloadUrl = null;
  resultCsvBlob = null;
  byId('batch-download').removeAttribute('href');
  byId('batch-download-xlsx').disabled = true;
  byId('batch-download-xlsx').textContent = 'Tải Excel ↓';
}
function displayPreview() {
  const col = csvColumn.value;
  const panel = byId('csv-preview');
  const list = byId('csv-preview-list');
  list.replaceChildren();
  if (!col || !csvPreviewRows.length) { panel.hidden = true; return; }
  for (const sample of csvPreviewRows) {
    const li = document.createElement('li');
    li.textContent = sample[col]?.trim() || '(trống)';
    list.append(li);
  }
  panel.hidden = false;
}
csvColumn.addEventListener('change', () => { displayPreview(); clearBatchResult(); batchSubmit.disabled = !selectedCsv || csvConfig.hidden || !csvColumn.value; });

async function selectCsv(file, requestedSheet = '') {
  const revision = ++csvRevision;
  csvController?.abort();
  batchController?.abort();
  csvController = new AbortController();
  selectedCsv = null;
  csvPreviewRows = [];
  csvConfig.hidden = true;
  csvColumn.replaceChildren(new Option('Tự động nhận diện', ''));
  csvColumn.disabled = true;
  batchSubmit.disabled = true;
  byId('csv-preview').hidden = true;
  byId('sheet-wrap').hidden = true;
  sheetSelect.replaceChildren();
  byId('selected-file').hidden = true;
  setBatchBusy(false);
  clearBatchResult();
  if (!file) { setBatchStatus('Chọn tệp để bắt đầu.'); return; }
  if (!/\.(csv|xlsx)$/i.test(file.name)) {
    setBatchStatus('Định dạng không hợp lệ. Hãy tải tệp CSV hoặc Excel (.xlsx).', 'error'); return;
  }
  if (file.size === 0) {
    setBatchStatus('Tệp đang trống.', 'error'); return;
  }
  if (file.size > maxCsvBytes) {
    setBatchStatus('Tệp ' + formatBytes(file.size) + ' vượt giới hạn ' + formatBytes(maxCsvBytes) + '.', 'error'); return;
  }
  selectedCsv = file;
  byId('selected-file').hidden = false;
  byId('file-name').textContent = file.name;
  byId('file-metadata').textContent = formatBytes(file.size) + ' · đang đọc tệp';
  setBatchStatus('Đang đọc tệp và kiểm tra dữ liệu…');
  setBatchBusy(true, 'Đang kiểm tra cấu trúc và cột dữ liệu…');
  try {
    const response = await fetch('/api/columns?filename=' + encodeURIComponent(file.name) + (requestedSheet ? '&sheet=' + encodeURIComponent(requestedSheet) : ''), {
      method: 'POST', headers: {'content-type': 'application/octet-stream'},
      body: file, signal: csvController.signal,
    });
    const data = await response.json().catch(() => null);
    if (revision !== csvRevision) return;
    if (!response.ok || !data || !Array.isArray(data.columns)) {
      setBatchStatus([data?.message || 'Không đọc được tệp.', data?.detail].filter(Boolean).join(' '), 'error');
      return;
    }
    const sheets = Array.isArray(data.sheets) ? data.sheets : [];
    if (sheets.length > 1) {
      for (const name of sheets) sheetSelect.append(new Option(name, name));
      sheetSelect.value = data.selected_sheet || sheets[0];
      byId('sheet-wrap').hidden = false;
    }
    csvColumn.replaceChildren();
    const initialOption = new Option('Chọn cột bình luận', '');
    initialOption.disabled = true;
    csvColumn.append(initialOption);
    const labelColumns = new Set(data.label_columns || []);
    const indexColumns = new Set([...(data.index_columns || []), ...(data.link_columns || [])]);
    for (const name of data.columns) {
      const option = new Option(
        labelColumns.has(name) ? name + ' (không phải cột nội dung)' :
        indexColumns.has(name) ? name + ' (không phải cột nội dung)' : name,
        name
      );
      option.disabled = labelColumns.has(name) || indexColumns.has(name);
      csvColumn.append(option);
    }
    csvColumn.value = data.suggested_column && data.columns.includes(data.suggested_column) ? data.suggested_column : '';
    csvPreviewRows = Array.isArray(data.preview_rows) ? data.preview_rows : [];
    csvConfig.hidden = false;
    byId('file-metadata').textContent = formatBytes(file.size) + ' · ' + formatNumber(data.rows) + ' dòng · ' + data.columns.length + ' cột';
    setBatchStatus(data.suggested_column
      ? 'Đã đọc ' + formatNumber(data.rows) + ' bình luận. Kiểm tra cột nội dung và bắt đầu phân tích.'
      : 'Không nhận diện được cột bình luận. Hãy chọn đúng cột nội dung.', data.suggested_column ? 'success' : 'error');
    displayPreview();
  } catch (error) {
    if (revision === csvRevision && error.name !== 'AbortError')
      setBatchStatus('Không kết nối được máy chủ TextSense. Hãy kiểm tra ứng dụng đang chạy.', 'error');
  } finally {
    if (revision === csvRevision) setBatchBusy(false);
  }
}

sheetSelect.addEventListener('change', () => {
  if (selectedCsv && sheetSelect.value) selectCsv(selectedCsv, sheetSelect.value);
});
csvFile.addEventListener('change', () => selectCsv(csvFile.files?.[0] || null));
byId('file-remove').addEventListener('click', () => {
  csvFile.value = '';
  selectCsv(null);
});
for (const name of ['dragenter', 'dragover']) {
  csvDropzone.addEventListener(name, (e) => {
    e.preventDefault();
    csvDropzone.classList.add('dragover');
  });
}
for (const name of ['dragleave', 'drop']) {
  csvDropzone.addEventListener(name, (e) => {
    e.preventDefault();
    csvDropzone.classList.remove('dragover');
  });
}
csvDropzone.addEventListener('drop', (e) => {
  const file = e.dataTransfer?.files?.[0];
  if (file) selectCsv(file);
});
batchSubmit.addEventListener('click', async () => {
  const file = selectedCsv;
  const column = csvColumn.value;
  if (!file || !column || csvConfig.hidden || batchSubmit.disabled) return;
  const revision = csvRevision;
  batchController = new AbortController();
  clearBatchResult();
  setBatchStatus('Đang phân tích bình luận trong tệp…');
  setBatchBusy(true, 'Đang phân tích… Vui lòng giữ trang này mở.');
  try {
    const response = await fetch('/api/batch?column=' + encodeURIComponent(column) + '&filename=' + encodeURIComponent(file.name) + (sheetSelect.value && !byId('sheet-wrap').hidden ? '&sheet=' + encodeURIComponent(sheetSelect.value) : ''), {
      method: 'POST', headers: {'content-type': 'application/octet-stream'},
      body: file, signal: batchController.signal,
    });
    if (revision !== csvRevision) return;
    if (!response.ok) {
      const error = await response.json().catch(() => null);
      setBatchStatus([error?.message || 'Không phân tích được tệp.', error?.detail].filter(Boolean).join(' '), 'error');
      return;
    }
    setBatchStatus('Đang chuẩn bị kết quả phân loại…');
    const total = Number(response.headers.get('X-Total-Rows'));
    const valid = Number(response.headers.get('X-Valid-Rows'));
    const nonnegative = Number(response.headers.get('X-Nonnegative-Rows'));
    const negative = Number(response.headers.get('X-Negative-Rows'));
    const invalid = Number(response.headers.get('X-Invalid-Rows'));
    const summary = decodeSummaryHeader(response.headers.get('X-TextSense-Summary'));
    const blob = await response.blob();
    if (revision !== csvRevision) return;
    resultCsvBlob = blob;
    resultDownloadUrl = URL.createObjectURL(blob);
    byId('batch-download-xlsx').disabled = false;
    const download = byId('batch-download');
    download.href = resultDownloadUrl;
    const originalName = file.name.replace(/\.(csv|xlsx)$/i, '').replace(/[^\p{L}\p{N}_-]/gu, '_').slice(0, 55) || 'binh_luan';
    download.download = 'TextSense_' + originalName + '_ket_qua.csv';
    byId('batch-download-xlsx').dataset.filename = 'TextSense_' + originalName + '_ket_qua.xlsx';
    byId('batch-facts').textContent = formatNumber(valid) + '/' + formatNumber(total) + ' dòng đã phân tích';
    // Cập nhật dashboard từ số liệu tổng hợp do API trả về cho chính tệp này.
    const safeTotal = Number.isFinite(total) && total >= 0 ? total : 0;
    const safeValid = Number.isFinite(valid) && valid >= 0 ? valid : 0;
    const safeInvalid = Number.isFinite(invalid) && invalid >= 0 ? invalid : Math.max(0, safeTotal - safeValid);
    const safeNegative = Number.isFinite(negative) && negative >= 0 ? negative : 0;
    const safeNonnegative = Number.isFinite(nonnegative) && nonnegative >= 0 ? nonnegative : 0;
    const pct = (value, base) => base > 0 ? (value * 100 / base) : 0;
    const negativePct = pct(safeNegative, safeValid);
    const nonnegativePct = pct(safeNonnegative, safeValid);
    const validPct = pct(safeValid, safeTotal);
    const invalidPct = pct(safeInvalid, safeTotal);
    const percentText = (value) => value.toLocaleString('vi-VN', {minimumFractionDigits: 1, maximumFractionDigits: 1}) + '%';
    byId('dash-total').textContent = formatNumber(safeTotal);
    byId('dash-valid').textContent = formatNumber(safeValid);
    byId('dash-invalid').textContent = formatNumber(safeInvalid);
    byId('dash-valid-rate').textContent = percentText(validPct) + ' tổng số dòng';
    byId('dash-invalid-rate').textContent = percentText(invalidPct) + ' tổng số dòng';
    byId('donut-total').textContent = formatNumber(safeValid);
    byId('dash-negative-count').textContent = formatNumber(safeNegative);
    byId('dash-nonnegative-count').textContent = formatNumber(safeNonnegative);
    byId('dash-negative-pct').textContent = percentText(negativePct);
    byId('dash-nonnegative-pct').textContent = percentText(nonnegativePct);
    byId('batch-donut').style.setProperty('--negative-share', negativePct + '%');
    byId('batch-donut').setAttribute('aria-label', 'Có nội dung tiêu cực ' + percentText(negativePct) + ', Không phát hiện nội dung tiêu cực ' + percentText(nonnegativePct));
    byId('dash-negative-bar').style.width = negativePct + '%';
    byId('dash-nonnegative-bar').style.width = nonnegativePct + '%';
    const dominant = safeNegative > safeNonnegative ? 'Có nội dung tiêu cực' : safeNonnegative > safeNegative ? 'Không phát hiện nội dung tiêu cực' : 'hai nhóm có số lượng bằng nhau';
    const dominantPct = Math.max(negativePct, nonnegativePct);
    byId('dash-insight').textContent = safeValid
      ? 'Nhóm chiếm tỷ trọng lớn hơn: ' + dominant + (dominantPct ? ' (' + percentText(dominantPct) + ' số dòng hợp lệ).' : '.')
      : 'Không có dòng hợp lệ để thống kê nhãn.';
    if (summary) renderDatasetInsights(summary);
    else console.warn('TextSense: thiếu dữ liệu thống kê. Cần cập nhật đồng bộ serve_textsense.py và web/app.js.');
    byId('batch-facts').textContent += safeInvalid ? ' · ' + formatNumber(safeInvalid) + ' dòng chưa thể phân loại' : '';
    batchResult.hidden = false;
    const historySaved = response.headers.get('X-History-Saved') === 'true';
    setBatchStatus('Đã phân tích xong ' + formatNumber(valid) + ' bình luận.' +
      (summary ? '' : ' Chưa tải được thống kê chi tiết, nhưng bạn vẫn có thể tải CSV.') +
      (historySaved ? '' : ' Lưu ý: Lịch sử chưa được lưu vào SQL Server.'),
      historySaved ? 'success' : 'warning');
    try {
      setBatchBusy(true, 'Đang mở danh sách bình luận…');
      const index = await TextSenseCsv.indexBlob(blob);
      if (revision !== csvRevision) return;
      const columns = await TextSenseCsv.readRow(blob, index, 0);
      if (index.rowCount !== total) throw new Error('Số dòng kết quả không khớp dữ liệu phân loại.');
      if (columns.at(-1) !== 'Nhãn dự đoán TextSense (0/1)') throw new Error('Tệp kết quả không đúng định dạng.');
      const textColumnIndex = columns.indexOf(column);
      if (textColumnIndex < 0 || columns.length < 2) throw new Error('Không tìm thấy cột bình luận hoặc cột kết quả.');
      batchCsv = {blob, index, rowCount: index.rowCount, columns, textColumnIndex,
        resultIndex: columns.length - 1, page: 0, openRow: null};
      byId('batch-browse').hidden = false;
      byId('batch-jump-input').max = String(index.rowCount);
      await renderBatchPage(0);
    } catch (e) {
      byId('batch-browse').hidden = true;
      setBatchStatus('Đã phân tích xong nhưng không mở được phần xem từng dòng: ' + e.message, 'error');
    } finally {
      if (revision === csvRevision) setBatchBusy(false);
    }
    batchResult.scrollIntoView({behavior: prefersReducedMotion.matches ? 'auto' : 'smooth', block: 'start'});
  } catch (error) {
    if (revision === csvRevision && error.name !== 'AbortError')
      setBatchStatus('Không kết nối được máy chủ. Hãy kiểm tra TextSense và thử lại.', 'error');
  } finally {
    if (revision === csvRevision) setBatchBusy(false);
  }
});


// The original result stays as CSV for fast browsing. Excel export is created on demand
// on the local server, without calling the classifier again.
byId('batch-download-xlsx').addEventListener('click', async () => {
  const blob = resultCsvBlob;
  const button = byId('batch-download-xlsx');
  if (!blob || button.disabled) return;
  button.disabled = true;
  button.textContent = 'Đang tạo Excel…';
  setBatchStatus('Đang tạo tệp Excel từ kết quả đã phân tích…');
  try {
    const response = await fetch('/api/export-xlsx', {
      method: 'POST',
      headers: {'content-type': 'application/octet-stream'},
      body: blob
    });
    if (!response.ok) {
      const error = await response.json().catch(() => null);
      throw new Error([error?.message || 'Không tạo được Excel.', error?.detail].filter(Boolean).join(' '));
    }
    const excelBlob = await response.blob();
    if (blob !== resultCsvBlob) return;
    const url = URL.createObjectURL(excelBlob);
    const link = document.createElement('a');
    link.href = url;
    link.download = button.dataset.filename || 'TextSense_ket_qua.xlsx';
    document.body.append(link);
    link.click();
    link.remove();
    window.setTimeout(() => URL.revokeObjectURL(url), 60000);
    setBatchStatus('Đã tạo tệp Excel. Bạn có thể tải CSV hoặc Excel.', 'success');
  } catch (error) {
    if (blob === resultCsvBlob) setBatchStatus(error.message || 'Không tạo được tệp Excel.', 'error');
  } finally {
    if (blob === resultCsvBlob) {
      button.disabled = false;
      button.textContent = 'Tải Excel ↓';
    }
  }
});

// Xem từng dòng kết quả; chi index vi tri byte, khong render 300.000 dong len DOM.
function labelFromRecord(record) {
  const value = (record[batchCsv.resultIndex] || '').trim();
  if (value === '1') return 'negative';
  if (value === '0') return 'nonnegative';
  return null;
}
function rowText(record) {
  return record[batchCsv.textColumnIndex] || '';
}
function rowStatus(record) {
  return record[batchCsv.resultIndex] ? 'Nhãn không hợp lệ trong dữ liệu' : 'Không có kết quả cho bình luận này';
}
function appendText(tag, className, content) {
  const el = document.createElement(tag);
  el.className = className;
  el.textContent = content;
  return el;
}
async function getBatchRecord(rowNumber) {
  if (!batchCsv || rowNumber < 1 || rowNumber > batchCsv.rowCount) throw new Error('Số dòng ngoài phạm vi.');
  const data = batchCsv;
  return TextSenseCsv.readRow(data.blob, data.index, rowNumber);
}
async function renderBatchPage(page) {
  const data = batchCsv;
  if (!data) return;
  const maximum = Math.max(0, Math.ceil(data.rowCount / PAGE_SIZE) - 1);
  const currentPage = Math.max(0, Math.min(maximum, page));
  data.page = currentPage;
  const request = ++browseRevision;
  const first = currentPage * PAGE_SIZE + 1;
  const last = Math.min(data.rowCount, first + PAGE_SIZE - 1);
  const fragment = document.createDocumentFragment();
  for (let rowNumber = first; rowNumber <= last; rowNumber++) {
    const record = await TextSenseCsv.readRow(data.blob, data.index, rowNumber);
    if (request !== browseRevision || data !== batchCsv) return;
    const key = labelFromRecord(record);
    const item = document.createElement('article');
    item.className = 'batch-row-card';
    item.id = 'batch-row-' + rowNumber;
    const header = document.createElement('div');
    header.className = 'batch-row-head';
    header.append(appendText('span','batch-row-number','Bình luận số ' + formatNumber(rowNumber)));
    header.append(appendText('span','batch-row-badge ' + (key || 'invalid'), key ? outcomes[key].title : 'Không phân loại được'));
    item.append(header);
    item.append(appendText('p','batch-row-snippet',rowText(record).trim() || '(Không có văn bản)'));
    const footer = document.createElement('div');
    footer.className = 'batch-row-footer';
    footer.append(appendText('span','batch-row-status',key ? 'Đã phân loại' : rowStatus(record))); 
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'button secondary row-view-button';
    button.textContent = 'Xem kết quả →';
    button.addEventListener('click', () => openBatchRow(rowNumber));
    footer.append(button);
    item.append(footer);
    fragment.append(item);
  }
  byId('batch-rows').replaceChildren(fragment);
  byId('batch-page-label').textContent = 'Dòng ' + formatNumber(first) + '–' + formatNumber(last) + ' / ' + formatNumber(data.rowCount);
  byId('batch-page-prev').disabled = currentPage === 0;
  byId('batch-page-next').disabled = currentPage >= maximum;
}
async function openBatchRow(rowNumber) {
  const data = batchCsv;
  if (!data || !Number.isSafeInteger(rowNumber) || rowNumber < 1 || rowNumber > data.rowCount) return;
  const request = ++browseRevision;
  try {
    const record = await getBatchRecord(rowNumber);
    if (request !== browseRevision || batchCsv !== data) return;
    data.openRow = rowNumber;
    const key = labelFromRecord(record);
    const text = rowText(record);
    if (!key) {
      resultAnimation += 1;
      resultOrigin = 'batch';
      lastResult = null;
      byId('result-label').textContent = 'Kết quả · Bình luận số ' + formatNumber(rowNumber);
      byId('back-input').hidden = true;
      byId('back-batch').hidden = false;
      byId('new-comment').hidden = true;
      byId('report').hidden = true;
      byId('batch-detail-nav').hidden = false;
      byId('batch-detail-position').textContent = formatNumber(rowNumber) + ' / ' + formatNumber(data.rowCount);
      byId('batch-detail-prev').disabled = rowNumber <= 1;
      byId('batch-detail-next').disabled = rowNumber >= data.rowCount;
      resultTitle.textContent = 'Chưa có kết quả';
      byId('result-detail').textContent = rowStatus(record) + '. Hãy kiểm tra nội dung hoặc chọn dòng khác.';
      renderSentenceBreakdown(null);
      byId('history-warning').hidden = true;
      byId('result-quote').textContent = text;
      byId('entry').hidden = true;
      result.hidden = false;
      setState('sad');
      setMode('single');
      requestAnimationFrame(() => result.scrollIntoView({behavior: prefersReducedMotion.matches ? 'auto' : 'smooth'}));
      return;
    }
    byId('report').hidden = false;
    showClassification({label: key, text}, 'batch', rowNumber);
    loadBatchSentenceBreakdown(text, resultAnimation, rowNumber);
  } catch (e) {
    setBatchStatus('Không mở được dòng đã chọn: ' + e.message, 'error');
  }
}
function returnToBatch() {
  resultAnimation += 1;
  navigateToMode('batch');
  requestAnimationFrame(() => {
    const el = byId('batch-browse');
    if (!el.hidden) el.scrollIntoView({behavior: prefersReducedMotion.matches ? 'auto' : 'smooth', block: 'start'});
  });
}
byId('batch-page-prev').addEventListener('click', () => renderBatchPage((batchCsv?.page || 0) - 1));
byId('batch-page-next').addEventListener('click', () => renderBatchPage((batchCsv?.page || 0) + 1));
function jumpToBatchRow() {
  if (!batchCsv) return;
  const row = Number(byId('batch-jump-input').value);
  if (!Number.isSafeInteger(row) || row < 1 || row > batchCsv.rowCount) {
    setBatchStatus('Số dòng phải nằm trong khoảng 1–' + formatNumber(batchCsv.rowCount) + '.', 'error');
    return;
  }
  const targetPage = Math.floor((row - 1) / PAGE_SIZE);
  renderBatchPage(targetPage).then(() => {
    const targetCard = byId('batch-row-' + row);
    if (targetCard) {
      targetCard.scrollIntoView({behavior: prefersReducedMotion.matches ? 'auto' : 'smooth', block: 'center'});
      targetCard.classList.add('batch-row-highlight');
      window.setTimeout(() => {
        targetCard.classList.remove('batch-row-highlight');
      }, 2500);
    } else {
      const target = byId('batch-rows');
      target.scrollIntoView({behavior: prefersReducedMotion.matches ? 'auto' : 'smooth', block: 'start'});
    }
  });
}
byId('batch-jump-go').addEventListener('click', jumpToBatchRow);
byId('batch-jump-input').addEventListener('keydown', (event) => {
  if (event.key === 'Enter') {event.preventDefault(); jumpToBatchRow();}
});

window.addEventListener('beforeunload', () => {
  if (resultDownloadUrl) URL.revokeObjectURL(resultDownloadUrl);
});
