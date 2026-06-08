const thread = document.getElementById('thread');
const composerStack = document.querySelector('.composer-stack');
const composerShell = document.querySelector('.composer-shell');
const topbar = document.querySelector('.topbar');
const controlDock = document.querySelector('.control-dock');
const composer = document.getElementById('composer');
const textarea = document.getElementById('text');
const sendButton = document.getElementById('send');
const stopButton = document.getElementById('stop');
const attachButton = document.getElementById('attach');
const fileInput = document.getElementById('file-input');
const attachmentTray = document.getElementById('attachment-tray');
const notice = document.getElementById('notice');
const queuedSend = document.getElementById('queued-send');
const queuedSendLabel = document.getElementById('queued-send-label');
const queuedSendList = document.getElementById('queued-send-list');
const topStatus = document.getElementById('top-status');
const contextQuickCard = document.getElementById('context-quick-card');
const contextQuickCompact = contextQuickCard;
const reasoningBadge = document.getElementById('reasoning-badge');
const reasoningMenuCard = document.getElementById('reasoning-menu-card');
const reasoningText = document.getElementById('reasoning-text');
const modelBadge = document.getElementById('model-badge');
const modelMenuCard = document.getElementById('model-menu-card');
const modelText = document.getElementById('model-text');
const threadButton = document.getElementById('thread-button');
const newThreadButton = document.getElementById('new-thread');
const settingsButton = document.getElementById('settings');
const settingsCard = document.getElementById('settings-card');
const themeSelect = document.getElementById('theme-select');
const settingSuperModeSwitch = document.getElementById('setting-super-mode');
const threadCurrentPin = document.getElementById('thread-current-pin');
const threadNameEl = document.getElementById('thread-name');
const threadMenuScrim = document.getElementById('thread-menu-scrim');
const threadMenu = document.getElementById('thread-menu');
const threadActionCard = document.getElementById('thread-action-card');
const threadActionArchive = document.getElementById('thread-action-archive');
const threadActionArchiveIcon = document.getElementById('thread-action-archive-icon');
const threadActionRename = document.getElementById('thread-action-rename');
const threadActionRenameIcon = document.getElementById('thread-action-rename-icon');
const threadActionPinToggle = document.getElementById('thread-action-pin-toggle');
const threadActionPinToggleIcon = document.getElementById('thread-action-pin-toggle-icon');
const threadActionPinToggleText = document.getElementById('thread-action-pin-toggle-text');
const threadRenameInput = document.getElementById('thread-rename-input');
const threadRenameCancel = document.getElementById('thread-rename-cancel');
const threadRenameSave = document.getElementById('thread-rename-save');
const queryToken = new URLSearchParams(location.search).get('token') || '';
if (queryToken) localStorage.setItem('codexGo.token', queryToken);
const token = queryToken || localStorage.getItem('codexGo.token') || '';
const ROUTE_STORAGE_KEY = 'codexGo.apiRoutes.v1';
const normalizeBaseUrl = value => String(value || '').trim().replace(/\/+$/, '');
const currentApiBase = normalizeBaseUrl(location.origin);
let apiCandidates = [];
let activeApiBase = currentApiBase;
let activeApiLabel = '本地';
let activeApiKind = 'local';
const apiUrl = path => `${activeApiBase}${path}`;
const target = 'codex';
const CONTEXT_COMPACT_COMMAND = '/压缩';

let selectedThreadId = localStorage.getItem('codexGo.selectedThread') || '';
let pendingNewThread = null;

function isPendingNewThreadView() {
  return Boolean(pendingNewThread && !selectedThreadId);
}
let knownThreads = [];
let pollTimer = null;
let runDurationTimer = null;
let pollAttempts = 0;
let pollGeneration = 0;
let activeWatch = null;
let activeAssistant = null;
let lastPreview = '';
let resolvingPermission = false;
let pendingAttachments = [];
let queuedSends = [];
let queuedSendRefreshTimer = null;
let queuedSendMirrorTimer = null;
let queuedSendRefreshBusy = false;
let queuedSendLoading = false;
let queuedSendActionBusyKey = '';
const queuedSendsCache = new Map();
const guidedQueuedSendKeys = new Set();
const QUEUED_SENDS_CACHE_MAX = 24;
let historyRequestId = 0;
let syncRequestId = 0;
let syncedThreadId = '';
let autoRefreshTimer = null;
let autoRefreshBusy = false;
let guiStateTimer = null;
let guiStateBusy = false;
let lastGuiStateSignature = '';
let threadStateTimer = null;
let threadStateBusy = false;
let appResumeRefreshTimer = null;
let routeMonitorBusy = false;
let actionThreadId = '';
let threadLongPressTimer = null;
let threadLongPressStart = null;
let threadLongPressOpened = false;
let reasoningLongPressTimer = null;
let reasoningLongPressStart = null;
let reasoningLongPressOpened = false;
let modelLongPressTimer = null;
let modelLongPressStart = null;
let modelLongPressOpened = false;
let suppressThreadClickUntil = 0;
let suppressReasoningClickUntil = 0;
let suppressModelClickUntil = 0;
let lastStatusSignature = '';
let topNoticeUntil = 0;
let topStatusState = '已连接';
let topStatusType = '';
let lastContextUsage = null;
let currentReasoningMode = null;
let switchingReasoningMode = false;
let currentModelInfo = null;
let switchingModel = false;
let foregroundDotBusy = false;
let authExpiredNoticeShown = false;
let keyboardMonitorTimer = null;
let keyboardAlignmentTimers = [];
let keyboardPinTimers = [];
let keyboardAlignRaf = 0;
let keyboardFocusStartedAt = 0;
let keyboardComposerRevealDone = false;
let layoutViewportBaselineHeight = Math.round(window.innerHeight || document.documentElement.clientHeight || 0);
let virtualKeyboardInset = 0;
let composerFlowRect = null;
let composerStackHeightLocked = 0;
let keyboardOverlayOpen = false;
let threadBottomScrollTimers = [];
let threadStickToBottomUntil = 0;
let lastTextareaFocusPrepareAt = 0;
let lastOutsideComposerTouchAt = 0;
let suppressNextTextareaBlurRestore = false;
let composerImeActive = false;
let composerImeEndedAt = 0;
const STORAGE_PREFIX = 'codexGoChat.v3';
const GROUPS_STORAGE_KEY = 'codexGo.threadGroups.open.v1';
const THREAD_NOTICE_STORAGE_KEY = 'codexGo.threadCompleteNotices.v1';
const REASONING_OVERRIDE_STORAGE_KEY = 'codexGo.reasoningOverrides.v1';
const MODEL_OVERRIDE_STORAGE_KEY = 'codexGo.modelOverrides.v1';
const APPEARANCE_SETTINGS_STORAGE_KEY = 'codexGo.appearanceSettings.v1';
const SUPER_MODE_STORAGE_KEY = 'codexGo.superMode.v1';
const THEME_OPTIONS = ['native', 'workbench', 'minimal', 'dark', 'luxe-dark', 'dracula', 'graphite'];
const THEME_ICON_VERSION = '20260608i';
const THREAD_NOTICE_MAX_AGE_MS = 30 * 60 * 1000;
const THREAD_SPINNER_MS = 850;
const LOCAL_STOP_SUPPRESS_MS = 2 * 60 * 1000;
const REASONING_MODE_OPTIONS = [
  { key: 'low', label: '低', displayName: '低' },
  { key: 'medium', label: '中', displayName: '中' },
  { key: 'high', label: '高', displayName: '高' },
  { key: 'xhigh', label: '超高', displayName: '超高' },
];
let modelMenuOptions = [];
const browserUserAgent = window.navigator.userAgent || '';
const isChromeKeyboardBrowser = /\b(?:Chrome|CriOS|Chromium)\//.test(browserUserAgent) && !/\b(?:Edg|EdgA|EdgiOS|OPR|SamsungBrowser)\//.test(browserUserAgent);
const isAndroidKeyboardBrowser = isChromeKeyboardBrowser && /\bAndroid\b/i.test(browserUserAgent);
const isIOSMobileBrowser = /\biPhone\b/i.test(browserUserAgent)
  || /\biPod\b/i.test(browserUserAgent)
  || (/\biPad\b/i.test(browserUserAgent) && Math.min(window.screen.width, window.screen.height) < 900);
document.documentElement.classList.toggle('android-keyboard-mode', isAndroidKeyboardBrowser);
document.body.classList.toggle('chrome-keyboard-mode', isChromeKeyboardBrowser);
document.body.classList.toggle('android-keyboard-mode', isAndroidKeyboardBrowser);
document.body.classList.toggle('ios-keyboard-mode', isIOSMobileBrowser);
if (navigator.virtualKeyboard) {
  try { navigator.virtualKeyboard.overlaysContent = true; } catch {}
}
const ANDROID_APPEARANCE_DEFAULTS_STORAGE_KEY = 'codexGo.androidAppearanceDefaults.v1';
let hasLocalAppearanceSettings = localStorage.getItem(APPEARANCE_SETTINGS_STORAGE_KEY) !== null;
let appearanceSettings = readAppearanceSettings();
let superModeEnabled = readSuperModeEnabled();
let localOnlyMode = true;
let apiConfigRefreshBusy = false;
let lastApiConfigRefreshAt = 0;
const API_CONFIG_REFRESH_MIN_MS = 15000;
const hasSavedProjectGroupState = localStorage.getItem(GROUPS_STORAGE_KEY) !== null;
const isStandalone = Boolean(window.navigator.standalone) || window.matchMedia('(display-mode: standalone)').matches;
document.body.classList.toggle('standalone', isStandalone);
ensureAndroidAppearanceDefaults();
applyAppearanceSettings();
applySuperModeSettings();

if (queryToken) {
  document.cookie = `codexGoToken=${encodeURIComponent(queryToken)}; Path=/; SameSite=Lax; Max-Age=31536000`;
}
let openProjectKeys = readOpenProjectKeys();
const threadRuntimeStates = new Map();
const locallyStoppedThreads = new Map();
let completedThreadNoticeTimes = new Map();
const completedThreadIds = readCompletedThreadIds();
let lastThreadMenuSignature = '';

function escapeHtml(value) {
  return String(value || '').replace(/[&<>"]/g, char => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[char]));
}
function renderInlineMarkdown(text) {
  let html = escapeHtml(text);
  const codeStore = [];
  html = html.replace(/`([^`]+)`/g, (_, code) => {
    const id = codeStore.push(`<code>${code}</code>`) - 1;
    return `@@CODE${id}@@`;
  });
  html = html.replace(/\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g, '<a href="$2" target="_blank" rel="noreferrer">$1</a>');
  html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
  html = html.replace(/@@CODE(\d+)@@/g, (_, index) => codeStore[Number(index)] || '');
  return html;
}
function splitMarkdownTableRow(line) {
  let value = String(line || '').trim();
  if (!value.includes('|')) return [];
  if (value.startsWith('|')) value = value.slice(1);
  if (value.endsWith('|')) value = value.slice(0, -1);
  const cells = [];
  let cell = '';
  for (let index = 0; index < value.length; index += 1) {
    const char = value[index];
    const next = value[index + 1];
    if (char === '\\' && (next === '|' || next === '\\')) {
      cell += next;
      index += 1;
      continue;
    }
    if (char === '|') {
      cells.push(cell.trim());
      cell = '';
      continue;
    }
    cell += char;
  }
  cells.push(cell.trim());
  return cells;
}
function markdownTableDelimiterInfo(line) {
  const cells = splitMarkdownTableRow(line);
  if (cells.length < 2 || !cells.every(cell => /^:?-{3,}:?$/.test(cell.replace(/\s+/g, '')))) return null;
  return cells.map(cell => {
    const normalized = cell.replace(/\s+/g, '');
    if (/^:-+:$/.test(normalized)) return 'center';
    if (/^-+:$/.test(normalized)) return 'right';
    return /^:-+$/.test(normalized) ? 'left' : '';
  });
}
function isMarkdownTableStart(lines, index) {
  const header = splitMarkdownTableRow(lines[index]);
  const alignments = markdownTableDelimiterInfo(lines[index + 1]);
  if (!alignments || header.length < 2) return null;
  return { header, alignments };
}
function tableCellClass(alignments, index) {
  const alignment = alignments[index] || '';
  if (alignment === 'center') return ' class="align-center"';
  if (alignment === 'right') return ' class="align-right"';
  return '';
}
function renderMarkdownTable(header, alignments, rows) {
  const width = Math.max(header.length, alignments.length, ...rows.map(row => row.length));
  const pad = row => Array.from({ length: width }, (_, index) => row[index] || '');
  const head = pad(header).map((cell, index) => `<th${tableCellClass(alignments, index)}>${renderInlineMarkdown(cell)}</th>`).join('');
  const body = rows.map(row => `<tr>${pad(row).map((cell, index) => `<td${tableCellClass(alignments, index)}>${renderInlineMarkdown(cell)}</td>`).join('')}</tr>`).join('');
  return `<div class="table-scroll"><table><thead><tr>${head}</tr></thead><tbody>${body}</tbody></table></div>`;
}
function extractTagContent(text, tag) {
  const match = String(text || '').match(new RegExp(`<${tag}>([\\s\\S]*?)<\\/${tag}>`, 'i'));
  return match ? match[1].trim() : '';
}
function parseMemoryCitationEntries(block) {
  const entriesText = extractTagContent(block, 'citation_entries');
  if (!entriesText) return [];
  return entriesText.split(/\n+/).map(line => {
    const trimmed = line.trim();
    if (!trimmed) return null;
    const match = trimmed.match(/^(.*?)(?::(\d+(?:-\d+)?))?\|note=\[([\s\S]*)\]$/);
    if (match) return { path: match[1].trim(), lines: match[2] || '', note: match[3].trim() };
    return { path: trimmed, lines: '', note: '' };
  }).filter(Boolean);
}
function renderMemoryCitationCard(block) {
  const entries = parseMemoryCitationEntries(block);
  const title = entries.length ? '记忆引用' : '记忆已更新';
  const items = entries.map(entry => {
    const lineText = entry.lines ? ` <span class="memory-citation-count">${escapeHtml(entry.lines)} 行</span>` : '';
    const note = entry.note ? `<div class="memory-citation-note">${escapeHtml(entry.note)}</div>` : '';
    return `<div class="memory-citation-item"><div class="memory-citation-path">${escapeHtml(entry.path)}${lineText}</div>${note}</div>`;
  }).join('');
  const empty = '<div class="memory-citation-empty">本轮有记忆信息，但没有可显示的引用条目</div>';
  return `<details class="memory-citation-card"><summary><span class="memory-citation-icon">↺</span><span class="memory-citation-title">${title}</span><span class="memory-citation-count">${entries.length} 条</span></summary>${items ? `<div class="memory-citation-list">${items}</div>` : empty}</details>`;
}
function splitMemoryCitationBlocks(markdown) {
  const text = String(markdown || '');
  const parts = [];
  const pattern = /<oai-mem-citation>[\s\S]*?<\/oai-mem-citation>/gi;
  let lastIndex = 0;
  let match;
  while ((match = pattern.exec(text))) {
    if (match.index > lastIndex) parts.push({ type: 'markdown', value: text.slice(lastIndex, match.index) });
    parts.push({ type: 'memory', value: match[0] });
    lastIndex = pattern.lastIndex;
  }
  if (lastIndex < text.length) parts.push({ type: 'markdown', value: text.slice(lastIndex) });
  return parts;
}
function markdownToHtmlWithoutMemory(markdown) {
  const lines = String(markdown || '').replace(/\r\n/g, '\n').split('\n');
  let html = '', paragraph = [], listType = null, inCode = false, codeLines = [];
  const flushParagraph = () => { if (paragraph.length) { html += `<p>${renderInlineMarkdown(paragraph.join(' '))}</p>`; paragraph = []; } };
  const closeList = () => { if (listType) { html += `</${listType}>`; listType = null; } };
  for (let index = 0; index < lines.length; index += 1) {
    const line = lines[index];
    const trimmed = line.trim();
    if (trimmed.startsWith('```')) {
      if (inCode) { html += `<pre><code>${escapeHtml(codeLines.join('\n'))}</code></pre>`; codeLines = []; inCode = false; }
      else { flushParagraph(); closeList(); inCode = true; }
      continue;
    }
    if (inCode) { codeLines.push(line); continue; }
    const table = index + 1 < lines.length ? isMarkdownTableStart(lines, index) : null;
    if (table) {
      flushParagraph();
      closeList();
      const rows = [];
      index += 2;
      while (index < lines.length) {
        const rowCells = splitMarkdownTableRow(lines[index]);
        if (rowCells.length < 2) { index -= 1; break; }
        rows.push(rowCells);
        index += 1;
      }
      if (index >= lines.length) index = lines.length - 1;
      html += renderMarkdownTable(table.header, table.alignments, rows);
      continue;
    }
    if (!trimmed) { flushParagraph(); closeList(); continue; }
    const heading = trimmed.match(/^(#{1,3})\s+(.+)$/);
    if (heading) { flushParagraph(); closeList(); const n = heading[1].length; html += `<h${n}>${renderInlineMarkdown(heading[2])}</h${n}>`; continue; }
    const quote = trimmed.match(/^>\s?(.+)$/);
    if (quote) { flushParagraph(); closeList(); html += `<blockquote>${renderInlineMarkdown(quote[1])}</blockquote>`; continue; }
    const bullet = trimmed.match(/^[-*]\s+(.+)$/);
    const ordered = trimmed.match(/^\d+[.)]\s+(.+)$/);
    if (bullet || ordered) {
      flushParagraph();
      const desired = bullet ? 'ul' : 'ol';
      if (listType !== desired) { closeList(); html += `<${desired}>`; listType = desired; }
      html += `<li>${renderInlineMarkdown((bullet || ordered)[1])}</li>`;
      continue;
    }
    closeList(); paragraph.push(trimmed);
  }
  if (inCode) html += `<pre><code>${escapeHtml(codeLines.join('\n'))}</code></pre>`;
  flushParagraph(); closeList();
  return html;
}
function markdownToHtml(markdown) {
  const parts = splitMemoryCitationBlocks(markdown);
  if (!parts.some(part => part.type === 'memory')) return markdownToHtmlWithoutMemory(markdown) || '<p></p>';
  const html = parts.map(part => part.type === 'memory'
    ? renderMemoryCitationCard(part.value)
    : markdownToHtmlWithoutMemory(part.value)).join('');
  return html || '<p></p>';
}
function setMarkdown(el, markdown) { el.innerHTML = markdownToHtml(markdown); }
function lockViewportZoom() {
  let lastTouchEndAt = 0;
  document.addEventListener('gesturestart', event => event.preventDefault(), { passive: false });
  document.addEventListener('gesturechange', event => event.preventDefault(), { passive: false });
  document.addEventListener('gestureend', event => event.preventDefault(), { passive: false });
  document.addEventListener('touchmove', event => {
    if (event.touches && event.touches.length > 1) event.preventDefault();
  }, { passive: false });
  document.addEventListener('touchend', event => {
    const now = Date.now();
    if (now - lastTouchEndAt <= 300) event.preventDefault();
    lastTouchEndAt = now;
  }, { passive: false });
}
function lockComposerDrag() {
  if (!composerShell) return;
  const dragThreshold = 2;
  let touchStart = null;
  let pointerStart = null;
  const isEditableTextareaTarget = target => Boolean(target && target === textarea);
  const isComposerTarget = target => Boolean(target && composer.contains(target) && !isEditableTextareaTarget(target));
  const resetTouch = () => { touchStart = null; };
  const resetPointer = () => { pointerStart = null; };

  composerShell.addEventListener('touchstart', event => {
    if (!isComposerTarget(event.target) || !event.touches || !event.touches.length) return;
    const touch = event.touches[0];
    touchStart = { x: touch.clientX, y: touch.clientY };
  }, { passive: true });
  composerShell.addEventListener('touchmove', event => {
    if (!touchStart || !event.touches || !event.touches.length || !isComposerTarget(event.target)) return;
    const touch = event.touches[0];
    const dx = Math.abs(touch.clientX - touchStart.x);
    const dy = Math.abs(touch.clientY - touchStart.y);
    if (dx < dragThreshold && dy < dragThreshold) return;
    event.preventDefault();
    event.stopPropagation();
    if (document.activeElement === textarea) alignComposerForKeyboard();
  }, { passive: false });
  composerShell.addEventListener('touchend', resetTouch, { passive: true });
  composerShell.addEventListener('touchcancel', resetTouch, { passive: true });

  composerShell.addEventListener('pointerdown', event => {
    if (event.pointerType !== 'touch' || !isComposerTarget(event.target)) return;
    pointerStart = { id: event.pointerId, x: event.clientX, y: event.clientY };
  });
  composerShell.addEventListener('pointermove', event => {
    if (!pointerStart || event.pointerId !== pointerStart.id || !isComposerTarget(event.target)) return;
    const dx = Math.abs(event.clientX - pointerStart.x);
    const dy = Math.abs(event.clientY - pointerStart.y);
    if (dx < dragThreshold && dy < dragThreshold) return;
    event.preventDefault();
    event.stopPropagation();
  });
  composerShell.addEventListener('pointerup', resetPointer);
  composerShell.addEventListener('pointercancel', resetPointer);
}
function lockPageScrollToThread() {
  let pageTouch = null;
  const verticalScrollSelector = '.thread, .thread-menu, .steps, textarea';
  const horizontalScrollSelector = '.top-actions, .process-tool-row, .table-scroll, .attachment-tray';
  const resetPageTouch = () => { pageTouch = null; };
  const preventPageMove = event => {
    event.preventDefault();
    event.stopPropagation();
    if (typeof keepLayoutViewportPinned === 'function') keepLayoutViewportPinned();
  };
  const nearest = (target, selector) => {
    if (!target || typeof target.closest !== 'function') return null;
    return target.closest(selector);
  };
  const canScrollVertically = (el, deltaY) => {
    if (!el) return false;
    const maxScroll = Math.max(0, el.scrollHeight - el.clientHeight);
    if (maxScroll <= 1) return false;
    if (deltaY > 0 && el.scrollTop <= 0) return false;
    if (deltaY < 0 && el.scrollTop >= maxScroll - 1) return false;
    return true;
  };
  const hasTextareaSelection = el => {
    if (!el || typeof el.selectionStart !== 'number' || typeof el.selectionEnd !== 'number') return false;
    return el.selectionStart !== el.selectionEnd;
  };

  document.addEventListener('touchstart', event => {
    if (!event.touches || event.touches.length !== 1) {
      resetPageTouch();
      return;
    }
    const touch = event.touches[0];
    pageTouch = {
      x: touch.clientX,
      y: touch.clientY,
      startedAt: performance.now(),
      verticalTarget: nearest(event.target, verticalScrollSelector),
      horizontalTarget: nearest(event.target, horizontalScrollSelector),
      editableTarget: nearest(event.target, 'textarea'),
    };
  }, { passive: true, capture: true });

  document.addEventListener('touchmove', event => {
    if (!event.touches || event.touches.length !== 1) return;
    if (!pageTouch) {
      preventPageMove(event);
      return;
    }
    const touch = event.touches[0];
    const dx = touch.clientX - pageTouch.x;
    const dy = touch.clientY - pageTouch.y;
    const verticalTarget = pageTouch.verticalTarget && document.contains(pageTouch.verticalTarget)
      ? pageTouch.verticalTarget
      : nearest(event.target, verticalScrollSelector);
    const horizontalTarget = pageTouch.horizontalTarget && document.contains(pageTouch.horizontalTarget)
      ? pageTouch.horizontalTarget
      : nearest(event.target, horizontalScrollSelector);
    const editableTarget = pageTouch.editableTarget && document.contains(pageTouch.editableTarget)
      ? pageTouch.editableTarget
      : nearest(event.target, 'textarea');

    if (editableTarget) {
      pageTouch.x = touch.clientX;
      pageTouch.y = touch.clientY;
      return;
    }
    if (horizontalTarget && Math.abs(dx) > Math.abs(dy)) {
      pageTouch.x = touch.clientX;
      pageTouch.y = touch.clientY;
      return;
    }
    if (verticalTarget && Math.abs(dy) >= Math.abs(dx) && canScrollVertically(verticalTarget, dy)) {
      pageTouch.x = touch.clientX;
      pageTouch.y = touch.clientY;
      return;
    }
    preventPageMove(event);
  }, { passive: false, capture: true });

  document.addEventListener('touchend', resetPageTouch, { passive: true, capture: true });
  document.addEventListener('touchcancel', resetPageTouch, { passive: true, capture: true });
}
function clampNumber(value, min, max) {
  const number = Number(value);
  if (!Number.isFinite(number)) return min;
  return Math.max(min, Math.min(max, number));
}
function formatTokenCount(value) {
  const number = Number(value);
  if (!Number.isFinite(number) || number <= 0) return '--';
  if (number >= 1000000) return `${(number / 1000000).toFixed(number >= 10000000 ? 0 : 1)}M`;
  if (number >= 1000) return `${Math.round(number / 1000)}k`;
  return String(Math.round(number));
}
function emptyContextUsage() {
  return { available: true, percent: 0, usedTokens: 0, windowTokens: 0 };
}

function resetPendingNewThreadIndicators() {
  renderContextIndicator(emptyContextUsage());
  lastGuiStateSignature = '';
  lastStatusSignature = '';
  refreshGuiState({ force: true });
}

function contextColor(percent) {
  const value = clampNumber(percent, 0, 100);
  if (value < 45) return 'color(display-p3 .42 1 .68)';
  if (value < 70) {
    const t = (value - 45) / 25;
    const hue = Math.round(142 - (94 * t));
    return `hsl(${hue} 92% 64%)`;
  }
  const t = (value - 70) / 30;
  const hue = Math.round(48 - (42 * t));
  return `hsl(${hue} 94% 63%)`;
}
function renderContextIndicator(context = lastContextUsage) {
  lastContextUsage = context || null;
  const hasContext = Boolean(context && context.available && Number.isFinite(Number(context.percent)));
  const percent = hasContext ? clampNumber(context.percent, 0, 100) : 0;
  const rounded = Math.round(percent);
  const color = hasContext ? contextColor(percent) : 'rgba(161,161,170,.72)';
  const used = hasContext ? formatTokenCount(context.usedTokens) : '--';
  const total = hasContext ? formatTokenCount(context.windowTokens) : '--';
  const percentText = hasContext ? `${rounded}%` : '--';
  const usedText = hasContext ? used : '--';
  const contextLevel = hasContext
    ? ` level-${percent >= 88 ? 'critical' : percent >= 70 ? 'high' : percent >= 45 ? 'medium' : 'low'}`
    : '';
  const detail = hasContext
    ? `当前上下文已使用 ${rounded}%（${used} / ${total} tokens）`
    : '暂未读到上下文用量';

  topStatus.className = `context-status${contextLevel}${hasContext ? '' : ' is-unknown'}${topStatusType ? ` state-${topStatusType}` : ''}`;
  topStatus.style.setProperty('--context-progress', `${percent * 3.6}deg`);
  topStatus.style.setProperty('--context-ratio', `${percent}%`);
  topStatus.style.setProperty('--context-color', color);
  topStatus.innerHTML = `<span class="context-ring" aria-hidden="true"></span><span class="context-text"><span class="context-percent">${percentText}</span><span class="context-sep">/</span><span class="context-used">${usedText}</span></span>`;
  topStatus.title = `${topStatusState || '已连接'} · ${detail}`;
  topStatus.setAttribute('aria-label', detail);
}
function updateContextFromStatus(data) {
  if (data && data.context) renderContextIndicator(data.context);
  updateReasoningFromStatus(data);
  updateModelFromStatus(data);
}
function guiStateSignature(data) {
  if (!data || !data.available) return '';
  return [
    data.activeThreadId || '',
    data.footerText || '',
    data.model?.displayName || data.modelDisplayName || '',
    data.reasoningMode?.key || data.reasoningLabel || '',
    data.permissionRequest?.callId || '',
    data.permissionRequest?.pending ? 'permission-pending' : '',
    data.updatedAt || '',
  ].join('|');
}
async function refreshGuiState(options = {}) {
  const pendingNew = isPendingNewThreadView();
  if ((!selectedThreadId && !pendingNew) || guiStateBusy || (document.hidden && !options.force)) return;
  guiStateBusy = true;
  const threadId = selectedThreadId;
  try {
    const params = new URLSearchParams({ token, thread: threadId });
    const response = await fetchApi(`/codex/gui-status?${params}`, {
      cache: 'no-store',
      apiTimeoutMs: options.force ? 5000 : 2800,
      routeSwitchQuiet: true,
      retryProbeTimeoutMs: 600,
    });
    const data = await response.json().catch(() => ({}));
    if (threadId !== selectedThreadId || !response.ok || !data.ok || !data.available) return;
    if (data.activeThreadId && data.activeThreadId !== threadId && !pendingNew) {
      syncedThreadId = '';
      lastGuiStateSignature = guiStateSignature(data);
      return;
    }
    const signature = guiStateSignature(data);
    if (!options.force && signature && signature === lastGuiStateSignature) return;
    lastGuiStateSignature = signature;
    if (data.reasoningMode?.available) {
      const mode = { ...data.reasoningMode, gui: true };
      writeReasoningOverride(threadId, mode);
      renderReasoningBadge(mode);
    }
    if (data.model?.available) {
      const model = { ...data.model, gui: true };
      writeModelOverride(threadId, model);
      renderModelBadge(model);
    }
    if (data.permissionRequest?.pending && !activeAssistant) {
      activeAssistant = messageEl('assistant', data.permissionRequest.text || data.permissionRequest.justification || 'Codex 正在等待确认。', { label: 'Codex · 等待确认', pending: true });
      activeWatch = { since: new Date().toISOString(), threadId };
      setActiveRunStart(activeWatch.since, Date.now());
      updateComposerAction();
    }
    if (data.permissionRequest?.pending && activeAssistant) {
      updatePermissionActions(activeAssistant, data.permissionRequest, {
        ...data,
        status: 'permission_required',
        threadId,
      });
      setTopStatus('等待权限');
    }
    if (data.activeThreadMatches) syncedThreadId = threadId;
  } catch (error) {
    if (options.force) console.warn('Codex Go gui status refresh skipped:', error);
  } finally {
    guiStateBusy = false;
  }
}
function setTopStatus(text = '已连接', type = '', options = {}) {
  if (!options.force && topNoticeUntil && Date.now() < topNoticeUntil) return;
  topStatusState = text || '已连接';
  topStatusType = type || '';
  renderContextIndicator();
}
function isNoticeTokenChar(char) {
  return /[A-Za-z0-9]/.test(char || '');
}
function stripNoticePeriods(text) {
  const raw = String(text || '').trim();
  let value = '';
  for (let index = 0; index < raw.length; index += 1) {
    const char = raw[index];
    if (char === '。') continue;
    if (char === '.') {
      const previous = raw[index - 1];
      const next = raw[index + 1];
      if (isNoticeTokenChar(previous) && isNoticeTokenChar(next)) value += char;
      continue;
    }
    value += char;
  }
  return value.trim();
}
function setNotice(text, type = '') {
  const value = stripNoticePeriods(text);
  topNoticeUntil = 0;
  if (!value) {
    notice.className = 'notice-pill';
    notice.textContent = '';
    return;
  }
  notice.className = `notice-pill is-visible ${type}`.trim();
  notice.textContent = value;
  window.clearTimeout(setNotice.timer);
  setNotice.timer = window.setTimeout(() => {
    notice.className = 'notice-pill';
  }, 6000);
}
function handleUnauthorizedResponse() {
  if (authExpiredNoticeShown) return;
  authExpiredNoticeShown = true;
  localStorage.removeItem('codexGo.token');
  setNotice('访问令牌已失效，请用启动器打印的新链接重新打开', 'error');
}
function readReasoningOverrides() {
  try {
    const parsed = JSON.parse(localStorage.getItem(REASONING_OVERRIDE_STORAGE_KEY) || '{}');
    return parsed && typeof parsed === 'object' ? parsed : {};
  } catch {
    return {};
  }
}
function writeReasoningOverride(threadId, mode) {
  if (!threadId || !mode) return;
  const rows = readReasoningOverrides();
  rows[threadId] = { ...mode, updatedAt: mode.updatedAt || new Date().toISOString(), local: true };
  try { localStorage.setItem(REASONING_OVERRIDE_STORAGE_KEY, JSON.stringify(rows)); } catch {}
}
function reasoningTime(mode) {
  const time = Date.parse(mode?.updatedAt || '');
  return Number.isFinite(time) ? time : 0;
}
function overrideReasoningForThread(threadId = selectedThreadId) {
  if (!threadId) return null;
  return readReasoningOverrides()[threadId] || null;
}
function bestReasoningMode(mode = null, threadId = selectedThreadId) {
  const override = overrideReasoningForThread(threadId);
  if (override && (!mode || reasoningTime(override) >= reasoningTime(mode))) return override;
  return mode || override || null;
}
function reasoningOptionByKey(targetKey = '') {
  return REASONING_MODE_OPTIONS.find(item => item.key === targetKey) || null;
}
function currentReasoningKey(mode = currentReasoningMode) {
  const key = String(mode?.key || '').trim();
  if (reasoningOptionByKey(key)) return key;
  const label = String(mode?.label || mode?.displayName || '').trim();
  return REASONING_MODE_OPTIONS.find(item => item.label === label)?.key || '';
}
function renderReasoningMenu() {
  const currentKey = currentReasoningKey();
  reasoningMenuCard.textContent = '';
  for (const item of REASONING_MODE_OPTIONS) {
    const button = document.createElement('button');
    button.type = 'button';
    button.className = `model-menu-item reasoning-menu-item mode-${item.key}${item.key === currentKey ? ' is-current' : ''}`;
    button.dataset.target = item.key;
    button.textContent = item.label;
    button.title = `推理模式：${item.displayName}`;
    button.setAttribute('aria-label', `推理模式：${item.displayName}${item.key === currentKey ? '（当前）' : ''}`);
    wireInstantActionButton(button, () => {
      if (switchingReasoningMode) return;
      if (item.key === currentKey) {
        closeReasoningMenu();
        setNotice(`当前已是${item.displayName}推理模式`, 'ok');
        return;
      }
      closeReasoningMenu();
      switchReasoningMode(item.key);
    });
    reasoningMenuCard.appendChild(button);
  }
}
function renderReasoningBadge(mode = currentReasoningMode) {
  currentReasoningMode = mode || null;
  const label = mode?.label || '中';
  const modeKey = currentReasoningKey(mode) || 'medium';
  reasoningText.textContent = label;
  reasoningBadge.className = `reasoning-badge mode-${modeKey}${switchingReasoningMode ? ' is-switching' : ''}`;
  const display = mode?.displayName || label || '中';
  reasoningBadge.title = `推理模式：${display}`;
  reasoningBadge.setAttribute('aria-label', `当前推理模式：${display}。点击打开低、中、高、超高选择菜单。`);
  reasoningBadge.disabled = switchingReasoningMode;
  if (reasoningMenuCard.classList.contains('is-open')) renderReasoningMenu();
}
function updateReasoningFromStatus(data) {
  const mode = bestReasoningMode(data?.reasoningMode || null, data?.threadId || selectedThreadId);
  renderReasoningBadge(mode);
}
function reasoningSwitchTarget(mode = currentReasoningMode) {
  const order = REASONING_MODE_OPTIONS.map(item => item.key);
  const currentIndex = order.indexOf(currentReasoningKey(mode));
  return order[(currentIndex + 1 + order.length) % order.length] || 'medium';
}
async function switchReasoningMode(targetKey = '') {
  if (switchingReasoningMode) return;
  if (!selectedThreadId) {
    setNotice('请先选择一个已有线程', 'error');
    return;
  }
  const requestedTarget = String(targetKey || '').trim() || reasoningSwitchTarget();
  switchingReasoningMode = true;
  renderReasoningBadge();
  setWorkingDot(true);
  setNotice('正在通过 Codex GUI 切换推理模式…', 'ok');
  try {
    await ensureRouteForSend();
    const response = await fetchApi('/codex/reasoning-mode', {
      method: 'POST',
      headers: { 'content-type': 'application/json', 'x-codex-go-token': token },
      body: JSON.stringify({ threadId: selectedThreadId, target: requestedTarget }),
      apiTimeoutMs: 20000,
      routeSwitchQuiet: true,
      retryProbeTimeoutMs: 900,
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok || !data.ok) throw new Error(data.message || '切换推理模式失败');
    if (data.targetReasoningMode) {
      writeReasoningOverride(selectedThreadId, data.targetReasoningMode);
      renderReasoningBadge(data.targetReasoningMode);
    }
    setNotice(data.message || '已切换推理模式', 'ok');
    refreshGuiState({ force: true });
    window.setTimeout(() => refreshCurrentThreadIfChanged(), 900);
  } catch (error) {
    setNotice(error.message || '切换推理模式失败', 'error');
  } finally {
    switchingReasoningMode = false;
    renderReasoningBadge();
    if (!activeAssistant && !pollTimer) setWorkingDot(false);
  }
}
function readModelOverrides() {
  try {
    const parsed = JSON.parse(localStorage.getItem(MODEL_OVERRIDE_STORAGE_KEY) || '{}');
    return parsed && typeof parsed === 'object' ? parsed : {};
  } catch {
    return {};
  }
}
function writeModelOverride(threadId, model) {
  if (!threadId || !model) return;
  const rows = readModelOverrides();
  rows[threadId] = { ...model, updatedAt: model.updatedAt || new Date().toISOString(), local: true };
  try { localStorage.setItem(MODEL_OVERRIDE_STORAGE_KEY, JSON.stringify(rows)); } catch {}
}
function modelTime(model) {
  const time = Date.parse(model?.updatedAt || '');
  return Number.isFinite(time) ? time : 0;
}
function overrideModelForThread(threadId = selectedThreadId) {
  if (!threadId) return null;
  return readModelOverrides()[threadId] || null;
}
function bestModelInfo(model = null, threadId = selectedThreadId) {
  const override = overrideModelForThread(threadId);
  if (override && (!model || modelTime(override) >= modelTime(model))) return override;
  return model || override || null;
}
function modelMenuOptionByKey(targetKey = '') {
  return modelMenuOptions.find(item => item.key === targetKey) || null;
}
function currentModelMenuKey(model = currentModelInfo) {
  const id = String(model?.id || '').trim();
  return modelMenuOptions.find(item => item.id === id)?.key || '';
}
function renderModelMenu() {
  const currentKey = currentModelMenuKey();
  modelMenuCard.textContent = '';
  for (const item of modelMenuOptions) {
    const button = document.createElement('button');
    button.type = 'button';
    button.className = `model-menu-item${item.key === currentKey ? ' is-current' : ''}`;
    button.dataset.target = item.key;
    button.textContent = item.label;
    button.title = item.displayName;
    button.setAttribute('aria-label', `${item.displayName}${item.key === currentKey ? '（当前）' : ''}`);
    wireInstantActionButton(button, () => {
      if (switchingModel) return;
      if (item.key === currentKey) {
        closeModelMenu();
        setNotice(`当前已是 ${item.displayName}`, 'ok');
        return;
      }
      closeModelMenu();
      switchCurrentModel(item.key);
    });
    modelMenuCard.appendChild(button);
  }
}
function renderModelBadge(model = currentModelInfo) {
  currentModelInfo = model || null;
  const label = model?.label || '--';
  const source = model?.source || 'unknown';
  modelText.textContent = label;
  modelBadge.className = `model-badge is-${source}${switchingModel ? ' is-switching' : ''}`;
  const sourceText = source === 'official' ? '官方' : source === 'local' ? '本机' : '未知';
  const display = model?.displayName || model?.id || '暂未读到当前模型';
  modelBadge.title = `${sourceText} · ${display}`;
  modelBadge.setAttribute('aria-label', `当前模型：${sourceText} ${label || display}。点击打开模型选择菜单。`);
  modelBadge.disabled = switchingModel;
  if (modelMenuCard.classList.contains('is-open')) renderModelMenu();
}
function updateModelFromStatus(data) {
  const model = bestModelInfo(data?.model || null, data?.threadId || selectedThreadId);
  renderModelBadge(model);
}
function modelSwitchTarget(model = currentModelInfo) {
  if (!modelMenuOptions.length) return '';
  const currentKey = currentModelMenuKey(model);
  const currentIndex = modelMenuOptions.findIndex(item => item.key === currentKey);
  const nextIndex = currentIndex >= 0 ? (currentIndex + 1) % modelMenuOptions.length : 0;
  return modelMenuOptions[nextIndex]?.key || '';
}
async function switchCurrentModel(targetKey = '') {
  if (switchingModel) return;
  if (!selectedThreadId) {
    setNotice('请先选择一个已有线程', 'error');
    return;
  }
  const requestedTarget = String(targetKey || '').trim() || modelSwitchTarget();
  if (!requestedTarget) {
    setNotice('未读取到可切换的本机模型', 'error');
    return;
  }
  switchingModel = true;
  renderModelBadge();
  setWorkingDot(true);
  setNotice('正在通过 Codex GUI 切换模型…', 'ok');
  try {
    await ensureRouteForSend();
    const response = await fetchApi('/codex/model-switch', {
      method: 'POST',
      headers: { 'content-type': 'application/json', 'x-codex-go-token': token },
      body: JSON.stringify({ threadId: selectedThreadId, target: requestedTarget }),
      apiTimeoutMs: 20000,
      routeSwitchQuiet: true,
      retryProbeTimeoutMs: 900,
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok || !data.ok) throw new Error(data.message || '切换模型失败');
    if (data.targetModel) {
      writeModelOverride(selectedThreadId, data.targetModel);
      renderModelBadge(data.targetModel);
    }
    setNotice(data.message || '已切换模型', 'ok');
    refreshGuiState({ force: true });
    window.setTimeout(() => refreshCurrentThreadIfChanged(), 900);
  } catch (error) {
    setNotice(error.message || '切换模型失败', 'error');
  } finally {
    switchingModel = false;
    renderModelBadge();
    if (!activeAssistant && !pollTimer) setWorkingDot(false);
  }
}
function defaultAppearanceSettings() {
  return { theme: 'dracula' };
}
function normalizeAppearanceSettings(value = {}) {
  const theme = THEME_OPTIONS.includes(String(value?.theme || '')) ? String(value.theme) : 'dracula';
  return { theme };
}
function readAppearanceSettings() {
  try {
    const parsed = JSON.parse(localStorage.getItem(APPEARANCE_SETTINGS_STORAGE_KEY) || 'null');
    return normalizeAppearanceSettings(parsed || defaultAppearanceSettings());
  } catch {
    return defaultAppearanceSettings();
  }
}
function persistAppearanceSettingsLocal(options = {}) {
  try { localStorage.setItem(APPEARANCE_SETTINGS_STORAGE_KEY, JSON.stringify(appearanceSettings)); } catch {}
  hasLocalAppearanceSettings = true;
  if (options.markAndroidDefaults && isAndroidKeyboardBrowser) {
    try { localStorage.setItem(ANDROID_APPEARANCE_DEFAULTS_STORAGE_KEY, '1'); } catch {}
  }
}
function ensureAndroidAppearanceDefaults() {
  return false;
}
function renderThemeSelect() {
  if (!themeSelect) return;
  themeSelect.value = normalizeAppearanceSettings(appearanceSettings).theme;
}
function isDarkTheme(theme = appearanceSettings.theme) {
  return theme === 'dark' || theme === 'luxe-dark' || theme === 'dracula' || theme === 'graphite';
}
function themeIconBase(theme = appearanceSettings.theme) {
  return isDarkTheme(theme) ? 'icons/dark' : 'icons';
}
function syncThemeIcons() {
  const base = themeIconBase();
  document.querySelectorAll('link[rel="icon"]').forEach(link => {
    const sizes = link.getAttribute('sizes');
    if (sizes === '32x32') link.href = `${base}/icon-32.png?v=${THEME_ICON_VERSION}`;
    if (sizes === '16x16') link.href = `${base}/icon-16.png?v=${THEME_ICON_VERSION}`;
  });
  document.querySelector('link[rel="apple-touch-icon"]')?.setAttribute(
    'href',
    `${base}/apple-touch-icon.png?v=${THEME_ICON_VERSION}`,
  );
}
function applyAppearanceSettings() {
  appearanceSettings = normalizeAppearanceSettings(appearanceSettings);
  for (const theme of THEME_OPTIONS) document.body.classList.remove(`theme-${theme}`);
  document.body.classList.add(`theme-${appearanceSettings.theme}`);
  document.body.classList.toggle('color-flow-on', appearanceSettings.theme === 'workbench' || appearanceSettings.theme === 'luxe-dark');
  document.documentElement.style.setProperty('color-scheme', isDarkTheme() ? 'dark' : 'light');
  const themeColorByName = {
    native: '#f4f3ef',
    workbench: '#edf2f1',
    minimal: '#f7f7f4',
    dark: '#141413',
    'luxe-dark': '#050506',
    dracula: '#282a36',
    graphite: '#0b0d0e',
  };
  const themeColor = themeColorByName[appearanceSettings.theme] || themeColorByName.dracula;
  document.querySelector('meta[name="theme-color"]')?.setAttribute('content', themeColor);
  syncThemeIcons();
  renderThemeSelect();
}
function themeDisplayName(theme) {
  if (theme === 'workbench') return '工作台';
  if (theme === 'minimal') return '极简';
  if (theme === 'dark') return '暗色';
  if (theme === 'luxe-dark') return '流光';
  if (theme === 'dracula') return 'Dracula';
  if (theme === 'graphite') return '墨岩';
  return '本机';
}
function setAppearanceTheme(theme) {
  if (!THEME_OPTIONS.includes(theme) || theme === appearanceSettings.theme) return;
  appearanceSettings = normalizeAppearanceSettings({ ...appearanceSettings, theme });
  persistAppearanceSettingsLocal();
  applyAppearanceSettings();
  setNotice(`已切换为${themeDisplayName(theme)}风格`, 'ok');
}
function readSuperModeEnabled() {
  try { return localStorage.getItem(SUPER_MODE_STORAGE_KEY) === '1'; } catch { return false; }
}
function persistSuperModeEnabled() {
  try { localStorage.setItem(SUPER_MODE_STORAGE_KEY, superModeEnabled ? '1' : '0'); } catch {}
}
function setSwitchState(button, on, disabled = false) {
  if (!button) return;
  button.classList.toggle('is-on', Boolean(on));
  button.disabled = Boolean(disabled);
  button.setAttribute('aria-checked', Boolean(on) ? 'true' : 'false');
}
function applySuperModeSettings() {
  setSwitchState(settingSuperModeSwitch, superModeEnabled);
}
function toggleSuperMode() {
  superModeEnabled = !superModeEnabled;
  persistSuperModeEnabled();
  applySuperModeSettings();
  setNotice(superModeEnabled ? '超级模式已开启（纯心理加成）' : '已关闭超级模式', 'ok');
}
function toggleSettingsCard() {
  closeReasoningMenu();
  closeModelMenu();
  closeThreadActionCard();
  closeContextQuickCard();
  threadMenu.classList.remove('is-open');
  const willOpen = !settingsCard.classList.contains('is-open');
  settingsCard.classList.toggle('is-open', willOpen);
  if (willOpen) {
    renderThemeSelect();
    applySuperModeSettings();
    positionSettingsCard();
  }
}
function closeSettingsCard() {
  settingsCard.classList.remove('is-open');
  settingsCard.style.left = '';
  settingsCard.style.top = '';
}
function positionSettingsCard(anchorElement = settingsButton) {
  if (!anchorElement || typeof anchorElement.getBoundingClientRect !== 'function') return;
  const anchor = anchorElement.getBoundingClientRect();
  const viewportWidth = window.innerWidth || document.documentElement.clientWidth || 0;
  const viewportHeight = window.innerHeight || document.documentElement.clientHeight || 0;
  const margin = 10;
  const cardWidth = settingsCard.offsetWidth || 344;
  const cardHeight = settingsCard.offsetHeight || 120;
  const rightAlignedLeft = anchor.right - cardWidth;
  const left = Math.max(margin, Math.min(viewportWidth - cardWidth - margin, rightAlignedLeft));
  const belowTop = anchor.bottom + 7;
  const aboveTop = anchor.top - cardHeight - 7;
  const top = belowTop + cardHeight + margin <= viewportHeight ? belowTop : Math.max(margin, aboveTop);
  settingsCard.style.left = `${Math.round(left)}px`;
  settingsCard.style.top = `${Math.round(top)}px`;
}
function setWorkingDot(active) {
  foregroundDotBusy = Boolean(active);
  updateTitleDotState();
}
const PIN_ICON = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 17v5"></path><path d="M9 10.76a2 2 0 0 1-1.11 1.79l-1.78.9A2 2 0 0 0 5 15.24V16h14v-.76a2 2 0 0 0-1.11-1.79l-1.78-.9A2 2 0 0 1 15 10.76V4h1a1 1 0 0 0 0-2H8a1 1 0 0 0 0 2h1z"></path></svg>';
const ARCHIVE_ICON = '<svg viewBox="0 0 24 24" aria-hidden="true"><rect width="20" height="5" x="2" y="3" rx="1"></rect><path d="M4 8v11a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8"></path><path d="M10 12h4"></path></svg>';
const RENAME_ICON = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 20h9"></path><path d="M16.5 3.5a2.12 2.12 0 0 1 3 3L7 19l-4 1 1-4Z"></path></svg>';
threadCurrentPin.innerHTML = PIN_ICON;
threadActionArchiveIcon.innerHTML = ARCHIVE_ICON;
threadActionRenameIcon.innerHTML = RENAME_ICON;
threadActionPinToggleIcon.innerHTML = PIN_ICON;
function alignTopActionsRight() {}
function routeLabel(candidate) {
  return candidate?.label || (candidate?.kind === 'local' ? '本地' : '外网');
}
function makeCandidate(id, baseUrl, label, kind, priority) {
  const normalized = normalizeBaseUrl(baseUrl);
  if (!normalized) return null;
  return { id, baseUrl: normalized, label, kind, priority };
}
function mergeApiCandidates(candidates) {
  const byBase = new Map();
  for (const candidate of candidates) {
    if (!candidate?.baseUrl) continue;
    const existing = byBase.get(candidate.baseUrl);
    if (!existing || candidate.priority < existing.priority) byBase.set(candidate.baseUrl, candidate);
  }
  apiCandidates = [...byBase.values()].sort((a, b) => a.priority - b.priority);
  try {
    localStorage.setItem(ROUTE_STORAGE_KEY, JSON.stringify(apiCandidates.filter(item => item.kind !== 'current')));
  } catch {}
  if (!apiCandidates.some(item => item.baseUrl === activeApiBase)) {
    const first = apiCandidates[0];
    if (first) {
      activeApiBase = first.baseUrl;
      activeApiLabel = routeLabel(first);
      activeApiKind = 'local';
    }
  }
}
function readStoredApiCandidates() {
  try { localStorage.removeItem(ROUTE_STORAGE_KEY); } catch {}
  return [];
}
async function fetchWithTimeout(url, options = {}, timeoutMs = 10000) {
  const controller = new AbortController();
  const timer = window.setTimeout(() => controller.abort(), timeoutMs);
  try {
    return await fetch(url, { ...options, signal: controller.signal });
  } finally {
    window.clearTimeout(timer);
  }
}
async function probeApiCandidate(candidate, timeoutMs = 2500) {
  if (!candidate?.baseUrl || !token) return false;
  const params = new URLSearchParams({ token, t: String(Date.now()) });
  try {
    const response = await fetchWithTimeout(`${candidate.baseUrl}/codex/health?${params}`, { cache: 'no-store' }, timeoutMs);
    const data = await response.json().catch(() => ({}));
    return response.ok && data.ok;
  } catch {
    return false;
  }
}
async function chooseApiCandidate(options = {}) {
  const { preferLocal = false, quiet = false, excludeBase = '', probeTimeoutMs = 2500 } = options;
  const ordered = [...apiCandidates].sort((a, b) => {
    const localBiasA = preferLocal && a.kind === 'local' ? -100 : 0;
    const localBiasB = preferLocal && b.kind === 'local' ? -100 : 0;
    return (a.priority + localBiasA) - (b.priority + localBiasB);
  });
  for (const candidate of ordered) {
    if (excludeBase && candidate.baseUrl === excludeBase) continue;
    if (await probeApiCandidate(candidate, probeTimeoutMs)) {
      const changed = activeApiBase !== candidate.baseUrl;
      activeApiBase = candidate.baseUrl;
      activeApiLabel = routeLabel(candidate);
      activeApiKind = 'local';
      if (changed && !quiet) setNotice('网络已自动切换到本地线路', 'ok');
      return candidate;
    }
  }
  return null;
}
async function loadApiConfig() {
  const baseCandidates = [
    makeCandidate('current', currentApiBase, '本地', 'local', 5),
    ...readStoredApiCandidates(),
  ].filter(Boolean);
  mergeApiCandidates(baseCandidates);

  const params = new URLSearchParams({ token });
  try {
    const response = await fetchWithTimeout(`${currentApiBase}/codex/config?${params}`, { cache: 'no-store' }, 5000);
    const data = await response.json();
    if (!response.ok || !data.ok) throw new Error(data.message || '读取线路配置失败');
    localOnlyMode = true;
    if (data.appearanceSettings) {
      if (hasLocalAppearanceSettings) {
        appearanceSettings = normalizeAppearanceSettings(appearanceSettings);
      } else {
        appearanceSettings = normalizeAppearanceSettings(data.appearanceSettings);
      }
      ensureAndroidAppearanceDefaults();
      applyAppearanceSettings();
    }
    if (Array.isArray(data.modelOptions) && data.modelOptions.length) {
      modelMenuOptions = data.modelOptions
        .filter(item => item && item.id)
        .map(item => ({
          key: String(item.key || item.id),
          id: String(item.id),
          label: String(item.label || item.displayName || item.id),
          displayName: String(item.displayName || item.label || item.id),
        }));
      renderModelBadge(currentModelInfo);
    }
    const configured = [
      ...baseCandidates,
      ...(data.localApiBases || []).map((base, index) => makeCandidate(`local-${index}`, base, '本地', 'local', 1 + index)),
    ].filter(Boolean);
    mergeApiCandidates(configured);
    apiCandidates = apiCandidates.filter(candidate => candidate.kind === 'local' || candidate.baseUrl === currentApiBase);
    if (activeApiKind !== 'local' && apiCandidates.length) {
      activeApiBase = apiCandidates[0].baseUrl;
      activeApiLabel = routeLabel(apiCandidates[0]);
      activeApiKind = 'local';
    }
    lastApiConfigRefreshAt = Date.now();
  } catch (error) {
    console.warn('Codex Go route config skipped:', error);
  }
}
async function refreshApiConfigIfNeeded(options = {}) {
  if (apiConfigRefreshBusy) return;
  const now = Date.now();
  if (!options.force && now - lastApiConfigRefreshAt < API_CONFIG_REFRESH_MIN_MS) return;
  apiConfigRefreshBusy = true;
  try {
    await loadApiConfig();
  } finally {
    apiConfigRefreshBusy = false;
  }
}
async function fetchApi(path, options = {}) {
  const timeoutMs = options.apiTimeoutMs || 12000;
  const routeSwitchQuiet = Boolean(options.routeSwitchQuiet);
  const retryProbeTimeoutMs = options.retryProbeTimeoutMs || 1200;
  const requestOptions = { ...options };
  delete requestOptions.apiTimeoutMs;
  delete requestOptions.routeSwitchQuiet;
  delete requestOptions.retryProbeTimeoutMs;
  const firstBase = activeApiBase;
  try {
    const response = await fetchWithTimeout(apiUrl(path), requestOptions, timeoutMs);
    if (response.status === 401) handleUnauthorizedResponse();
    if (![502, 503, 504].includes(response.status)) return response;
    const next = await chooseApiCandidate({ preferLocal: false, excludeBase: firstBase, quiet: routeSwitchQuiet, probeTimeoutMs: retryProbeTimeoutMs });
    const retryResponse = next ? await fetchWithTimeout(apiUrl(path), requestOptions, timeoutMs) : response;
    if (retryResponse.status === 401) handleUnauthorizedResponse();
    return retryResponse;
  } catch (error) {
    const next = await chooseApiCandidate({ preferLocal: false, excludeBase: firstBase, quiet: routeSwitchQuiet, probeTimeoutMs: retryProbeTimeoutMs });
    if (!next) throw error;
    const retryResponse = await fetchWithTimeout(apiUrl(path), requestOptions, timeoutMs);
    if (retryResponse.status === 401) handleUnauthorizedResponse();
    return retryResponse;
  }
}

async function ensureRouteForSend() {
  if (localOnlyMode) return;
  const active = apiCandidates.find(item => item.baseUrl === activeApiBase);
  if (!active || active.kind !== 'local') return;
  if (await probeApiCandidate(active, 700)) return;
  await chooseApiCandidate({ preferLocal: false, excludeBase: active.baseUrl, quiet: true, probeTimeoutMs: 900 });
}
function startRouteMonitor() {
  window.setInterval(async () => {
    if (localOnlyMode) return;
    if (document.hidden || routeMonitorBusy) return;
    routeMonitorBusy = true;
    const active = apiCandidates.find(item => item.baseUrl === activeApiBase);
    try {
      if (active?.kind === 'local') {
        if (await probeApiCandidate(active, 900)) return;
        await chooseApiCandidate({ preferLocal: false, excludeBase: active.baseUrl, quiet: true, probeTimeoutMs: 900 });
        return;
      }
      await chooseApiCandidate({ preferLocal: true, quiet: true, probeTimeoutMs: 1200 });
    } finally {
      routeMonitorBusy = false;
    }
  }, 5000);
}
function clearThreadBottomScrollTimers() {
  threadBottomScrollTimers.forEach(timer => window.clearTimeout(timer));
  threadBottomScrollTimers = [];
}

function scrollThreadToBottom(instant = true) {
  const apply = () => {
    thread.scrollTop = Math.max(0, thread.scrollHeight - thread.clientHeight);
  };
  if (instant) thread.classList.add('is-instant-scroll');
  apply();
  requestAnimationFrame(apply);
}

function scheduleThreadScrollToBottom(delays = [0, 32, 96, 220, 480, 800]) {
  clearThreadBottomScrollTimers();
  threadStickToBottomUntil = Date.now() + Math.max(...delays, 800) + 400;
  thread.classList.add('is-instant-scroll');
  for (const delay of delays) {
    if (delay === 0) {
      scrollThreadToBottom(true);
      continue;
    }
    threadBottomScrollTimers.push(window.setTimeout(() => scrollThreadToBottom(true), delay));
  }
  const releaseInstant = Math.max(...delays, 0) + 48;
  threadBottomScrollTimers.push(window.setTimeout(() => {
    thread.classList.remove('is-instant-scroll');
  }, releaseInstant));
}

function scrollBottom(options = {}) {
  if (options.instant) scrollThreadToBottom(true);
  else requestAnimationFrame(() => scrollThreadToBottom(false));
}

function beginHistoryRenderAtBottom() {
  thread.classList.add('is-history-rendering', 'is-instant-scroll');
}

function finishHistoryRenderAtBottom() {
  thread.classList.remove('is-history-rendering');
  scheduleThreadScrollToBottom();
}

function isDesktopKeyboardBypass() {
  return window.matchMedia('(pointer: fine)').matches && !window.matchMedia('(pointer: coarse)').matches;
}

function usesComposerKeyboardOverlay() {
  if (isDesktopKeyboardBypass()) return false;
  return window.matchMedia('(pointer: coarse)').matches
    || window.matchMedia('(hover: none)').matches
    || window.matchMedia('(max-width: 700px)').matches
    || isIOSMobileBrowser;
}

function syncMobileKeyboardModeClass() {
  document.body.classList.toggle('mobile-keyboard-mode', usesComposerKeyboardOverlay());
}

function stageOverlayRect() {
  const stage = document.querySelector('.stage');
  if (stage) return stage.getBoundingClientRect();
  const stackEl = composerStack || composerShell;
  return stackEl ? stackEl.getBoundingClientRect() : null;
}

function mobileKeyboardBottomInset() {
  const layoutHeight = Math.round(window.innerHeight || document.documentElement.clientHeight || 0);
  const viewport = window.visualViewport;
  if (!viewport) return Math.max(0, virtualKeyboardInset);
  const viewportTop = Math.max(0, Math.round(viewport.offsetTop || 0));
  const viewportHeight = Math.round(viewport.height || layoutHeight);
  const viewportShrink = Math.max(0, layoutHeight - viewportHeight);
  const viewportGap = Math.max(0, layoutHeight - viewportTop - viewportHeight);
  const baselineShrink = Math.max(0, layoutViewportBaselineHeight - viewportHeight);
  return Math.max(viewportShrink, viewportGap, baselineShrink, virtualKeyboardInset);
}

function composerOverlayBottom(keyboardBottom) {
  if (keyboardBottom > 8) return keyboardBottom;
  const stackEl = composerStack || composerShell;
  if (!stackEl) return 0;
  const rect = stackEl.getBoundingClientRect();
  return Math.max(0, Math.round(window.innerHeight - rect.bottom));
}

function isMobileKeyboardLikelyOpen(focused, keyboardBottom) {
  if (!focused) return false;
  if (keyboardBottom > 20) return true;
  const viewport = window.visualViewport;
  if (!viewport) return false;
  const layoutHeight = Math.round(window.innerHeight || document.documentElement.clientHeight || 0);
  const viewportHeight = Math.round(viewport.height || layoutHeight);
  return layoutHeight - viewportHeight > 20 || layoutViewportBaselineHeight - viewportHeight > 20;
}

function captureComposerStackRect() {
  const stackEl = composerStack || composerShell;
  if (!stackEl) return;
  const rect = stackEl.getBoundingClientRect();
  composerFlowRect = rect;
  const height = Math.ceil(rect.height || 0);
  if (height > 0) composerStackHeightLocked = height;
}

function measureComposerStackHeight() {
  if (document.body.classList.contains('keyboard-open') && composerStackHeightLocked > 0) {
    return composerStackHeightLocked;
  }
  const stack = composerStack || composerShell;
  if (!stack) return composerStackHeightLocked || 0;
  const height = Math.ceil(stack.getBoundingClientRect().height || 0);
  if (height > 0) composerStackHeightLocked = height;
  return height || composerStackHeightLocked || 0;
}

function setComposerStackMetrics(height, rect) {
  if (height) {
    document.documentElement.style.setProperty('--composer-stack-height', `${height}px`);
    document.documentElement.style.setProperty('--composer-shell-height', `${height}px`);
  }
  if (rect) {
    document.documentElement.style.setProperty('--composer-overlay-left', `${Math.max(0, Math.round(rect.left))}px`);
    document.documentElement.style.setProperty('--composer-overlay-right', `${Math.max(0, Math.round(window.innerWidth - rect.right))}px`);
  }
}

function resetDesktopViewportPlacement(layoutHeight) {
  document.body.classList.remove('keyboard-open');
  document.documentElement.style.setProperty('--app-top', '0px');
  document.documentElement.style.setProperty('--app-height', `${Math.max(1, layoutHeight)}px`);
  document.documentElement.style.setProperty('--keyboard-overlay-bottom', '0px');
  document.documentElement.style.setProperty('--composer-overlay-left', '0px');
  document.documentElement.style.setProperty('--composer-overlay-right', '0px');
  layoutViewportBaselineHeight = layoutHeight;
  setComposerStackMetrics(measureComposerStackHeight());
}

function updateComposerViewportPlacement() {
  const layoutHeight = Math.round(window.innerHeight || document.documentElement.clientHeight || 0);
  if (!usesComposerKeyboardOverlay()) {
    resetDesktopViewportPlacement(layoutHeight);
    return false;
  }
  syncMobileKeyboardModeClass();
  const focused = document.activeElement === textarea;
  const keyboardBottom = mobileKeyboardBottomInset();
  const keyboardOpen = isMobileKeyboardLikelyOpen(focused, keyboardBottom);
  document.body.classList.toggle('keyboard-open', keyboardOpen);
  document.documentElement.style.setProperty('--app-top', '0px');
  document.documentElement.style.setProperty('--app-height', `${Math.max(1, layoutHeight)}px`);
  const overlayBottom = keyboardOpen ? composerOverlayBottom(keyboardBottom) : 0;
  document.documentElement.style.setProperty('--keyboard-overlay-bottom', `${overlayBottom}px`);
  const stackHeight = measureComposerStackHeight();
  if (keyboardOpen) {
    setComposerStackMetrics(stackHeight, stageOverlayRect());
  } else {
    setComposerStackMetrics(stackHeight);
    document.documentElement.style.setProperty('--composer-overlay-left', '0px');
    document.documentElement.style.setProperty('--composer-overlay-right', '0px');
    captureComposerStackRect();
  }
  layoutViewportBaselineHeight = layoutHeight;
  return keyboardOpen;
}

function keepLayoutViewportPinned() {
  if (window.scrollX || window.scrollY) window.scrollTo(0, 0);
  const scroller = document.scrollingElement || document.documentElement;
  if (scroller && scroller.scrollTop) scroller.scrollTop = 0;
  if (document.body && document.body.scrollTop) document.body.scrollTop = 0;
}

function stableViewportHeight() {
  const viewportHeight = Math.round((window.visualViewport && window.visualViewport.height) || 0);
  return Math.round(viewportHeight || window.innerHeight || document.documentElement.clientHeight || 0);
}

function pinLayoutForKeyboardFocus() {
  if (!usesComposerKeyboardOverlay()) return;
  captureComposerStackRect();
  keyboardPinTimers.forEach(timer => window.clearTimeout(timer));
  keepLayoutViewportPinned();
  updateComposerViewportPlacement();
  keyboardPinTimers = [16, 32, 50, 80, 120, 180, 260, 360, 520].map(delay => window.setTimeout(keepLayoutViewportPinned, delay));
}

function shouldRearmFocusedTextarea(now) {
  if (composerImeActive || Date.now() - composerImeEndedAt < 600) return false;
  if (keyboardFocusStartedAt && now - keyboardFocusStartedAt < 1600) return false;
  if (lastTextareaFocusPrepareAt && now - lastTextareaFocusPrepareAt < 350) return false;
  return true;
}

function shouldUseNativeTextareaFocus(event, alreadyFocused) {
  return Boolean(event && event.target === textarea && !alreadyFocused);
}

function prepareTextareaFocus(event) {
  const now = performance.now();
  const keyboardLikelyOpen = document.body.classList.contains('keyboard-open');
  let alreadyFocused = document.activeElement === textarea;
  const nativeTextareaEdit = alreadyFocused && event && event.target === textarea && (keyboardLikelyOpen || textarea.value);
  if (!nativeTextareaEdit && alreadyFocused && !keyboardLikelyOpen && event && shouldRearmFocusedTextarea(now)) {
    suppressNextTextareaBlurRestore = true;
    try {
      textarea.blur();
    } catch {}
    alreadyFocused = document.activeElement === textarea;
  }
  lastTextareaFocusPrepareAt = now;
  if (nativeTextareaEdit) {
    return;
  }
  const nativeTextareaFocus = shouldUseNativeTextareaFocus(event, alreadyFocused);
  if (nativeTextareaFocus) {
    keyboardFocusStartedAt = now;
    return;
  }
  if (!keyboardFocusStartedAt || !alreadyFocused) keyboardFocusStartedAt = now;
  pinLayoutForKeyboardFocus();
  if (event && event.cancelable) event.preventDefault();
  if (event && typeof event.stopPropagation === 'function') event.stopPropagation();
  if (!alreadyFocused) {
    try {
      textarea.focus({ preventScroll: true });
    } catch {
      textarea.focus();
    }
    beginKeyboardAlignment();
  } else {
    scheduleKeyboardAlignment();
  }
}

function shouldPrepareComposerFocus(target) {
  if (!target || !composer.contains(target)) return false;
  if (target === textarea) return true;
  if (target.closest('button, input, .attachment-tray, .queued-send-bar')) return target === textarea;
  return true;
}

function prepareComposerFocus(event) {
  if (!shouldPrepareComposerFocus(event.target)) return;
  prepareTextareaFocus(event);
}

function noteOutsideComposerTouch(event) {
  if (!event || !event.target) return;
  if ((composerStack && composerStack.contains(event.target)) || (composerShell && composerShell.contains(event.target))) return;
  lastOutsideComposerTouchAt = performance.now();
}

function applyViewportSize() {
  const keyboardOpen = updateComposerViewportPlacement();
  if (!usesComposerKeyboardOverlay() || isAndroidKeyboardBrowser) keepLayoutViewportPinned();
  return keyboardOpen;
}

function alignComposerForKeyboard() {
  if (!usesComposerKeyboardOverlay()) {
    keyboardOverlayOpen = false;
    applyViewportSize();
    return;
  }
  const keyboardOpen = applyViewportSize();
  const openedNow = keyboardOpen && !keyboardOverlayOpen;
  keyboardOverlayOpen = keyboardOpen;
  if (keyboardAlignRaf) window.cancelAnimationFrame(keyboardAlignRaf);
  keyboardAlignRaf = requestAnimationFrame(() => {
    keyboardAlignRaf = 0;
    if (isAndroidKeyboardBrowser) keepLayoutViewportPinned();
    if (openedNow) thread.scrollTop = thread.scrollHeight;
    if (keyboardOpen && document.activeElement === textarea) {
      keyboardComposerRevealDone = true;
    }
  });
}

function scheduleKeyboardAlignment() {
  if (!usesComposerKeyboardOverlay()) return;
  keyboardAlignmentTimers.forEach(timer => window.clearTimeout(timer));
  alignComposerForKeyboard();
  keyboardAlignmentTimers = [48, 140, 280].map(delay => window.setTimeout(alignComposerForKeyboard, delay));
}

function beginKeyboardAlignment() {
  if (!usesComposerKeyboardOverlay()) {
    applyViewportSize();
    return;
  }
  captureComposerStackRect();
  keyboardComposerRevealDone = false;
  keyboardFocusStartedAt = performance.now();
  pinLayoutForKeyboardFocus();
  scheduleKeyboardAlignment();
}

function startKeyboardMonitor() {
  // Intentionally empty: let iOS/Safari own keyboard layout.
}

function stopKeyboardMonitor() {
  if (!keyboardMonitorTimer) return;
  window.clearInterval(keyboardMonitorTimer);
  keyboardMonitorTimer = null;
}

function restoreLayoutAfterKeyboard() {
  if (!usesComposerKeyboardOverlay()) {
    resetDesktopViewportPlacement(Math.round(window.innerHeight || document.documentElement.clientHeight || 0));
    return;
  }
  if (suppressNextTextareaBlurRestore) {
    suppressNextTextareaBlurRestore = false;
    stopKeyboardMonitor();
    keyboardAlignmentTimers.forEach(timer => window.clearTimeout(timer));
    keyboardAlignmentTimers = [];
    document.body.classList.remove('keyboard-open');
    keyboardComposerRevealDone = false;
    keyboardFocusStartedAt = 0;
    updateComposerViewportPlacement();
    keepLayoutViewportPinned();
    return;
  }
  const now = performance.now();
  const recentInputFocus = now - lastTextareaFocusPrepareAt < 650;
  const recentOutsideDismiss = lastOutsideComposerTouchAt > lastTextareaFocusPrepareAt && now - lastOutsideComposerTouchAt < 700;
  if (recentInputFocus && !recentOutsideDismiss) {
    window.setTimeout(() => {
      if (document.activeElement === textarea) return;
      try {
        textarea.focus({ preventScroll: true });
      } catch {
        textarea.focus();
      }
      beginKeyboardAlignment();
    }, 40);
    return;
  }
  stopKeyboardMonitor();
  keyboardAlignmentTimers.forEach(timer => window.clearTimeout(timer));
  keyboardAlignmentTimers = [];
  keyboardPinTimers.forEach(timer => window.clearTimeout(timer));
  keyboardPinTimers = [];
  if (keyboardAlignRaf) {
    window.cancelAnimationFrame(keyboardAlignRaf);
    keyboardAlignRaf = 0;
  }
  keyboardOverlayOpen = false;
  document.body.classList.remove('keyboard-open');
  keyboardComposerRevealDone = false;
  keyboardFocusStartedAt = 0;
  document.documentElement.style.setProperty('--app-top', '0px');
  document.documentElement.style.setProperty('--app-height', `${Math.max(1, window.innerHeight || document.documentElement.clientHeight || stableViewportHeight())}px`);
  if (isAndroidKeyboardBrowser) keepLayoutViewportPinned();
  requestAnimationFrame(() => {
    updateComposerViewportPlacement();
  });
}

function readOpenProjectKeys() {
  try {
    const keys = JSON.parse(localStorage.getItem(GROUPS_STORAGE_KEY) || '[]');
    return new Set(Array.isArray(keys) ? keys.filter(Boolean) : []);
  } catch {
    return new Set();
  }
}

function persistOpenProjectKeys() {
  localStorage.setItem(GROUPS_STORAGE_KEY, JSON.stringify([...openProjectKeys]));
}

function readCompletedThreadIds() {
  try {
    const raw = JSON.parse(localStorage.getItem(THREAD_NOTICE_STORAGE_KEY) || '[]');
    const rows = Array.isArray(raw)
      ? raw.map(id => ({ id, at: 0 }))
      : Array.isArray(raw?.rows)
        ? raw.rows
        : Array.isArray(raw?.ids)
          ? raw.ids.map(id => ({ id, at: raw.at || 0 }))
          : [];
    const ids = new Set();
    completedThreadNoticeTimes = new Map();
    for (const row of rows) {
      const id = typeof row === 'string' ? row : row?.id;
      if (!id) continue;
      const rawAt = typeof row === 'string' ? 0 : row.at;
      const at = typeof rawAt === 'number' ? rawAt : Date.parse(rawAt || '') || 0;
      ids.add(id);
      completedThreadNoticeTimes.set(id, at);
    }
    return ids;
  } catch {
    completedThreadNoticeTimes = new Map();
    return new Set();
  }
}

function persistCompletedThreadIds() {
  const rows = [...completedThreadIds].map(id => ({
    id,
    at: completedThreadNoticeTimes.get(id) || Date.now(),
  }));
  localStorage.setItem(THREAD_NOTICE_STORAGE_KEY, JSON.stringify({ version: 2, rows }));
}

function isCompletedThreadNoticeExpired(id, now = Date.now()) {
  const at = Number(completedThreadNoticeTimes.get(id)) || 0;
  return !at || now - at > THREAD_NOTICE_MAX_AGE_MS;
}

function hasUnreadCompletedThread() {
  const knownThreadIds = new Set(knownThreads.map(item => item.id).filter(Boolean));
  const now = Date.now();
  for (const id of completedThreadIds) {
    if (!id || id === selectedThreadId) continue;
    if (isCompletedThreadNoticeExpired(id, now)) continue;
    if (knownThreadIds.size && !knownThreadIds.has(id)) continue;
    return true;
  }
  return false;
}

function pruneCompletedThreadNotices() {
  const knownThreadIds = new Set(knownThreads.map(item => item.id).filter(Boolean));
  const now = Date.now();
  let changed = false;
  for (const id of [...completedThreadIds]) {
    const runtime = threadRuntimeStates.get(id);
    if (id === selectedThreadId || isCompletedThreadNoticeExpired(id, now) || (knownThreadIds.size && !knownThreadIds.has(id)) || isThreadRunningStatus(runtime?.status)) {
      completedThreadIds.delete(id);
      completedThreadNoticeTimes.delete(id);
      changed = true;
    }
  }
  if (changed) persistCompletedThreadIds();
  updateTitleDotState();
}

function hasOtherRunningThread() {
  for (const [id, runtime] of threadRuntimeStates) {
    if (id && id !== selectedThreadId && isThreadRunningStatus(runtime?.status)) return true;
  }
  for (const item of knownThreads) {
    if (!item?.id || item.id === selectedThreadId) continue;
    const runtime = threadRuntimeStates.get(item.id) || runtimeSnapshotFromThread(item) || {};
    if (isThreadRunningStatus(runtime.status)) return true;
  }
  return false;
}

function isSelectedThreadRunning() {
  const runtime = selectedThreadId ? threadRuntimeStates.get(selectedThreadId) : null;
  return Boolean(activeAssistant || pollTimer || isThreadRunningStatus(runtime?.status));
}

function updateTitleDotState() {
  const currentWorking = Boolean(foregroundDotBusy || isSelectedThreadRunning());
  const otherRunning = hasOtherRunningThread();
  const anyWorking = currentWorking || otherRunning;
  const unreadComplete = hasUnreadCompletedThread();
  document.body.classList.remove('dot-working', 'dot-background-working', 'dot-attention');
  document.body.classList.toggle('dot-flashing', anyWorking);
  document.body.classList.toggle('dot-blue', unreadComplete);
  document.body.classList.toggle('dot-orange', !unreadComplete && otherRunning);
}

function isThreadRunningStatus(status) {
  return status === 'running' || status === 'waiting' || status === 'permission_required';
}

function isThreadPermissionStatus(status) {
  return status === 'permission_required';
}

function isThreadCompleteStatus(status) {
  return status === 'complete' || status === 'error';
}

function clearLocalStopSuppression(threadId) {
  if (!threadId) return;
  locallyStoppedThreads.delete(threadId);
}

function markThreadLocallyStopped(threadId) {
  if (!threadId) return;
  const now = Date.now();
  locallyStoppedThreads.set(threadId, {
    at: now,
    until: now + LOCAL_STOP_SUPPRESS_MS,
  });
}

function isLocalStopSuppressed(threadId, startedAt = '') {
  if (!threadId) return false;
  const entry = locallyStoppedThreads.get(threadId);
  if (!entry) return false;
  if (Date.now() > entry.until) {
    locallyStoppedThreads.delete(threadId);
    return false;
  }
  const startedMs = Date.parse(startedAt || '');
  if (Number.isFinite(startedMs) && startedMs > entry.at + 1000) {
    locallyStoppedThreads.delete(threadId);
    return false;
  }
  return true;
}

function suppressRunningSnapshotAfterLocalStop(threadId, snapshot) {
  if (!snapshot || !isThreadRunningStatus(snapshot.status) || !isLocalStopSuppressed(threadId, snapshot.startedAt)) return snapshot;
  return {
    ...snapshot,
    status: 'idle',
    active: false,
    updatedAt: new Date().toISOString(),
  };
}

function setThreadCompleteNotice(threadId, active, completedAtMs = Date.now()) {
  if (!threadId) return;
  const before = completedThreadIds.has(threadId);
  const beforeAt = completedThreadNoticeTimes.get(threadId) || 0;
  if (active && threadId !== selectedThreadId) {
    completedThreadIds.add(threadId);
    completedThreadNoticeTimes.set(threadId, completedAtMs || Date.now());
  } else {
    completedThreadIds.delete(threadId);
    completedThreadNoticeTimes.delete(threadId);
  }
  if (before !== completedThreadIds.has(threadId) || beforeAt !== (completedThreadNoticeTimes.get(threadId) || 0)) persistCompletedThreadIds();
  updateTitleDotState();
}

function runtimeSnapshotFromThread(item) {
  if (!item) return null;
  const status = item.runtimeStatus || '';
  if (!status) return null;
  return {
    status,
    active: Boolean(item.runtimeActive || isThreadRunningStatus(status)),
    startedAt: item.runtimeStartedAt || '',
    completedAt: item.runtimeCompletedAt || '',
    updatedAt: item.runtimeUpdatedAt || item.effectiveUpdatedAt || item.updatedAt || '',
    turnId: item.runtimeTurnId || '',
  };
}

function applyThreadRuntimeState(threadId, snapshot, options = {}) {
  if (!threadId || !snapshot) return;
  snapshot = suppressRunningSnapshotAfterLocalStop(threadId, snapshot);
  const previous = threadRuntimeStates.get(threadId);
  threadRuntimeStates.set(threadId, snapshot);
  if (threadId === selectedThreadId) {
    setThreadCompleteNotice(threadId, false);
    return;
  }
  if (isThreadRunningStatus(snapshot.status)) {
    setThreadCompleteNotice(threadId, false);
    return;
  }
  if (!options.detectTransitions || !isThreadCompleteStatus(snapshot.status) || !previous) return;
  const wasRunning = isThreadRunningStatus(previous.status);
  const changedToComplete = previous.status !== snapshot.status && isThreadCompleteStatus(snapshot.status);
  const previousTime = Date.parse(previous.completedAt || previous.updatedAt || '') || 0;
  const currentTime = Date.parse(snapshot.completedAt || snapshot.updatedAt || '') || 0;
  const isRecentCompletion = Boolean(currentTime && Date.now() - currentTime <= THREAD_NOTICE_MAX_AGE_MS);
  if (isRecentCompletion && (wasRunning || changedToComplete || (currentTime && previousTime && currentTime > previousTime))) {
    setThreadCompleteNotice(threadId, true, currentTime);
  }
}

function formatDuration(ms = 0) {
  const total = Math.max(0, Math.floor(Math.max(0, Number(ms) || 0) / 1000));
  const minutes = Math.floor(total / 60);
  const seconds = total % 60;
  return minutes ? `${minutes}m ${seconds}s` : `${seconds}s`;
}

function setMetaLabel(meta, label = '') {
  if (!meta) return;
  const text = String(label || '');
  const match = text.match(/^(.*?)(\d+m\s+\d+s|\d+s)$/);
  meta.textContent = '';
  if (!match) {
    meta.textContent = text;
    return;
  }
  meta.append(document.createTextNode(match[1] || ''));
  const duration = match[2] || '';
  let cursor = 0;
  for (const digitMatch of duration.matchAll(/\d+/g)) {
    const index = digitMatch.index || 0;
    if (index > cursor) meta.append(document.createTextNode(duration.slice(cursor, index)));
    const number = document.createElement('span');
    number.className = 'meta-duration-number';
    number.textContent = digitMatch[0];
    meta.append(number);
    cursor = index + digitMatch[0].length;
  }
  if (cursor < duration.length) meta.append(document.createTextNode(duration.slice(cursor)));
}

function parseTimeMs(value) {
  const parsed = Date.parse(value || '');
  return Number.isFinite(parsed) ? parsed : 0;
}

function setActiveRunStart(startedAt = '', fallbackMs = Date.now()) {
  if (!activeAssistant || activeAssistant.runStartedAtMs) return;
  const parsed = parseTimeMs(startedAt);
  const startMs = parsed || fallbackMs;
  activeAssistant.runStartedAtMs = startMs;
  activeAssistant.runStartedAt = new Date(startMs).toISOString();
}

function activeRunDurationMs(endAt = '') {
  if (!activeAssistant) return 0;
  const startMs = Number(activeAssistant.runStartedAtMs) || parseTimeMs(activeAssistant.runStartedAt);
  if (!startMs) return 0;
  const endMs = parseTimeMs(endAt) || Date.now();
  return Math.max(0, endMs - startMs);
}

function finalRunDurationMs(data = {}) {
  const serverDuration = Number(data.durationMs);
  if (Number.isFinite(serverDuration) && serverDuration >= 0) return serverDuration;
  const timestampDuration = activeRunDurationMs(data.completedAt || data.updatedAt || '');
  if (timestampDuration) return timestampDuration;
  return activeRunDurationMs();
}

function updateActiveRunDuration(force = false) {
  if (!activeAssistant) return;
  const durationText = formatDuration(activeRunDurationMs());
  if (!force && durationText === activeAssistant.runDurationText) return;
  activeAssistant.runDurationText = durationText;
  const activeCommandUi = commandUi(activeAssistant.commandKind || '');
  setMetaLabel(activeAssistant.meta, activeCommandUi ? activeCommandUi.runningLabel(durationText) : `Codex · 运行 ${durationText}`);
  setTopStatus(activeCommandUi ? activeCommandUi.runningNotice(durationText) : `Codex 正在回复 · ${durationText}`);
}

function startRunDurationTimer() {
  if (runDurationTimer) return;
  runDurationTimer = window.setInterval(() => updateActiveRunDuration(false), 1000);
}

function stopRunDurationTimer() {
  if (runDurationTimer) window.clearInterval(runDurationTimer);
  runDurationTimer = null;
}

function commandKindForText(text) {
  return String(text || '').trim() === CONTEXT_COMPACT_COMMAND ? 'compact' : '';
}

function commandUi(commandKind) {
  if (commandKind === 'compact') {
    return {
      userLabel: '你 · 压缩',
      pendingText: '正在压缩中…',
      runningLabel: durationText => `Codex · 压缩 ${durationText}`,
      completeLabel: durationText => `Codex · 已压缩 ${durationText}`,
      runningNotice: durationText => `正在压缩 · ${durationText}`,
      completeText: '已压缩。',
    };
  }
  return null;
}

function latestUserCommandKind() {
  const users = [...thread.querySelectorAll('.message.user .bubble')];
  const latest = users[users.length - 1];
  return commandKindForText(latest?.textContent || '');
}

function stepMarkdown(steps = []) {
  if (!steps.length) return '已发送，等待 Codex 开始回复…';
  return steps.map(step => {
    if (step.kind === 'tool') return `- **工具**：${step.text || ''}`;
    if (step.kind === 'permission') return `- **权限**：${step.text || '等待你在电脑端确认权限请求'}`;
    if (step.kind === 'commentary') return `- **进度**：${step.text || ''}`;
    if (step.kind === 'thinking') return step.text || '正在分析请求';
    if (step.kind === 'start') return `- **开始**：${step.text || '开始处理'}`;
    if (step.kind === 'complete') return `- **完成**：${step.text || '回复完成'}`;
    if (step.kind === 'error') return `- **失败**：${step.text || 'Codex 回复失败'}`;
    return `- **${step.label || '事件'}**：${step.text || ''}`;
  }).join('\n\n');
}

function renderProcessSteps(el, steps = []) {
  if (!steps.length) return setMarkdown(el, '已发送，等待 Codex 开始回复…');
  const previousRects = new Map();
  el.querySelectorAll('.process-tool[data-tool-key]').forEach(node => {
    previousRects.set(node.dataset.toolKey, node.getBoundingClientRect());
  });

  el.innerHTML = '';
  const feed = document.createElement('div');
  feed.className = 'process-feed';
  let currentToolRow = null;
  let toolGroupIndex = -1;
  let toolIndexInGroup = 0;
  const animatedTools = [];

  const animateToolLayout = item => {
    const previous = previousRects.get(item.dataset.toolKey);
    const next = item.getBoundingClientRect();
    if (previous) {
      const dx = previous.left - next.left;
      if (Math.abs(dx) > 1) {
        item.style.transition = 'none';
        item.style.transform = `translateX(${dx}px)`;
        animatedTools.push(item);
      }
    } else {
      item.style.transition = 'none';
      item.style.opacity = '0';
      item.style.transform = 'translateX(-10px) scale(.98)';
      animatedTools.push(item);
    }
  };

  const appendToolGroup = group => {
    if (!group.length) return;
    currentToolRow = document.createElement('div');
    currentToolRow.className = 'process-tool-row';
    currentToolRow.setAttribute('aria-label', '工具调用过程，可左右滑动查看');
    feed.appendChild(currentToolRow);
    for (let i = group.length - 1; i >= 0; i -= 1) {
      const step = group[i];
      const item = document.createElement('div');
      item.className = 'process-tool';
      item.textContent = step.text || '调用工具';
      item.dataset.toolKey = step.callId || `${toolGroupIndex}:${i}:${step.text || ''}`;
      currentToolRow.appendChild(item);
    }
  };

  let pendingToolGroup = [];
  const flushToolGroup = () => {
    if (!pendingToolGroup.length) return;
    toolGroupIndex += 1;
    toolIndexInGroup = 0;
    appendToolGroup(pendingToolGroup.map(step => ({ ...step, __toolIndex: toolIndexInGroup++ })));
    pendingToolGroup = [];
  };

  for (const step of steps) {
    if (step.kind === 'tool') {
      pendingToolGroup.push(step);
      continue;
    }

    flushToolGroup();
    currentToolRow = null;
    const item = document.createElement('div');
    if (step.kind === 'thinking') {
      item.className = 'process-thinking markdown-body';
      const body = document.createElement('div');
      body.innerHTML = markdownToHtml(step.text || '正在分析请求');
      item.append(body);
    } else if (step.kind === 'commentary') {
      item.className = 'process-commentary markdown-body';
      const body = document.createElement('div');
      body.innerHTML = markdownToHtml(step.text || '');
      item.append(body);
    } else if (step.kind === 'permission') {
      item.className = `process-permission${step.pending === false ? ' is-resolved' : ''}`;
      item.textContent = `${step.label || (step.pending === false ? '已授权' : '等待权限')}：${step.text || '等待你在电脑端确认权限请求'}`;
    } else {
      item.className = step.kind === 'complete' ? 'process-complete' : step.kind === 'error' ? 'process-error' : 'process-start';
      item.textContent = `${step.label || '事件'}：${step.text || ''}`;
    }
    feed.appendChild(item);
  }
  flushToolGroup();
  el.appendChild(feed);

  feed.querySelectorAll('.process-tool[data-tool-key]').forEach(animateToolLayout);
  if (animatedTools.length) {
    requestAnimationFrame(() => {
      for (const item of animatedTools) {
        item.style.transition = 'transform 220ms cubic-bezier(.2,.8,.2,1), opacity 160ms ease-out';
        item.style.transform = '';
        item.style.opacity = '';
      }
      window.setTimeout(() => {
        for (const item of animatedTools) item.style.transition = '';
      }, 260);
    });
  }
}

function fileToDataUrl(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result);
    reader.onerror = () => reject(reader.error || new Error('读取附件失败'));
    reader.readAsDataURL(file);
  });
}

function isImageAttachment(item = {}) {
  return String(item.type || '').toLowerCase().startsWith('image/');
}

function attachmentKind(item = {}) {
  const explicit = String(item.kind || '').toLowerCase();
  if (['image', 'video', 'audio', 'pdf', 'archive', 'text', 'file'].includes(explicit)) return explicit;
  const type = String(item.type || '').toLowerCase();
  const name = String(item.name || '').toLowerCase();
  if (type.startsWith('image/')) return 'image';
  if (type.startsWith('video/')) return 'video';
  if (type.startsWith('audio/')) return 'audio';
  if (type.includes('pdf') || name.endsWith('.pdf')) return 'pdf';
  if (type.includes('zip') || /\.(zip|rar|7z|tar|gz)$/i.test(name)) return 'archive';
  if (type.startsWith('text/') || /\.(txt|md|json|csv|log|py|js|ts|tsx|jsx|css|html|xml|yaml|yml|toml|sh|rs|go)$/i.test(name)) return 'text';
  return 'file';
}

function attachmentKindLabel(kind) {
  return {
    image: '图片',
    video: '视频',
    audio: '音频',
    pdf: 'PDF',
    archive: '压缩包',
    text: '文本',
    file: '文件',
  }[kind] || '文件';
}

function attachmentSummary(attachments = []) {
  if (!attachments.length) return '';
  const counts = {};
  for (const item of attachments) {
    const label = attachmentKindLabel(attachmentKind(item));
    counts[label] = (counts[label] || 0) + 1;
  }
  return Object.entries(counts).map(([label, count]) => `${count} ${label === '图片' ? '张' : '个'}${label}`).join('、');
}

function fileBadgeText(item = {}) {
  const name = String(item.name || '附件');
  const ext = name.includes('.') ? name.split('.').pop().slice(0, 5) : '';
  return ext ? ext.toUpperCase() : attachmentKindLabel(attachmentKind(item));
}

function renderAttachmentTray() {
  attachmentTray.innerHTML = '';
  attachmentTray.classList.toggle('has-items', pendingAttachments.length > 0);
  pendingAttachments.forEach((item, index) => {
    const chip = document.createElement('div');
    const remove = document.createElement('button');
    chip.className = `attachment-chip ${isImageAttachment(item) ? 'is-image' : 'is-file'}`;
    chip.title = item.name || '附件';
    if (isImageAttachment(item)) {
      const img = document.createElement('img');
      img.src = item.dataUrl;
      img.alt = item.name || '图片';
      chip.appendChild(img);
    } else {
      const badge = document.createElement('span');
      const name = document.createElement('span');
      badge.className = 'attachment-file-badge';
      badge.textContent = fileBadgeText(item);
      name.className = 'attachment-file-name';
      name.textContent = item.name || '附件';
      chip.append(badge, name);
    }
    remove.type = 'button';
    remove.textContent = '×';
    remove.addEventListener('click', () => {
      pendingAttachments.splice(index, 1);
      renderAttachmentTray();
      scheduleComposerDraftSave();
      if (!window.matchMedia('(max-width: 700px), (pointer: coarse)').matches) {
        textarea.focus({ preventScroll: true });
      }
    });
    chip.appendChild(remove);
    attachmentTray.appendChild(chip);
  });
  updateComposerViewportPlacement();
}

function queuedSendSummary(text, attachments = []) {
  const body = String(text || '').replace(/\s+/g, ' ').trim();
  const attachmentText = attachmentSummary(attachments);
  if (body && attachmentText) return `${body} · ${attachmentText}`;
  return body || attachmentText || '空消息';
}

function queuedSendActionKey(action, text) {
  return `${action}:${String(text || '').slice(0, 180)}`;
}

function moveQueuedSendToComposer(text) {
  const value = String(text || '');
  if (!value.trim()) return;
  textarea.value = value;
  textarea.dispatchEvent(new Event('input', { bubbles: true }));
  autosize();
  updateComposerAction();
  saveComposerDraftForKey();
  textarea.focus({ preventScroll: true });
  try {
    textarea.setSelectionRange(textarea.value.length, textarea.value.length);
  } catch {
    // Some mobile browsers can reject selection changes while focus is settling.
  }
}

function queuedSendGuidedKey(threadId, text) {
  return `${threadId || ''}:${String(text || '').slice(0, 180)}`;
}

function markQueuedSendGuided(text) {
  if (!selectedThreadId || !text) return;
  guidedQueuedSendKeys.add(queuedSendGuidedKey(selectedThreadId, text));
}

function isQueuedSendGuided(text) {
  return guidedQueuedSendKeys.has(queuedSendGuidedKey(selectedThreadId, text));
}

function pruneGuidedQueuedSendKeys(items = []) {
  if (!selectedThreadId) return;
  const prefix = `${selectedThreadId}:`;
  const live = new Set((Array.isArray(items) ? items : []).map(item => queuedSendGuidedKey(selectedThreadId, item.text || item.summary || '')));
  for (const key of guidedQueuedSendKeys) {
    if (!key.startsWith(prefix)) continue;
    if (!live.has(key)) guidedQueuedSendKeys.delete(key);
  }
}

function appendGuidedSendNoteToThread(text) {
  const summary = String(text || '').replace(/\s+/g, ' ').trim();
  if (!summary) return;
  const article = document.createElement('article');
  article.className = 'message guided-send-note';
  const wrap = document.createElement('div');
  wrap.className = 'bubble-wrap';
  const bubble = document.createElement('div');
  bubble.className = 'bubble';
  bubble.textContent = `已引导 ${summary}`;
  wrap.append(bubble);
  article.append(wrap);
  thread.appendChild(article);
  scheduleThreadScrollToBottom([0, 32, 96]);
}

function rememberQueuedSends(threadId, items = []) {
  if (!threadId) return;
  queuedSendsCache.set(threadId, Array.isArray(items) ? items : []);
  while (queuedSendsCache.size > QUEUED_SENDS_CACHE_MAX) {
    const oldest = queuedSendsCache.keys().next().value;
    if (oldest === undefined) break;
    queuedSendsCache.delete(oldest);
  }
}

function readQueuedSendsCache(threadId) {
  if (!threadId || !queuedSendsCache.has(threadId)) return null;
  return queuedSendsCache.get(threadId) || [];
}

function queuedSendsRawSignature(items = []) {
  return (Array.isArray(items) ? items : [])
    .map((item, index) => `${Number.isFinite(Number(item.order)) ? Number(item.order) : index}:${String(item.text || item.summary || '').replace(/\s+/g, ' ').trim()}`)
    .join('|');
}

function queuedSendsCurrentSignature() {
  return queuedSends.map(item => `${item.order}:${item.text}`).join('|');
}

function prepareQueuedSendsForThread(threadId) {
  if (queuedSendsCache.has(threadId)) {
    queuedSendLoading = false;
    const cached = readQueuedSendsCache(threadId) || [];
    if (cached.length) setQueuedSendsFromCodex(cached, { skipCache: true });
    else {
      queuedSends = [];
      renderQueuedSends();
    }
    return;
  }
  queuedSendLoading = true;
  queuedSends = [];
  renderQueuedSends();
}

function maybeScrollThreadForComposerGrowth(previousVisible, previousHeight) {
  const visible = queuedSend.classList.contains('is-visible');
  const height = visible ? queuedSend.offsetHeight : 0;
  if (!visible && !previousVisible) return;
  if (height <= previousHeight + 2) return;
  const maxScroll = Math.max(0, thread.scrollHeight - thread.clientHeight);
  if (thread.scrollTop >= maxScroll - 96) scheduleThreadScrollToBottom([0, 32, 96]);
}

function renderQueuedSends() {
  const previousVisible = queuedSend.classList.contains('is-visible');
  const previousHeight = previousVisible ? queuedSend.offsetHeight : 0;
  const count = queuedSends.length;
  const showLoading = queuedSendLoading && !count;
  const visible = count > 0 || showLoading;
  queuedSend.classList.toggle('is-visible', visible);
  queuedSend.classList.toggle('is-loading', showLoading);
  queuedSendList.innerHTML = '';
  if (showLoading) {
    queuedSend.classList.add('is-sending');
    queuedSendLabel.textContent = '同步中';
    const placeholder = document.createElement('div');
    placeholder.className = 'queued-send-placeholder';
    placeholder.textContent = '正在读取排队消息…';
    queuedSendList.appendChild(placeholder);
    updateComposerViewportPlacement();
    maybeScrollThreadForComposerGrowth(previousVisible, previousHeight);
    return;
  }
  if (!count) {
    queuedSend.classList.remove('is-sending', 'is-loading');
    updateComposerViewportPlacement();
    maybeScrollThreadForComposerGrowth(previousVisible, previousHeight);
    return;
  }
  const hasSending = queuedSends.some(item => item.state === 'sending');
  queuedSend.classList.toggle('is-sending', hasSending);
  queuedSendLabel.textContent = hasSending ? '同步中' : count > 1 ? `待发送 ${count}` : '待发送';
  queuedSends.forEach(item => {
    const row = document.createElement('div');
    const body = document.createElement('div');
    const state = document.createElement('span');
    const text = document.createElement('span');
    const actions = document.createElement('div');
    const guide = document.createElement('button');
    const edit = document.createElement('button');
    const remove = document.createElement('button');
    const sending = item.state === 'sending';
    const itemText = item.text || item.summary || '';
    const guideBusy = queuedSendActionBusyKey === queuedSendActionKey('guide', itemText);
    const editBusy = queuedSendActionBusyKey === queuedSendActionKey('edit', itemText);
    const deleteBusy = queuedSendActionBusyKey === queuedSendActionKey('delete', itemText);
    row.className = 'queued-send-item';
    body.className = 'queued-send-body';
    state.className = 'queued-send-state';
    text.className = 'queued-send-text';
    actions.className = 'queued-send-actions';
    state.textContent = sending ? '正在同步 Codex 排队消息' : '来自 Codex 原生排队';
    text.textContent = item.summary;
    guide.className = 'queued-send-action is-primary';
    guide.type = 'button';
    guide.textContent = guideBusy ? '处理中' : '引导';
    guide.title = '使用 Codex 原生引导处理这条排队消息';
    guide.setAttribute('aria-label', guide.title);
    guide.disabled = sending || Boolean(queuedSendActionBusyKey);
    guide.addEventListener('click', event => {
      event.preventDefault();
      event.stopPropagation();
      if (guide.disabled) return;
      runQueuedSendAction('guide', itemText);
    });
    edit.className = 'queued-send-action is-edit';
    edit.type = 'button';
    edit.textContent = editBusy ? '处理中' : '编辑';
    edit.title = '删除这条排队消息，并放回输入框编辑';
    edit.setAttribute('aria-label', edit.title);
    edit.disabled = sending || Boolean(queuedSendActionBusyKey);
    edit.addEventListener('click', event => {
      event.preventDefault();
      event.stopPropagation();
      if (edit.disabled) return;
      runQueuedSendAction('edit', itemText);
    });
    remove.className = 'queued-send-action is-danger';
    remove.type = 'button';
    remove.textContent = deleteBusy ? '处理中' : '删除';
    remove.title = '删除 Codex 原生排队消息';
    remove.setAttribute('aria-label', remove.title);
    remove.disabled = sending || Boolean(queuedSendActionBusyKey);
    remove.addEventListener('click', event => {
      event.preventDefault();
      event.stopPropagation();
      if (remove.disabled) return;
      runQueuedSendAction('delete', itemText);
    });
    body.append(state, text);
    actions.append(guide, edit, remove);
    row.append(body, actions);
    queuedSendList.appendChild(row);
  });
  updateComposerViewportPlacement();
  maybeScrollThreadForComposerGrowth(previousVisible, previousHeight);
}

function setQueuedSendsFromCodex(items = [], options = {}) {
  queuedSends = (Array.isArray(items) ? items : [])
    .map((item, index) => {
      const text = String(item.text || item.summary || '').replace(/\s+/g, ' ').trim();
      if (!text) return null;
      return {
        text,
        summary: text,
        order: Number.isFinite(Number(item.order)) ? Number(item.order) : index,
        state: 'queued',
      };
    })
    .filter(Boolean)
    .sort((a, b) => a.order - b.order);
  pruneGuidedQueuedSendKeys(items);
  if (!options.skipCache && selectedThreadId) rememberQueuedSends(selectedThreadId, items);
  renderQueuedSends();
}

function clearQueuedSends() {
  queuedSendLoading = false;
  if (!queuedSends.length && !queuedSend.classList.contains('is-visible')) return;
  queuedSends = [];
  renderQueuedSends();
}

async function refreshQueuedSends(options = {}) {
  if (!selectedThreadId || isPendingNewThreadView()) {
    clearQueuedSends();
    return;
  }
  if (queuedSendRefreshBusy) {
    if (options.force) scheduleQueuedSendRefresh(350, { ...options, force: false });
    return;
  }
  queuedSendRefreshBusy = true;
  try {
    const params = new URLSearchParams({ token, thread: selectedThreadId });
    const response = await fetchApi(`/codex/pending-sends?${params}`, {
      cache: 'no-store',
      apiTimeoutMs: 10000,
      routeSwitchQuiet: true,
      retryProbeTimeoutMs: 700,
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok || !data.ok) throw new Error(data.message || '读取 Codex 排队消息失败');
    if (selectedThreadId !== data.threadId) return;
    const items = data.items || [];
    const changed = queuedSendsRawSignature(items) !== queuedSendsCurrentSignature();
    queuedSendLoading = false;
    if (changed) {
      setQueuedSendsFromCodex(items);
    } else {
      rememberQueuedSends(selectedThreadId, items);
      if (queuedSend.classList.contains('is-loading')) renderQueuedSends();
    }
  } catch (error) {
    queuedSendLoading = false;
    if (queuedSend.classList.contains('is-loading')) renderQueuedSends();
    if (options.showError) setNotice(error.message || '读取 Codex 排队消息失败', 'error');
    else console.warn('Codex Go queued sends refresh skipped:', error);
  } finally {
    queuedSendRefreshBusy = false;
  }
}

function scheduleQueuedSendRefresh(delayMs = 0, options = {}) {
  if (queuedSendRefreshTimer) window.clearTimeout(queuedSendRefreshTimer);
  queuedSendRefreshTimer = window.setTimeout(() => {
    queuedSendRefreshTimer = null;
    refreshQueuedSends(options).catch(error => console.warn('Codex Go queued sends refresh skipped:', error));
  }, Math.max(0, delayMs));
}

async function runQueuedSendAction(action, text) {
  if (!selectedThreadId || !text) return;
  queuedSendActionBusyKey = queuedSendActionKey(action, text);
  const backendAction = action === 'edit' ? 'delete' : action;
  renderQueuedSends();
  setWorkingDot(true);
  setNotice(
    action === 'edit'
      ? '正在移回输入框…'
      : action === 'delete'
        ? '正在删除 Codex 排队消息…'
        : '正在引导 Codex 排队消息…',
    'ok',
  );
  try {
    const response = await fetchApi('/codex/pending-send-action', {
      method: 'POST',
      headers: { 'content-type': 'application/json', 'x-codex-go-token': token },
      body: JSON.stringify({ threadId: selectedThreadId, action: backendAction, text }),
      apiTimeoutMs: 15000,
      routeSwitchQuiet: true,
      retryProbeTimeoutMs: 700,
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok || !data.ok) throw new Error(data.message || '排队消息操作失败');
    if (action === 'guide' && !isQueuedSendGuided(text)) {
      markQueuedSendGuided(text);
      appendGuidedSendNoteToThread(text);
    }
    if (action === 'edit') moveQueuedSendToComposer(text);
    setNotice(
      action === 'edit'
        ? '已移回输入框，可继续编辑'
        : data.message || (action === 'delete' ? '已删除 Codex 排队消息' : '已引导 Codex 排队消息'),
      'ok',
    );
  } catch (error) {
    setNotice(error.message || '排队消息操作失败', 'error');
  } finally {
    queuedSendActionBusyKey = '';
    if (!activeAssistant && !pollTimer) setWorkingDot(false);
    scheduleQueuedSendRefresh(250, { force: true, showError: true });
  }
}

function appendImagesToBubble(message, attachments) {
  if (!attachments.length) return;
  for (const item of attachments) {
    if (isImageAttachment(item)) {
      const img = document.createElement('img');
      img.className = 'attachment-preview';
      img.src = item.dataUrl;
      img.alt = item.name || '图片';
      message.bubble.appendChild(img);
    } else {
      const note = document.createElement('div');
      note.className = 'attachment-note';
      note.textContent = `${attachmentKindLabel(attachmentKind(item))}：${item.name || '附件'}`;
      message.bubble.appendChild(note);
    }
  }
}

function messageEl(role, text, options = {}) {
  const article = document.createElement('article');
  article.className = `message ${role}${options.pending ? ' pending' : ''}`;
  if (selectedThreadId) article.dataset.threadId = selectedThreadId;
  const wrap = document.createElement('div');
  const meta = document.createElement('div');
  const bubble = document.createElement('div');
  wrap.className = 'bubble-wrap';
  meta.className = 'meta';
  bubble.className = 'bubble markdown-body';
  setMetaLabel(meta, options.label || (role === 'user' ? '你' : 'Codex'));
  setMarkdown(bubble, text);
  wrap.append(meta, bubble);
  article.appendChild(wrap);
  thread.appendChild(article);
  if (!options.skipScroll) scrollBottom();
  return { article, bubble, meta, role };
}

function permissionActionLabel(action = {}) {
  const id = String(action.id || '');
  if (id === 'allow') return '是';
  if (id === 'allow_always') return '总是';
  if (id === 'deny') return '跳过';
  return action.label || id || '处理';
}

function permissionActionNotice(action) {
  if (action === 'deny') return '正在跳过 Codex 权限请求…';
  if (action === 'allow_always') return '正在总是允许 Codex 权限请求…';
  return '正在允许 Codex 权限请求…';
}

function updatePermissionActions(message, request, statusData = {}) {
  if (!message?.bubble) return;
  let actions = message.bubble.querySelector('.permission-actions');
  const pending = Boolean(request && request.pending);
  if (!pending) {
    actions?.remove();
    return;
  }
  if (!actions) {
    actions = document.createElement('div');
    actions.className = 'permission-actions';
    message.bubble.appendChild(actions);
  }
  const availableActions = Array.isArray(request.actions) && request.actions.length
    ? request.actions
    : [{ id: 'allow' }, { id: 'allow_always' }, { id: 'deny' }];
  actions.innerHTML = '';
  for (const action of availableActions) {
    const id = String(action.id || '');
    if (!id) continue;
    const button = document.createElement('button');
    button.type = 'button';
    button.className = `permission-action-btn${id === 'allow' ? ' is-primary' : id === 'deny' ? ' is-danger' : ''}`;
    button.textContent = resolvingPermission ? '处理中…' : permissionActionLabel(action);
    button.disabled = resolvingPermission;
    button.addEventListener('click', () => resolvePermissionRequest(id, request, statusData));
    actions.appendChild(button);
  }
}

async function resolvePermissionRequest(action, request = {}, statusData = {}) {
  if (resolvingPermission) return;
  const threadId = statusData.threadId || activeWatch?.threadId || selectedThreadId || '';
  if (!threadId || !request.callId) {
    setNotice('没有可处理的权限请求', 'error');
    return;
  }
  resolvingPermission = true;
  updatePermissionActions(activeAssistant, request, statusData);
  setWorkingDot(true);
  setNotice(permissionActionNotice(action), 'ok');
  try {
    const response = await fetchApi('/codex/permission-action', {
      method: 'POST',
      headers: { 'content-type': 'application/json', 'x-codex-go-token': token },
      body: JSON.stringify({ threadId, callId: request.callId, action }),
      apiTimeoutMs: 15000,
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok || !data.ok) throw new Error(data.message || '权限操作失败');
    setNotice(data.message || '已处理权限请求', 'ok');
  } catch (error) {
    setNotice(error.message || '权限操作失败，请在电脑端手动处理', 'error');
  } finally {
    resolvingPermission = false;
    if (activeAssistant && activeWatch) {
      pollStatus(activeWatch, pollGeneration).catch(() => {});
    } else {
      setWorkingDot(false);
    }
  }
}

function addDetails(message, steps = []) {
  const old = message.article.querySelector('details.process');
  if (old) old.remove();
  if (!steps.length) return;
  const details = document.createElement('details');
  const summary = document.createElement('summary');
  const list = document.createElement('ul');
  details.className = 'process';
  list.className = 'steps';
  summary.textContent = '查看详细过程';
  for (const step of steps) {
    const li = document.createElement('li');
    li.textContent = `${step.label || '事件'}：${step.text || ''}`;
    list.appendChild(li);
  }
  details.append(summary, list);
  message.article.querySelector('.bubble-wrap').appendChild(details);
}

function captureVisibleProcessSteps(message) {
  if (!message?.bubble) return [];
  const steps = [];
  for (const node of [...message.bubble.querySelectorAll('.process-start, .process-complete, .process-error, .process-commentary, .process-thinking, .process-tool, .process-permission')]) {
    const text = node.textContent.replace(/\s+/g, ' ').trim();
    if (!text) continue;
    let label = '过程';
    if (node.classList.contains('process-thinking')) label = '思考';
    else if (node.classList.contains('process-commentary')) label = '进度';
    else if (node.classList.contains('process-tool')) label = '工具';
    else if (node.classList.contains('process-permission')) label = '权限';
    else if (node.classList.contains('process-start')) label = '开始';
    else if (node.classList.contains('process-complete')) label = '完成';
    else if (node.classList.contains('process-error')) label = '失败';
    steps.push({ label, text });
  }
  const plain = message.bubble.textContent.replace(/\s+/g, ' ').trim();
  if (!steps.length && plain && plain !== '已发送，等待 Codex 开始回复…' && plain !== 'Codex 正在回复…') {
    steps.push({ label: '已生成内容', text: plain });
  }
  return steps;
}

function chatStorageKey(threadId = selectedThreadId) {
  return `${STORAGE_PREFIX}.${threadId || 'default'}`;
}

const COMPOSER_DRAFT_PREFIX = 'codexGoComposer.v1';
const composerDraftMemory = new Map();
let composerDraftSaveTimer = null;

function composerDraftKey(threadId = selectedThreadId) {
  if (isPendingNewThreadView()) {
    const scope = pendingNewThread?.scope || 'conversation';
    const project = pendingNewThread?.projectPath || pendingNewThread?.cwd || '';
    return `__new__:${scope}:${project}`;
  }
  return threadId || '__none__';
}

function snapshotComposerDraft() {
  return {
    text: textarea.value,
    attachments: pendingAttachments.map(({ name, type, dataUrl }) => ({ name, type, dataUrl })),
  };
}

function readComposerDraft(key) {
  if (!key) return null;
  if (composerDraftMemory.has(key)) return composerDraftMemory.get(key);
  try {
    const raw = localStorage.getItem(`${COMPOSER_DRAFT_PREFIX}.${key}`);
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    if (!parsed || typeof parsed !== 'object') return null;
    return {
      text: typeof parsed.text === 'string' ? parsed.text : '',
      attachments: Array.isArray(parsed.attachments) ? parsed.attachments : [],
    };
  } catch {
    return null;
  }
}

function writeComposerDraft(key, draft) {
  if (!key) return;
  const payload = {
    text: String(draft?.text || ''),
    attachments: Array.isArray(draft?.attachments)
      ? draft.attachments.slice(0, 6).map(item => ({
          name: item?.name || 'attachment',
          type: item?.type || 'application/octet-stream',
          dataUrl: item?.dataUrl || '',
        })).filter(item => item.dataUrl)
      : [],
  };
  if (!payload.text.trim() && !payload.attachments.length) {
    clearComposerDraft(key);
    return;
  }
  composerDraftMemory.set(key, payload);
  try {
    localStorage.setItem(`${COMPOSER_DRAFT_PREFIX}.${key}`, JSON.stringify(payload));
  } catch (error) {
    console.warn('Codex Go composer draft skipped:', error);
    try {
      const textOnly = { text: payload.text, attachments: [] };
      if (!textOnly.text.trim()) {
        clearComposerDraft(key);
        return;
      }
      localStorage.setItem(`${COMPOSER_DRAFT_PREFIX}.${key}`, JSON.stringify(textOnly));
      composerDraftMemory.set(key, textOnly);
    } catch {
      clearComposerDraft(key);
    }
  }
}

function clearComposerDraft(key = composerDraftKey()) {
  if (!key) return;
  composerDraftMemory.delete(key);
  try {
    localStorage.removeItem(`${COMPOSER_DRAFT_PREFIX}.${key}`);
  } catch {
    // ignore storage failures
  }
}

function saveComposerDraftForKey(key = composerDraftKey()) {
  writeComposerDraft(key, snapshotComposerDraft());
}

function applyComposerDraft(key = composerDraftKey()) {
  const draft = readComposerDraft(key);
  textarea.value = draft?.text || '';
  pendingAttachments = Array.isArray(draft?.attachments)
    ? draft.attachments.map(item => ({
        name: item?.name || 'attachment',
        type: item?.type || 'application/octet-stream',
        dataUrl: item?.dataUrl || '',
      })).filter(item => item.dataUrl)
    : [];
  renderAttachmentTray();
  autosize();
  updateComposerAction();
}

function migrateComposerDraft(fromKey, toKey) {
  if (!fromKey || !toKey || fromKey === toKey) return;
  const draft = readComposerDraft(fromKey);
  if (draft) writeComposerDraft(toKey, draft);
  clearComposerDraft(fromKey);
}

function scheduleComposerDraftSave() {
  clearTimeout(composerDraftSaveTimer);
  composerDraftSaveTimer = window.setTimeout(() => {
    saveComposerDraftForKey();
  }, 200);
}

function clearThreadMessages() {
  [...thread.querySelectorAll('.message')].forEach(node => node.remove());
}

function updateThreadTitle() {
  if (isPendingNewThreadView()) {
    const suffix = pendingNewThread.projectName && pendingNewThread.projectName !== '对话' ? ` · ${pendingNewThread.projectName}` : '';
    threadNameEl.textContent = `新线程${suffix}`;
    document.body.classList.remove('thread-current-pinned');
    document.title = `新线程${suffix} · Codex Go`;
    return;
  }
  const current = knownThreads.find(item => item.id === selectedThreadId);
  threadNameEl.textContent = current ? current.name : '选择线程';
  document.body.classList.toggle('thread-current-pinned', Boolean(current?.pinned));
  document.title = current ? `${current.name} · Codex Go` : 'Codex Go';
}

function formatRelativeTime(value) {
  const then = Date.parse(value || '');
  if (!Number.isFinite(then)) return '';
  const seconds = Math.max(0, Math.floor((Date.now() - then) / 1000));
  if (seconds < 60) return '刚刚';
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes} 分钟`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours} 小时`;
  const days = Math.floor(hours / 24);
  if (days < 7) return `${days} 天`;
  const weeks = Math.floor(days / 7);
  if (weeks < 8) return `${weeks} 周`;
  const months = Math.floor(days / 30);
  if (months < 12) return `${months} 个月`;
  return `${Math.floor(days / 365)} 年`;
}

function threadSortTimeMs(item) {
  return Date.parse(item?.effectiveUpdatedAt || item?.updatedAt || '') || item?.effectiveUpdatedMs || 0;
}

function sortThreadsByTime(items) {
  return [...items].sort((a, b) => {
    const delta = threadSortTimeMs(b) - threadSortTimeMs(a);
    if (delta !== 0) return delta;
    return String(a.id || '').localeCompare(String(b.id || ''));
  });
}

function threadMenuStateForItem(item) {
  const runtime = threadRuntimeStates.get(item.id) || runtimeSnapshotFromThread(item) || {};
  if (isThreadPermissionStatus(runtime.status)) return 'permission';
  if (isThreadRunningStatus(runtime.status)) return 'running';
  if (completedThreadIds.has(item.id) && item.id !== selectedThreadId) return 'done';
  return 'time';
}

function threadMenuVisualSignature() {
  const threadPart = [...knownThreads]
    .sort((a, b) => String(a.id || '').localeCompare(String(b.id || '')))
    .map(item => `${item.id}:${item.name || ''}:${item.pinned ? 'pinned' : 'normal'}:${threadMenuStateForItem(item)}`)
    .join('|');
  const openPart = [...openProjectKeys].sort().join(',');
  return `${selectedThreadId}::${openPart}::${threadPart}`;
}

function renderThreadMenuIfVisualChanged() {
  if (threadMenuVisualSignature() !== lastThreadMenuSignature) renderThreadMenu();
}

function wireThreadMenuItemInteractions(button, item) {
  let timer = 0;
  let startPoint = null;
  let longPressReady = false;
  let handledAt = 0;
  let activePointerId = null;
  const releaseCapture = () => {
    if (activePointerId === null) return;
    try { button.releasePointerCapture(activePointerId); } catch {}
    activePointerId = null;
  };
  const cancel = () => {
    window.clearTimeout(timer);
    timer = 0;
    startPoint = null;
    longPressReady = false;
    releaseCapture();
  };
  button.addEventListener('pointerdown', event => {
    if (event.button !== 0) return;
    startPoint = { x: event.clientX || 0, y: event.clientY || 0 };
    longPressReady = false;
    window.clearTimeout(timer);
    activePointerId = event.pointerId;
    try { button.setPointerCapture(event.pointerId); } catch {}
    timer = window.setTimeout(() => {
      longPressReady = true;
      vibrateForLongPress();
    }, 560);
  });
  button.addEventListener('pointermove', event => {
    if (!startPoint || activePointerId !== event.pointerId) return;
    const dx = Math.abs((event.clientX || 0) - startPoint.x);
    const dy = Math.abs((event.clientY || 0) - startPoint.y);
    if (dx > 12 || dy > 12) cancel();
  });
  button.addEventListener('pointerup', event => {
    if (event.button !== 0) return;
    const ready = longPressReady;
    const shouldSelect = Boolean(startPoint && !ready);
    cancel();
    handledAt = Date.now();
    if (ready) {
      if (event.cancelable) event.preventDefault();
      event.stopPropagation();
      clearNativeSelection();
      openThreadActionCard(item.id, { anchorElement: button, keepThreadMenu: true });
      return;
    }
    if (shouldSelect) {
      if (event.cancelable) event.preventDefault();
      event.stopPropagation();
      selectThread(item.id);
    }
  });
  button.addEventListener('pointercancel', cancel);
  button.addEventListener('contextmenu', event => {
    event.preventDefault();
    event.stopPropagation();
    cancel();
    handledAt = Date.now();
    clearNativeSelection();
    openThreadActionCard(item.id, { anchorElement: button, keepThreadMenu: true, vibrate: true });
  });
  button.addEventListener('click', event => {
    event.preventDefault();
    event.stopPropagation();
    if (Date.now() - handledAt < 700) return;
    selectThread(item.id);
  });
}

function appendThreadOption(parent, item, isConversation = false) {
  const button = document.createElement('button');
  const name = document.createElement('span');
  const state = document.createElement('span');
  const runtime = threadRuntimeStates.get(item.id) || runtimeSnapshotFromThread(item) || {};
  button.className = `thread-option${isConversation ? ' is-conversation' : ''}${item.pinned ? ' is-pinned' : ''}${isThreadPermissionStatus(runtime.status) ? ' is-permission-required' : ''}`;
  button.type = 'button';
  button.title = item.cwd || item.projectPath || item.name || '';
  button.setAttribute('aria-current', String(item.id === selectedThreadId));
  name.className = 'thread-option-title';
  state.className = 'thread-option-state';
  const text = document.createElement('span');
  text.className = 'thread-title-text';
  text.textContent = item.name || '未命名线程';
  if (item.pinned) {
    const pin = document.createElement('span');
    pin.className = 'thread-title-pin';
    pin.innerHTML = PIN_ICON;
    name.append(pin, text);
  } else {
    name.appendChild(text);
  }
  if (isThreadPermissionStatus(runtime.status)) {
    const badge = document.createElement('span');
    badge.className = 'thread-option-permission-badge';
    badge.setAttribute('aria-hidden', 'true');
    badge.innerHTML = '<span class="thread-option-permission-dot"></span><span class="thread-option-permission-text">授权</span>';
    state.title = '这个线程正在等待授权';
    state.setAttribute('aria-label', '等待授权');
    state.appendChild(badge);
  } else if (isThreadRunningStatus(runtime.status)) {
    const spinner = document.createElement('span');
    spinner.className = 'thread-option-spinner';
    spinner.setAttribute('aria-hidden', 'true');
    spinner.style.animationDelay = `${-(performance.now() % THREAD_SPINNER_MS)}ms`;
    state.title = '这个线程正在回复';
    state.setAttribute('aria-label', '正在回复');
    state.appendChild(spinner);
  } else if (completedThreadIds.has(item.id) && item.id !== selectedThreadId) {
    state.title = '这个线程刚刚回复完毕';
    state.setAttribute('aria-label', '刚刚回复完毕');
    state.innerHTML = '<span class="thread-option-dot" aria-hidden="true"></span>';
  } else {
    state.textContent = formatRelativeTime(item.effectiveUpdatedAt || item.updatedAt) || item.id.slice(0, 8);
  }
  button.append(name, state);
  wireThreadMenuItemInteractions(button, item);
  parent.appendChild(button);
}

function appendPinnedThreadOption(parent, item) {
  const button = document.createElement('button');
  const icon = document.createElement('span');
  const name = document.createElement('span');
  const meta = document.createElement('small');
  const runtime = threadRuntimeStates.get(item.id) || runtimeSnapshotFromThread(item) || {};
  button.className = `pinned-thread-option${isThreadPermissionStatus(runtime.status) ? ' is-permission-required' : ''}`;
  button.type = 'button';
  button.title = item.cwd || item.projectPath || item.name || '';
  button.setAttribute('aria-current', String(item.id === selectedThreadId));
  icon.className = 'pinned-thread-icon';
  name.className = 'pinned-thread-name';
  meta.className = 'pinned-thread-meta';
  icon.innerHTML = PIN_ICON;
  name.textContent = item.name || '未命名线程';
  if (isThreadPermissionStatus(runtime.status)) {
    meta.classList.add('is-permission');
    meta.textContent = '等待授权';
    meta.setAttribute('aria-label', '等待授权');
  } else {
    meta.textContent = formatRelativeTime(item.effectiveUpdatedAt || item.updatedAt) || '';
  }
  button.append(icon, name, meta);
  wireThreadMenuItemInteractions(button, item);
  parent.appendChild(button);
}

function appendProjectGroup(parent, group, isCurrent = false) {
  const isOpen = openProjectKeys.has(group.key);
  const wrap = document.createElement('div');
  const header = document.createElement('button');
  const folder = document.createElement('span');
  const name = document.createElement('span');
  const count = document.createElement('small');
  const list = document.createElement('div');
  wrap.className = `project-group${isOpen ? ' is-open' : ''}`;
  header.className = `project-header${isCurrent ? ' is-current' : ''}`;
  header.type = 'button';
  header.setAttribute('aria-expanded', String(isOpen));
  header.setAttribute('aria-label', `${isOpen ? '收起' : '展开'}项目 ${group.name || '未命名项目'}`);
  folder.className = 'project-folder';
  folder.innerHTML = '<svg viewBox="0 0 24 20" aria-hidden="true"><path d="M3.8 6.2V5.1c0-1.2.8-2 2-2h4.1c.8 0 1.25.22 1.8.84l1.05 1.16c.36.4.67.56 1.28.56h4.15c1.35 0 2.02.68 2.02 2.02v7.2c0 1.34-.67 2.02-2.02 2.02H5.82c-1.35 0-2.02-.68-2.02-2.02V6.2Z"/><path d="M4 7.1h16"/></svg>';
  name.className = 'project-name';
  list.className = 'thread-list';
  folder.setAttribute('aria-hidden', 'true');
  name.textContent = group.name || '未命名项目';
  count.textContent = `${group.items.length} 条`;
  header.title = group.path || group.name || '';
  header.append(folder, name, count);
  header.addEventListener('click', event => {
    event.stopPropagation();
    if (openProjectKeys.has(group.key)) openProjectKeys.delete(group.key);
    else openProjectKeys.add(group.key);
    persistOpenProjectKeys();
    renderThreadMenu();
  });
  for (const item of sortThreadsByTime(group.items)) appendThreadOption(list, item);
  wrap.append(header, list);
  parent.appendChild(wrap);
}

function renderThreadMenu() {
  const previousScrollTop = threadMenu.scrollTop;
  threadMenu.innerHTML = '';
  if (!knownThreads.length) {
    const empty = document.createElement('div');
    empty.className = 'empty-thread-menu';
    empty.textContent = '还没有读取到 Codex 线程。';
    threadMenu.appendChild(empty);
    lastThreadMenuSignature = threadMenuVisualSignature();
    positionThreadMenuCard();
    threadMenu.scrollTop = previousScrollTop;
    return;
  }

  const current = knownThreads.find(item => item.id === selectedThreadId);
  const currentProjectKey = current?.isProjectThread ? current.projectKey : '';
  const projectMap = new Map();
  const conversations = [];
  const pinnedThreads = sortThreadsByTime(knownThreads.filter(item => item.pinned));

  for (const item of knownThreads) {
    if (item.pinned) continue;
    if (!item.isProjectThread) {
      conversations.push(item);
      continue;
    }
    const key = item.projectKey || item.projectPath || item.cwd || 'project';
    if (!projectMap.has(key)) {
      projectMap.set(key, {
        key,
        name: item.projectName || '未命名项目',
        path: item.projectPath || item.cwd || '',
        latest: 0,
        items: [],
      });
    }
    const group = projectMap.get(key);
    group.items.push(item);
    group.latest = Math.max(group.latest, Date.parse(item.effectiveUpdatedAt || item.updatedAt || '') || item.effectiveUpdatedMs || 0);
  }

  const projectGroups = [...projectMap.values()].sort((a, b) => b.latest - a.latest);
  if (!hasSavedProjectGroupState && projectGroups.length && !openProjectKeys.size) {
    openProjectKeys.add(currentProjectKey || projectGroups[0].key);
    persistOpenProjectKeys();
  }

  if (pinnedThreads.length) {
    const section = document.createElement('section');
    const label = document.createElement('div');
    section.className = 'thread-section';
    label.className = 'thread-section-label';
    label.textContent = '置顶';
    section.appendChild(label);
    pinnedThreads.forEach(item => appendPinnedThreadOption(section, item));
    threadMenu.appendChild(section);
  }

  if (projectGroups.length) {
    const section = document.createElement('section');
    const label = document.createElement('div');
    section.className = 'thread-section';
    label.className = 'thread-section-label';
    label.textContent = '项目';
    section.appendChild(label);
    projectGroups.forEach(group => appendProjectGroup(section, group, group.key === currentProjectKey));
    threadMenu.appendChild(section);
  }

  if (conversations.length) {
    const section = document.createElement('section');
    const label = document.createElement('div');
    const list = document.createElement('div');
    section.className = 'thread-section';
    label.className = 'thread-section-label';
    list.className = 'thread-list';
    label.textContent = '对话';
    for (const item of sortThreadsByTime(conversations)) appendThreadOption(list, item, true);
    section.append(label, list);
    threadMenu.appendChild(section);
  }
  lastThreadMenuSignature = threadMenuVisualSignature();
  positionThreadMenuCard();
  threadMenu.scrollTop = previousScrollTop;
}

async function loadThreads(options = {}) {
  const detectTransitions = Boolean(options.detectTransitions);
  const renderMode = options.renderMenu || 'always';
  const response = await fetchApi(`/codex/threads?limit=120&token=${encodeURIComponent(token)}`, { cache: 'no-store' });
  const data = await response.json();
  if (!data.ok) throw new Error(data.message || '读取线程失败');
  knownThreads = data.threads || [];
  for (const item of knownThreads) {
    applyThreadRuntimeState(item.id, runtimeSnapshotFromThread(item), { detectTransitions });
  }
  pruneCompletedThreadNotices();
  if (!pendingNewThread && (!selectedThreadId || !knownThreads.some(item => item.id === selectedThreadId))) {
    selectedThreadId = knownThreads[0]?.id || '';
    if (selectedThreadId) localStorage.setItem('codexGo.selectedThread', selectedThreadId);
  }
  setThreadCompleteNotice(selectedThreadId, false);
  updateThreadTitle();
  if (renderMode === 'ifChanged') renderThreadMenuIfVisualChanged();
  else renderThreadMenu();
}

async function openCodexThread(threadId, apiOptions = {}) {
  if (!threadId) return;
  const response = await fetchApi('/codex/select', {
    method: 'POST',
    headers: { 'content-type': 'application/json', 'x-codex-go-token': token },
    body: JSON.stringify({ threadId }),
    apiTimeoutMs: 15000,
    ...apiOptions,
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok || !data.ok) throw new Error(data.message || '切换 Codex 线程失败');
  return data;
}

function currentThreadItem() {
  return knownThreads.find(item => item.id === selectedThreadId) || null;
}

function threadItemById(threadId) {
  return knownThreads.find(item => item.id === threadId) || null;
}

function actionThreadItem() {
  return threadItemById(actionThreadId || selectedThreadId);
}

function closeThreadActionCard() {
  threadActionCard.classList.remove('is-open', 'is-renaming');
  threadActionCard.style.left = '';
  threadActionCard.style.top = '';
  threadRenameInput.blur();
}

function cancelThreadRename() {
  suppressThreadClickUntil = Date.now() + 700;
  closeThreadActionCard();
}

function viewportHeight() {
  return Math.round((window.visualViewport && window.visualViewport.height) || window.innerHeight || document.documentElement.clientHeight || 0);
}

function positionThreadActionCard(anchorElement) {
  if (!anchorElement || typeof anchorElement.getBoundingClientRect !== 'function') return;
  const anchor = anchorElement.getBoundingClientRect();
  const viewportWidth = window.innerWidth || document.documentElement.clientWidth || 0;
  const viewportHeight = window.innerHeight || document.documentElement.clientHeight || 0;
  const margin = 10;
  const cardWidth = threadActionCard.offsetWidth || 224;
  const cardHeight = threadActionCard.offsetHeight || 160;
  if (threadMenu?.classList.contains('is-open') && threadMenu.contains(anchorElement)) {
    const menuRect = threadMenu.getBoundingClientRect();
    const besideMenuLeft = menuRect.right + 8;
    const left = besideMenuLeft + cardWidth + margin <= viewportWidth
      ? besideMenuLeft
      : Math.max(margin, Math.min(viewportWidth - cardWidth - margin, anchor.left + anchor.width / 2 - cardWidth / 2));
    const top = Math.max(margin, Math.min(viewportHeight - cardHeight - margin, anchor.top));
    threadActionCard.style.left = `${Math.round(left)}px`;
    threadActionCard.style.top = `${Math.round(top)}px`;
    return;
  }
  const anchorCenterX = anchor.left + anchor.width / 2;
  const left = Math.max(margin, Math.min(viewportWidth - cardWidth - margin, anchorCenterX - cardWidth / 2));
  const belowTop = anchor.bottom + 6;
  const aboveTop = anchor.top - cardHeight - 6;
  const hasRoomBelow = belowTop + cardHeight + margin <= viewportHeight;
  const top = hasRoomBelow ? belowTop : Math.max(margin, aboveTop);
  threadActionCard.style.left = `${Math.round(left)}px`;
  threadActionCard.style.top = `${Math.round(top)}px`;
}

function vibrateForLongPress() {
  let fired = false;
  try {
    window.Telegram?.WebApp?.HapticFeedback?.impactOccurred?.('medium');
    fired = true;
  } catch {}
  try {
    window.webkit?.messageHandlers?.haptic?.postMessage?.('medium');
    fired = true;
  } catch {}
  try {
    window.webkit?.messageHandlers?.hapticFeedback?.postMessage?.({ type: 'impact', style: 'medium' });
    fired = true;
  } catch {}
  try {
    window.webkit?.messageHandlers?.vibrate?.postMessage?.([45, 25, 45]);
    fired = true;
  } catch {}
  try {
    if (navigator.vibrate) {
      navigator.vibrate([45, 25, 45]);
      fired = true;
    }
  } catch {}
  return fired;
}

function openThreadActionCard(threadId = selectedThreadId, options = {}) {
  const current = threadItemById(threadId);
  if (!current || !threadId) return;
  actionThreadId = threadId;
  if (!options.keepThreadMenu) threadMenu.classList.remove('is-open');
  closeReasoningMenu();
  closeModelMenu();
  threadActionCard.style.left = '';
  threadActionCard.style.top = '';
  threadActionCard.classList.toggle('is-pinned', Boolean(current.pinned));
  threadActionCard.classList.remove('is-renaming');
  threadRenameInput.value = current.name || '';
  threadActionPinToggleText.textContent = current.pinned ? '取消置顶' : '置顶';
  threadActionPinToggle.setAttribute('aria-label', current.pinned ? '取消置顶当前线程' : '置顶当前线程');
  threadActionCard.classList.add('is-open');
  if (options.anchorElement) positionThreadActionCard(options.anchorElement);
  if (options.vibrate) vibrateForLongPress();
}

function showRenamePanel() {
  const current = actionThreadItem();
  if (!current) return;
  threadMenu.classList.remove('is-open');
  threadRenameInput.value = current.name || '';
  threadActionCard.classList.add('is-renaming');
  threadActionCard.style.left = '';
  threadActionCard.style.top = '';
  threadRenameInput.focus({ preventScroll: false });
  try {
    threadRenameInput.setSelectionRange(0, threadRenameInput.value.length);
  } catch {}
  window.setTimeout(() => {
    const rect = threadActionCard.getBoundingClientRect();
    const visibleHeight = viewportHeight();
    if (rect.bottom > visibleHeight - 12) {
      threadActionCard.style.top = `${Math.max(72, visibleHeight - rect.height - 12)}px`;
    }
  }, 80);
}

async function postThreadAction(action, payload = {}) {
  const targetThreadId = actionThreadId || selectedThreadId;
  if (!targetThreadId) throw new Error('还没有选中线程。');
  const response = await fetchApi('/codex/thread-action', {
    method: 'POST',
    headers: { 'content-type': 'application/json', 'x-codex-go-token': token },
    body: JSON.stringify({ action, threadId: targetThreadId, ...payload }),
    apiTimeoutMs: 20000,
    routeSwitchQuiet: true,
    retryProbeTimeoutMs: 900,
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok || !data.ok) throw new Error(data.message || '线程操作失败');
  return data;
}

async function archiveCurrentThread() {
  const archivedThreadId = actionThreadId || selectedThreadId;
  if (!archivedThreadId) return;
  const archivedSelectedThread = archivedThreadId === selectedThreadId;
  closeThreadActionCard();
  setWorkingDot(true);
  setNotice('正在归档当前 Codex 线程…', 'ok');
  try {
    const data = await postThreadAction('archive');
    completedThreadIds.delete(archivedThreadId);
    knownThreads = knownThreads.filter(item => item.id !== archivedThreadId);
    if (archivedSelectedThread) {
      serializeMessages(archivedThreadId);
      saveComposerDraftForKey(composerDraftKey());
      stopPolling();
      selectedThreadId = '';
      syncedThreadId = '';
      localStorage.removeItem('codexGo.selectedThread');
      await loadThreads();
      const nextThreadId = data.nextThreadId || selectedThreadId || '';
      if (nextThreadId) {
        selectedThreadId = '';
        await selectThread(nextThreadId);
      } else {
        clearThreadMessages();
        applyComposerDraft('__none__');
        updateThreadTitle();
        renderThreadMenu();
      }
    } else {
      renderThreadMenu();
      await loadThreads({ renderMenu: 'always' });
    }
    setNotice('已归档当前线程', 'ok');
  } catch (error) {
    setNotice(error.message || '归档失败', 'error');
  } finally {
    if (!activeAssistant && !pollTimer) setWorkingDot(false);
  }
}

async function toggleCurrentThreadPin() {
  const current = actionThreadItem();
  if (!current) return;
  const targetThreadId = current.id;
  const nextPinned = !current.pinned;
  closeThreadActionCard();
  setWorkingDot(true);
  setNotice(nextPinned ? '正在置顶当前 Codex 线程…' : '正在取消置顶当前 Codex 线程…', 'ok');
  try {
    await postThreadAction(nextPinned ? 'pin' : 'unpin');
    for (const item of knownThreads) {
      if (item.id === targetThreadId) item.pinned = nextPinned;
    }
    if (targetThreadId === selectedThreadId) updateThreadTitle();
    renderThreadMenu();
    await loadThreads({ renderMenu: 'always' });
    setNotice(nextPinned ? '已同步置顶：Codex 和手机列表都会置顶' : '已同步取消置顶', 'ok');
  } catch (error) {
    setNotice(error.message || '置顶操作失败', 'error');
  } finally {
    if (!activeAssistant && !pollTimer) setWorkingDot(false);
  }
}

async function renameCurrentThread() {
  const current = actionThreadItem();
  if (!current) return;
  const targetThreadId = current.id;
  const nextName = threadRenameInput.value.replace(/\s+/g, ' ').trim();
  if (!nextName) {
    setNotice('新名称不能为空', 'error');
    threadRenameInput.focus();
    return;
  }
  if (nextName === current.name) {
    closeThreadActionCard();
    return;
  }
  threadRenameSave.disabled = true;
  setWorkingDot(true);
  setNotice('正在重命名当前 Codex 线程…', 'ok');
  closeThreadActionCard();
  try {
    const data = await postThreadAction('rename', { name: nextName });
    for (const item of knownThreads) {
      if (item.id === targetThreadId) item.name = data.name || nextName;
    }
    if (targetThreadId === selectedThreadId) updateThreadTitle();
    renderThreadMenu();
    window.setTimeout(() => loadThreads({ renderMenu: 'always' }).catch(() => {}), 700);
    setNotice('已重命名当前线程', 'ok');
  } catch (error) {
    setNotice(error.message || '重命名失败', 'error');
  } finally {
    threadRenameSave.disabled = false;
    if (!activeAssistant && !pollTimer) setWorkingDot(false);
  }
}

function createNewThreadInCurrentProject() {
  if (newThreadButton.disabled) return;
  const current = knownThreads.find(item => item.id === selectedThreadId);
  const previousThreadId = selectedThreadId || '';
  const isProjectScope = Boolean(current?.isProjectThread && (current.projectPath || current.cwd));
  const newThreadScope = isProjectScope ? 'project' : 'conversation';
  const projectPath = isProjectScope ? (current?.projectPath || current?.cwd || '') : '';
  const projectName = isProjectScope ? (current?.projectName || '未命名项目') : '对话';
  const previousDraftKey = composerDraftKey();
  threadMenu.classList.remove('is-open');
  saveComposerDraftForKey(previousDraftKey);
  pendingNewThread = {
    cwd: projectPath,
    projectName,
    projectPath,
    previousThreadId,
    scope: newThreadScope,
    isProjectThread: isProjectScope,
    createdAt: new Date().toISOString(),
  };
  detachForegroundRunForNewThread();
  selectedThreadId = '';
  syncedThreadId = '';
  localStorage.removeItem('codexGo.selectedThread');
  clearThreadMessages();
  applyComposerDraft(composerDraftKey());
  const draftHint = isProjectScope
    ? `新线程草稿已就绪（${projectName}）。发送第一条消息后，电脑端 Codex 才会真正创建这个线程。`
    : '新线程草稿已就绪。发送第一条消息后，电脑端 Codex 才会真正创建这个线程。';
  messageEl('assistant', draftHint, { label: 'Codex Go' });
  updateThreadTitle();
  renderThreadMenu();
  resetPendingNewThreadIndicators();
  setNotice(isProjectScope ? `已准备好在“${projectName}”新建线程` : '已准备好新建对话线程', 'ok');
  restoreLayoutAfterKeyboard();
}

async function syncCodexThread(threadId = selectedThreadId, options = {}) {
  if (!threadId) return { ok: false, skipped: true };
  const { quiet = false, force = false } = options;
  if (!force && syncedThreadId === threadId) return { ok: true, threadId, cached: true };

  const requestId = ++syncRequestId;
  const previousStatus = topStatusState || '已连接';
  setWorkingDot(true);
  setTopStatus('同步线程');
  if (!quiet) setNotice('正在同步桌面端 Codex 到当前线程…', 'ok');
  try {
    const data = await openCodexThread(threadId, { routeSwitchQuiet: quiet, retryProbeTimeoutMs: 900 });
    if (requestId === syncRequestId && threadId === selectedThreadId) syncedThreadId = threadId;
    if (!quiet && requestId === syncRequestId) setNotice('桌面端 Codex 已切到当前线程', 'ok');
    return data || { ok: true, threadId };
  } catch (error) {
    if (requestId === syncRequestId) setNotice(error.message || '同步 Codex 线程失败', 'error');
    throw error;
  } finally {
    if (requestId === syncRequestId) {
      setTopStatus(previousStatus === '同步线程' ? '已连接' : previousStatus);
      if (!pollTimer && !activeAssistant) setWorkingDot(false);
    }
  }
}

function isRunningStatus(data) {
  return Boolean(data && (data.active || data.status === 'running' || data.status === 'waiting'));
}

function codexStatusSignature(data) {
  if (!data || !data.available) return '';
  return [
    data.threadId || '',
    data.sessionFile || '',
    data.turnId || '',
    data.status || '',
    data.updatedAt || '',
    data.startedAt || '',
    data.completedAt || '',
    data.permissionRequest?.callId || '',
    data.permissionRequest?.pending ? 'permission-pending' : '',
  ].join('|');
}

function runtimeSnapshotFromStatusData(data) {
  if (!data || !data.available) return null;
  return {
    status: data.status || '',
    active: Boolean(data.active || isThreadRunningStatus(data.status)),
    startedAt: data.startedAt || '',
    completedAt: data.completedAt || '',
    updatedAt: data.updatedAt || data.completedAt || data.startedAt || '',
    turnId: data.turnId || '',
  };
}

async function resumeActiveThreadStatus(threadId, requestId = historyRequestId) {
  if (!threadId) return false;
  const params = new URLSearchParams({ token, thread: threadId });
  const response = await fetchApi(`/codex/status?${params}`, { cache: 'no-store' });
  const data = await response.json();
  if (requestId !== historyRequestId || threadId !== selectedThreadId) return false;
  if (!response.ok || !data.ok || !data.available) return false;
  updateContextFromStatus(data);
  applyThreadRuntimeState(threadId, runtimeSnapshotFromStatusData(data), { detectTransitions: false });
  renderThreadMenuIfVisualChanged();
  lastStatusSignature = codexStatusSignature(data);
  if (isRunningStatus(data) && isLocalStopSuppressed(threadId, data.startedAt)) return false;
  if (!isRunningStatus(data)) return false;

  const durationText = formatDuration(data.durationMs || 0);
  const resumeCommandKind = latestUserCommandKind();
  const resumeCommandUi = commandUi(resumeCommandKind);
  activeAssistant = messageEl('assistant', resumeCommandUi?.pendingText || 'Codex 正在回复…', { label: resumeCommandUi ? resumeCommandUi.runningLabel(durationText) : `Codex · 运行 ${durationText}`, pending: true });
  activeAssistant.commandKind = resumeCommandKind;
  setActiveRunStart(data.startedAt || '', Date.now() - (Number(data.durationMs) || 0));
  activeAssistant.runDurationText = durationText;
  updateComposerAction();
  if (resumeCommandUi) setMarkdown(activeAssistant.bubble, resumeCommandUi.pendingText);
  else renderProcessSteps(activeAssistant.bubble, data.steps || []);
  updatePermissionActions(activeAssistant, data.permissionRequest || null, data);
  setTopStatus(data.status === 'permission_required' ? '等待权限' : resumeCommandUi ? resumeCommandUi.runningNotice(durationText) : `Codex 正在回复 · ${durationText}`);
  setNotice('已接上这个线程正在进行的回复状态', 'ok');
  startPolling({
    since: data.startedAt || '',
    threadId,
    sessionFile: data.sessionFile || '',
  });
  return true;
}

async function loadThreadHistory(threadId = selectedThreadId) {
  if (!threadId) return;
  const requestId = ++historyRequestId;
  clearThreadMessages();
  const loading = messageEl('assistant', '正在加载这个 Codex 线程的本机聊天记录…', { label: 'Codex Go' });
  try {
    const params = new URLSearchParams({ token, thread: threadId, limit: '120' });
    const response = await fetchApi(`/codex/history?${params}`, { cache: 'no-store', apiTimeoutMs: 30000 });
    const data = await response.json();
    if (requestId !== historyRequestId || threadId !== selectedThreadId) return;
    loading.article.remove();
    if (!response.ok || !data.ok) throw new Error(data.message || '读取聊天记录失败');
    if (!data.available || !Array.isArray(data.messages) || !data.messages.length) {
      const resumed = await resumeActiveThreadStatus(threadId, requestId);
      if (!resumed) messageEl('assistant', '这个线程暂时没有可加载的聊天记录。', { label: 'Codex Go' });
      scheduleThreadScrollToBottom();
      return;
    }
    beginHistoryRenderAtBottom();
    try {
      for (const row of data.messages) {
        const msg = messageEl(row.role, row.text || '', {
          label: row.label || (row.role === 'user' ? '你' : 'Codex'),
          skipScroll: true,
        });
        if (row.attachments?.length) {
          const note = document.createElement('div');
          note.className = 'attachment-note';
          note.textContent = row.attachments.map(item => `${attachmentKindLabel(attachmentKind(item))}：${item.name || '附件'}`).join(' · ');
          msg.bubble.appendChild(note);
        }
      }
    } finally {
      finishHistoryRenderAtBottom();
    }
    const resumed = await resumeActiveThreadStatus(threadId, requestId);
    if (!resumed) {
      if (data.truncated) setNotice('已加载最近一部分聊天记录，较早日志太大已省略', 'ok');
      else setNotice('已从本机 Codex 线程加载聊天记录', 'ok');
    }
    scheduleThreadScrollToBottom([0, 80, 200, 500, 1000]);
    if (document.fonts?.ready) {
      document.fonts.ready.then(() => scheduleThreadScrollToBottom([0, 50, 180]));
    }
  } catch (error) {
    if (requestId !== historyRequestId || threadId !== selectedThreadId) return;
    loading.article.remove();
    setNotice(error.message || '读取聊天记录失败', 'error');
    restoreMessages(threadId);
  }
}

async function selectThread(threadId) {
  if (!threadId) return;
  threadMenu.classList.remove('is-open');
  setThreadCompleteNotice(threadId, false);
  const previousDraftKey = composerDraftKey();
  if (pendingNewThread) pendingNewThread = null;
  const leavingThreadId = selectedThreadId;
  if (threadId === selectedThreadId) {
    if (activeAssistant || pollTimer) {
      setNotice('当前正在查看这个线程，回复状态会继续更新', 'ok');
      scheduleQueuedSendRefresh(0, { force: true });
      return;
    }
    setNotice('正在刷新这个线程的本机聊天记录…', 'ok');
    await loadThreadHistory(threadId);
    scheduleQueuedSendRefresh(0, { force: true });
    refreshGuiState({ force: true });
    return;
  }

  serializeMessages(leavingThreadId);
  saveComposerDraftForKey(previousDraftKey);
  stopPolling();
  prepareQueuedSendsForThread(threadId);
  selectedThreadId = threadId;
  syncedThreadId = '';
  localStorage.setItem('codexGo.selectedThread', selectedThreadId);
  setThreadCompleteNotice(selectedThreadId, false);
  activeAssistant = null;
  renderReasoningBadge(bestReasoningMode(null, selectedThreadId));
  renderModelBadge(bestModelInfo(null, selectedThreadId));
  updateComposerAction();
  lastStatusSignature = '';
  clearThreadMessages();
  updateThreadTitle();
  renderThreadMenu();
  applyComposerDraft(composerDraftKey());
  setNotice('已切换到查看线程，正在加载本机聊天记录…', 'ok');

  await loadThreadHistory(threadId);
  scheduleQueuedSendRefresh(0, { force: true });
  refreshGuiState({ force: true });
}

function safeBubbleHtml(article) {
  const bubble = article.querySelector('.bubble');
  if (!bubble) return '';
  const clone = bubble.cloneNode(true);
  for (const img of [...clone.querySelectorAll('img.attachment-preview')]) {
    const note = document.createElement('div');
    note.className = 'attachment-note';
    note.textContent = `图片：${img.alt || '已发送图片'}（刷新后不缓存预览）`;
    img.replaceWith(note);
  }
  const html = clone.innerHTML || '';
  return html.length > 30000 ? `${html.slice(0, 30000)}…` : html;
}

function serializeMessages(threadId = selectedThreadId) {
  if (!threadId) return;
  const rows = [...thread.querySelectorAll('.message')]
    .filter(article => {
      const owner = article.dataset.threadId;
      return !owner || owner === threadId;
    })
    .slice(-30)
    .map(article => ({
      role: article.classList.contains('user') ? 'user' : 'assistant',
      label: article.querySelector('.meta')?.textContent?.replace(/ · 正在回复$/, '') || '',
      html: safeBubbleHtml(article),
    }));
  const key = chatStorageKey(threadId);
  try {
    localStorage.setItem(key, JSON.stringify(rows));
  } catch (error) {
    console.warn('Codex Go chat cache skipped:', error);
    try {
      localStorage.removeItem(key);
      localStorage.setItem(key, JSON.stringify(rows.slice(-8)));
    } catch {
      localStorage.removeItem(key);
    }
  }
}

function serializeMessagesIfStillOnThread(threadId) {
  if (!threadId || threadId !== selectedThreadId) return;
  serializeMessages(threadId);
}

function restoreMessages(threadId = selectedThreadId) {
  if (!threadId || threadId !== selectedThreadId) return;
  try {
    const rows = JSON.parse(localStorage.getItem(chatStorageKey(threadId)) || '[]');
    for (const row of rows.slice(-20)) {
      const msg = messageEl(row.role, '', { label: row.label, skipScroll: true });
      msg.bubble.innerHTML = row.html;
    }
  } catch {}
}

function stopPolling() {
  pollGeneration += 1;
  if (pollTimer) clearInterval(pollTimer);
  pollTimer = null;
  stopRunDurationTimer();
  activeWatch = null;
  pollAttempts = 0;
  updateComposerAction();
  setWorkingDot(false);
  setTopStatus('已连接');
}

function detachForegroundRunForNewThread() {
  pollGeneration += 1;
  if (pollTimer) clearInterval(pollTimer);
  pollTimer = null;
  stopRunDurationTimer();
  activeWatch = null;
  pollAttempts = 0;
  activeAssistant = null;
  lastPreview = '';
  updateComposerAction();
  setTopStatus('已连接');
}

function adoptNewThreadId(threadId) {
  if (!threadId || (selectedThreadId && selectedThreadId === threadId)) return;
  const pendingDraftKey = pendingNewThread ? composerDraftKey() : '';
  selectedThreadId = threadId;
  pendingNewThread = null;
  syncedThreadId = threadId;
  if (pendingDraftKey) migrateComposerDraft(pendingDraftKey, threadId);
  if (activeWatch) activeWatch.threadId = threadId;
  localStorage.setItem('codexGo.selectedThread', threadId);
  setThreadCompleteNotice(threadId, false);
  renderReasoningBadge(bestReasoningMode(null, threadId));
  renderModelBadge(bestModelInfo(null, threadId));
  updateThreadTitle();
  scheduleQueuedSendRefresh(250, { force: true });
  loadThreads({ detectTransitions: false, renderMenu: 'ifChanged' }).catch(error => {
    console.warn('Codex Go new thread list refresh skipped:', error);
  });
}

async function pollStatus(watch, generation = pollGeneration) {
  if (generation !== pollGeneration) return;
  if (!watch || !activeAssistant) return stopPolling();
  pollAttempts += 1;
  const params = new URLSearchParams({ token, since: watch.since || '', thread: watch.threadId || selectedThreadId || '' });
  if (watch.sessionFile) params.set('session', watch.sessionFile);
  if (watch.expectNewThread) params.set('expectNewThread', '1');
  if (watch.excludeThreadId) params.set('excludeThread', watch.excludeThreadId);
  if (watch.cwd) params.set('cwd', watch.cwd);
  try {
    const res = await fetchApi(`/codex/status?${params}`, { cache: 'no-store' });
    const data = await res.json();
    if (generation !== pollGeneration || !activeAssistant) return;
    if (!data.ok) throw new Error(data.message || '读取失败');
    if (!data.available && data.status === 'missing') throw new Error(data.message || '没有找到所选线程。');
    if (data.available) {
      if (data.threadId && (!selectedThreadId || pendingNewThread)) adoptNewThreadId(data.threadId);
      updateContextFromStatus(data);
      applyThreadRuntimeState(data.threadId || watch.threadId || selectedThreadId, runtimeSnapshotFromStatusData(data), { detectTransitions: true });
      renderThreadMenuIfVisualChanged();
      lastStatusSignature = codexStatusSignature(data);
      scheduleQueuedSendRefresh(0, { force: true });
    }
    setActiveRunStart(data.startedAt || watch.since || '', Date.now() - (Number(data.durationMs) || 0));
    const activeCommandUi = commandUi(activeAssistant.commandKind || '');
    if (data.status === 'complete' || data.status === 'error') {
      const isErrorStatus = data.status === 'error';
      const finalText = isErrorStatus
        ? (data.error || data.preview || 'Codex 回复失败。')
        : (activeCommandUi?.completeText || data.final || data.preview || '已完成。');
      if (finalText !== lastPreview) {
        lastPreview = finalText;
        setMarkdown(activeAssistant.bubble, finalText);
        scrollBottom();
      }
      updatePermissionActions(activeAssistant, null, data);
      const finalDurationText = formatDuration(finalRunDurationMs(data));
      activeAssistant.runDurationText = finalDurationText;
      setMetaLabel(activeAssistant.meta, isErrorStatus
        ? `Codex · 失败 ${finalDurationText}`
        : activeCommandUi ? activeCommandUi.completeLabel(finalDurationText) : `Codex · 已处理 ${finalDurationText}`);
      activeAssistant.article.classList.remove('pending');
      addDetails(activeAssistant, data.steps || []);
      serializeMessagesIfStillOnThread(watch.threadId || selectedThreadId);
      scheduleQueuedSendRefresh(150, { force: true });
      activeAssistant = null;
      stopPolling();
    } else {
      const processText = activeCommandUi?.pendingText || stepMarkdown(data.steps || []);
      if (processText !== lastPreview) {
        lastPreview = processText;
        if (activeCommandUi) setMarkdown(activeAssistant.bubble, processText);
        else renderProcessSteps(activeAssistant.bubble, data.steps || []);
        updatePermissionActions(activeAssistant, data.permissionRequest || null, data);
        scrollBottom();
      }
      if (data.status === 'permission_required') updatePermissionActions(activeAssistant, data.permissionRequest || null, data);
      if (data.status === 'permission_required') setTopStatus('等待权限');
      else if (!data.active) setTopStatus('等待 Codex');
      if (pollAttempts > 180) {
        activeAssistant.article.classList.remove('pending');
        if (activeCommandUi) setMarkdown(activeAssistant.bubble, activeCommandUi.completeText);
        addDetails(activeAssistant, data.steps || []);
        const finalDurationText = formatDuration(finalRunDurationMs(data));
        activeAssistant.runDurationText = finalDurationText;
        setMetaLabel(activeAssistant.meta, activeCommandUi ? activeCommandUi.completeLabel(finalDurationText) : `Codex · 已处理 ${finalDurationText}`);
        scheduleQueuedSendRefresh(150, { force: true });
        activeAssistant = null;
        stopPolling();
      }
    }
  } catch (error) {
    setNotice(error.message || '读取 Codex 回复失败', 'error');
  }
}

function startPolling(watch) {
  stopPolling();
  if (!activeAssistant) return;
  const generation = ++pollGeneration;
  activeWatch = watch || null;
  setWorkingDot(true);
  lastPreview = '';
  setActiveRunStart(watch?.since || '', Date.now());
  setTopStatus(commandUi(activeAssistant.commandKind || '') ? '正在压缩' : '等待 Codex');
  updateActiveRunDuration(true);
  startRunDurationTimer();
  pollStatus(watch, generation);
  if (activeAssistant && generation === pollGeneration) {
    pollTimer = setInterval(() => pollStatus(watch, generation), 1400);
    updateComposerAction();
  }
}

async function refreshCurrentThreadIfChanged() {
  if (!selectedThreadId || activeAssistant || autoRefreshBusy || document.hidden) return;
  autoRefreshBusy = true;
  let dotStarted = false;
  const threadId = selectedThreadId;
  try {
    const params = new URLSearchParams({ token, thread: threadId });
    const response = await fetchApi(`/codex/status?${params}`, { cache: 'no-store' });
    const data = await response.json();
    if (threadId !== selectedThreadId || !response.ok || !data.ok || !data.available) return;
    updateContextFromStatus(data);
    applyThreadRuntimeState(threadId, runtimeSnapshotFromStatusData(data), { detectTransitions: false });
    renderThreadMenuIfVisualChanged();
    if (isRunningStatus(data) && isLocalStopSuppressed(threadId, data.startedAt)) {
      lastStatusSignature = codexStatusSignature(data);
      return;
    }
    const signature = codexStatusSignature(data);
    const shouldReload = isRunningStatus(data) || (lastStatusSignature && signature && signature !== lastStatusSignature);
    if (!lastStatusSignature) lastStatusSignature = signature;
    if (!shouldReload) return;
    lastStatusSignature = signature;
    setWorkingDot(true);
    dotStarted = true;
    setNotice(isRunningStatus(data) ? '检测到桌面端正在回复，正在同步到手机…' : '检测到桌面端聊天记录更新，正在同步…', 'ok');
    await loadThreadHistory(threadId);
  } catch (error) {
    console.warn('Codex Go auto refresh skipped:', error);
  } finally {
    autoRefreshBusy = false;
    if (dotStarted && !activeAssistant && !pollTimer) setWorkingDot(false);
  }
}

function startAutoRefresh() {
  if (autoRefreshTimer) clearInterval(autoRefreshTimer);
  autoRefreshTimer = setInterval(refreshCurrentThreadIfChanged, 5000);
}

function startGuiStateWatcher() {
  if (guiStateTimer) clearInterval(guiStateTimer);
  refreshGuiState({ force: true });
  guiStateTimer = setInterval(refreshGuiState, 2200);
}

async function refreshThreadRuntimeStates(options = {}) {
  if (threadStateBusy || document.hidden) return;
  threadStateBusy = true;
  try {
    await loadThreads({ detectTransitions: options.detectTransitions !== false, renderMenu: 'ifChanged' });
  } catch (error) {
    console.warn('Codex Go thread state refresh skipped:', error);
  } finally {
    threadStateBusy = false;
  }
}

function scheduleForegroundStateRefresh() {
  if (document.hidden) return;
  pruneCompletedThreadNotices();
  if (appResumeRefreshTimer) window.clearTimeout(appResumeRefreshTimer);
  appResumeRefreshTimer = window.setTimeout(() => {
    appResumeRefreshTimer = null;
    refreshApiConfigIfNeeded();
    refreshGuiState({ force: true });
    refreshCurrentThreadIfChanged();
    refreshThreadRuntimeStates({ detectTransitions: true });
  }, 80);
}

function closeReasoningMenu() {
  reasoningMenuCard.classList.remove('is-open');
  reasoningMenuCard.style.left = '';
  reasoningMenuCard.style.top = '';
}

function positionReasoningMenu(anchorElement = reasoningBadge) {
  if (!anchorElement || typeof anchorElement.getBoundingClientRect !== 'function') return;
  const anchor = anchorElement.getBoundingClientRect();
  const viewportWidth = window.innerWidth || document.documentElement.clientWidth || 0;
  const viewportHeight = window.innerHeight || document.documentElement.clientHeight || 0;
  const margin = 10;
  const cardWidth = reasoningMenuCard.offsetWidth || 97;
  const cardHeight = reasoningMenuCard.offsetHeight || 90;
  const rightAlignedLeft = anchor.right - cardWidth;
  const left = Math.max(margin, Math.min(viewportWidth - cardWidth - margin, rightAlignedLeft));
  const belowTop = anchor.bottom + 7;
  const aboveTop = anchor.top - cardHeight - 7;
  const top = belowTop + cardHeight + margin <= viewportHeight ? belowTop : Math.max(margin, aboveTop);
  reasoningMenuCard.style.left = `${Math.round(left)}px`;
  reasoningMenuCard.style.top = `${Math.round(top)}px`;
}

function openReasoningMenu(options = {}) {
  threadMenu.classList.remove('is-open');
  closeThreadActionCard();
  closeContextQuickCard();
  closeSettingsCard();
  closeModelMenu();
  renderReasoningMenu();
  reasoningMenuCard.classList.add('is-open');
  positionReasoningMenu(reasoningBadge);
  if (options.vibrate) vibrateForLongPress();
}

function cancelReasoningLongPress() {
  window.clearTimeout(reasoningLongPressTimer);
  reasoningLongPressTimer = null;
  reasoningLongPressStart = null;
}

function startReasoningLongPress(event) {
  if (event.button > 0 || switchingReasoningMode) return;
  reasoningLongPressStart = { x: event.clientX || 0, y: event.clientY || 0 };
  reasoningLongPressOpened = false;
  window.clearTimeout(reasoningLongPressTimer);
  reasoningLongPressTimer = window.setTimeout(() => {
    reasoningLongPressOpened = true;
    suppressReasoningClickUntil = Date.now() + 900;
    clearNativeSelection();
    openReasoningMenu({ vibrate: true });
  }, 560);
}

function moveReasoningLongPress(event) {
  if (!reasoningLongPressStart) return;
  const dx = Math.abs((event.clientX || 0) - reasoningLongPressStart.x);
  const dy = Math.abs((event.clientY || 0) - reasoningLongPressStart.y);
  if (dx > 10 || dy > 10) cancelReasoningLongPress();
}

function finishReasoningPress(event) {
  const opened = reasoningLongPressOpened;
  cancelReasoningLongPress();
  if (opened) {
    if (event.cancelable) event.preventDefault();
    event.stopPropagation();
  }
}

function closeModelMenu() {
  modelMenuCard.classList.remove('is-open');
  modelMenuCard.style.left = '';
  modelMenuCard.style.top = '';
}

function positionModelMenu(anchorElement = modelBadge) {
  if (!anchorElement || typeof anchorElement.getBoundingClientRect !== 'function') return;
  const anchor = anchorElement.getBoundingClientRect();
  const viewportWidth = window.innerWidth || document.documentElement.clientWidth || 0;
  const viewportHeight = window.innerHeight || document.documentElement.clientHeight || 0;
  const margin = 10;
  const cardWidth = modelMenuCard.offsetWidth || 182;
  const cardHeight = modelMenuCard.offsetHeight || 160;
  const rightAlignedLeft = anchor.right - cardWidth;
  const left = Math.max(margin, Math.min(viewportWidth - cardWidth - margin, rightAlignedLeft));
  const belowTop = anchor.bottom + 7;
  const aboveTop = anchor.top - cardHeight - 7;
  const top = belowTop + cardHeight + margin <= viewportHeight ? belowTop : Math.max(margin, aboveTop);
  modelMenuCard.style.left = `${Math.round(left)}px`;
  modelMenuCard.style.top = `${Math.round(top)}px`;
}

let liveModelOptionsRefreshBusy = false;

async function refreshLiveModelMenuOptions() {
  if (liveModelOptionsRefreshBusy) return;
  liveModelOptionsRefreshBusy = true;
  try {
    const params = new URLSearchParams({ token });
    const response = await fetchApi(`/codex/model-options?${params}`, {
      cache: 'no-store',
      apiTimeoutMs: 12000,
      routeSwitchQuiet: true,
    });
    const data = await response.json();
    if (!response.ok || !data.ok || !Array.isArray(data.modelOptions) || !data.modelOptions.length) return;
    modelMenuOptions = data.modelOptions
      .filter(item => item && item.id)
      .map(item => ({
        key: String(item.key || item.id),
        id: String(item.id),
        label: String(item.label || item.displayName || item.id),
        displayName: String(item.displayName || item.label || item.id),
      }));
    renderModelBadge(currentModelInfo);
    if (modelMenuCard.classList.contains('is-open')) renderModelMenu();
  } catch (error) {
    console.warn('Codex Go live model options skipped:', error);
  } finally {
    liveModelOptionsRefreshBusy = false;
  }
}

function openModelMenu(options = {}) {
  threadMenu.classList.remove('is-open');
  closeThreadActionCard();
  closeContextQuickCard();
  closeSettingsCard();
  closeReasoningMenu();
  renderModelMenu();
  modelMenuCard.classList.add('is-open');
  positionModelMenu(modelBadge);
  if (!options.skipLiveRefresh) refreshLiveModelMenuOptions();
  if (options.vibrate) vibrateForLongPress();
}

function cancelModelLongPress() {
  window.clearTimeout(modelLongPressTimer);
  modelLongPressTimer = null;
  modelLongPressStart = null;
}

function startModelLongPress(event) {
  if (event.button > 0 || switchingModel) return;
  modelLongPressStart = { x: event.clientX || 0, y: event.clientY || 0 };
  modelLongPressOpened = false;
  window.clearTimeout(modelLongPressTimer);
  modelLongPressTimer = window.setTimeout(() => {
    modelLongPressOpened = true;
    suppressModelClickUntil = Date.now() + 900;
    clearNativeSelection();
    openModelMenu({ vibrate: true });
  }, 560);
}

function moveModelLongPress(event) {
  if (!modelLongPressStart) return;
  const dx = Math.abs((event.clientX || 0) - modelLongPressStart.x);
  const dy = Math.abs((event.clientY || 0) - modelLongPressStart.y);
  if (dx > 10 || dy > 10) cancelModelLongPress();
}

function finishModelPress(event) {
  const opened = modelLongPressOpened;
  cancelModelLongPress();
  if (opened) {
    if (event.cancelable) event.preventDefault();
    event.stopPropagation();
  }
}

function closeContextQuickCard() {
  contextQuickCard.classList.remove('is-open');
  contextQuickCard.style.left = '';
  contextQuickCard.style.top = '';
}

function positionContextQuickCard(anchorElement = topStatus) {
  if (!anchorElement || typeof anchorElement.getBoundingClientRect !== 'function') return;
  const anchor = anchorElement.getBoundingClientRect();
  const viewportWidth = window.innerWidth || document.documentElement.clientWidth || 0;
  const viewportHeight = window.innerHeight || document.documentElement.clientHeight || 0;
  const margin = 10;
  const cardWidth = contextQuickCard.offsetWidth || 112;
  const cardHeight = contextQuickCard.offsetHeight || 54;
  const rightAlignedLeft = anchor.right - cardWidth;
  const left = Math.max(margin, Math.min(viewportWidth - cardWidth - margin, rightAlignedLeft));
  const belowTop = anchor.bottom + 7;
  const aboveTop = anchor.top - cardHeight - 7;
  const top = belowTop + cardHeight + margin <= viewportHeight ? belowTop : Math.max(margin, aboveTop);
  contextQuickCard.style.left = `${Math.round(left)}px`;
  contextQuickCard.style.top = `${Math.round(top)}px`;
}

function openContextQuickCard() {
  threadMenu.classList.remove('is-open');
  closeThreadActionCard();
  closeSettingsCard();
  closeReasoningMenu();
  closeModelMenu();
  contextQuickCard.classList.add('is-open');
  positionContextQuickCard(topStatus);
}

function toggleContextQuickCard() {
  if (contextQuickCard.classList.contains('is-open')) closeContextQuickCard();
  else openContextQuickCard();
}

async function sendContextCompactCommand() {
  closeContextQuickCard();
  await sendText({
    text: CONTEXT_COMPACT_COMMAND,
    commandKind: 'compact',
    userLabel: '你 · 压缩',
    sendingNotice: '正在发送压缩指令…',
    sentNotice: '已发送压缩指令',
  });
}

function startThreadStateWatcher() {
  if (threadStateTimer) clearInterval(threadStateTimer);
  threadStateTimer = setInterval(refreshThreadRuntimeStates, 4500);
}

function startQueuedSendMirrorWatcher() {
  const tick = () => {
    const shouldPoll = Boolean(selectedThreadId && !isPendingNewThreadView() && !document.hidden);
    if (shouldPoll) refreshQueuedSends().catch(error => console.warn('Codex Go queued sends mirror skipped:', error));
    const delay = activeAssistant || pollTimer ? 3000 : queuedSends.length ? 5000 : 20000;
    queuedSendMirrorTimer = window.setTimeout(tick, delay);
  };
  if (queuedSendMirrorTimer) window.clearTimeout(queuedSendMirrorTimer);
  queuedSendMirrorTimer = window.setTimeout(tick, 1200);
}


function autosize() {
  const maxHeight = 150;
  textarea.style.height = 'auto';
  const scrollHeight = textarea.scrollHeight;
  const nextHeight = Math.min(scrollHeight, maxHeight);
  textarea.style.height = `${nextHeight}px`;
  textarea.style.overflowY = scrollHeight > maxHeight ? 'auto' : 'hidden';
  updateComposerViewportPlacement();
}

function updateComposerAction() {
  const running = Boolean(activeAssistant || pollTimer);
  sendButton.hidden = running;
  sendButton.classList.toggle('composer-action-hidden', running);
  stopButton.hidden = !running;
  stopButton.classList.toggle('composer-action-hidden', !running);
  composer.classList.toggle('is-running', running);
  updateTitleDotState();
}

function isComposerImeEnter(event) {
  if (!event) return false;
  if (composerImeActive || event.isComposing) return true;
  if (event.key === 'Process' || event.keyCode === 229 || event.which === 229) return true;
  return event.key === 'Enter' && Date.now() - composerImeEndedAt < 250;
}

async function sendText(options = {}) {
  const hasTextOverride = typeof options.text === 'string';
  if (!hasTextOverride && options.userInitiated !== true) return;
  const sendThreadId = selectedThreadId;
  const isPendingNewThreadFirstSend = isPendingNewThreadView();
  const queueBehindActiveRun = Boolean((activeAssistant || pollTimer) && !isPendingNewThreadFirstSend);
  if (isPendingNewThreadFirstSend && (activeAssistant || pollTimer)) detachForegroundRunForNewThread();
  const text = hasTextOverride ? options.text : textarea.value;
  const attachmentsToSend = hasTextOverride ? [] : [...pendingAttachments];
  let composerClearedForSend = false;
  if (!text.trim() && !attachmentsToSend.length) return;
  const commandKind = options.commandKind || commandKindForText(text);
  const textCommandUi = commandUi(commandKind);
  clearLocalStopSuppression(selectedThreadId);

  sendButton.disabled = true;
  setWorkingDot(true);
  setNotice(
    options.sendingNotice
      || (isPendingNewThreadFirstSend ? '正在创建新线程并发送…' : queueBehindActiveRun ? '正在发送到 Codex 队列…' : '正在发送到 Codex…'),
    'ok',
  );
  try {
    await ensureRouteForSend();
    if (!isPendingNewThreadFirstSend) {
      await syncCodexThread(selectedThreadId, { quiet: true, force: true });
    }
  } catch (error) {
    setNotice(error.message || '同步 Codex 线程失败，已取消发送', 'error');
    sendButton.disabled = false;
    setWorkingDot(false);
    if (hasTextOverride) restoreLayoutAfterKeyboard();
    else textarea.focus({ preventScroll: true });
    return;
  }

  if (!queueBehindActiveRun) {
    const user = messageEl('user', text || (attachmentsToSend.length ? ' ' : ''), { label: options.userLabel || textCommandUi?.userLabel || (attachmentsToSend.length ? `你 · ${attachmentSummary(attachmentsToSend)}` : '你') });
    appendImagesToBubble(user, attachmentsToSend);
  }
  const queuedAssistant = queueBehindActiveRun
    ? null
    : messageEl('assistant', textCommandUi?.pendingText || '已发送，等待 Codex 回复…', { label: textCommandUi ? textCommandUi.runningLabel('0s') : 'Codex · 运行 0s', pending: true });
  if (!queueBehindActiveRun) {
    activeAssistant = queuedAssistant;
    activeAssistant.commandKind = commandKind;
    setActiveRunStart('', Date.now());
  }
  if (selectedThreadId && !queueBehindActiveRun) {
    applyThreadRuntimeState(selectedThreadId, {
      status: 'waiting',
      active: true,
      startedAt: new Date().toISOString(),
      completedAt: '',
      updatedAt: new Date().toISOString(),
      turnId: '',
    }, { detectTransitions: false });
  }
  renderThreadMenu();
  updateComposerAction();
  if (!hasTextOverride) {
    textarea.value = '';
    pendingAttachments = [];
    composerClearedForSend = true;
    clearComposerDraft();
    renderAttachmentTray();
    autosize();
  }
  try {
    const clientRequestId = `send-${Date.now()}-${Math.random().toString(36).slice(2)}`;
    const res = await fetchApi('/send', {
      method: 'POST',
      headers: { 'content-type': 'application/json', 'x-codex-go-token': token },
      body: JSON.stringify({
        clientRequestId,
        text,
        target,
        threadId: selectedThreadId,
        previousThreadId: pendingNewThread?.previousThreadId || '',
        expectedCwd: pendingNewThread?.cwd || pendingNewThread?.projectPath || '',
        newThreadScope: pendingNewThread?.scope || '',
        projectPath: pendingNewThread?.projectPath || '',
        isProjectThread: pendingNewThread?.isProjectThread ?? null,
        expectNewThread: isPendingNewThreadFirstSend,
        attachments: attachmentsToSend.map(({ name, type, dataUrl }) => ({ name, type, dataUrl })),
      }),
      apiTimeoutMs: 60000,
      routeSwitchQuiet: true,
      retryProbeTimeoutMs: 900,
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok || !data.ok) throw new Error(data.message || '发送失败');
    setNotice(options.sentNotice || (queueBehindActiveRun ? '已发送，Codex 会排在当前回复后继续处理' : '已发送'), 'ok');
    serializeMessagesIfStillOnThread(sendThreadId);
    if (queueBehindActiveRun) scheduleQueuedSendRefresh(250, { force: true, showBusy: true, showError: true });
    if (!queueBehindActiveRun) startPolling(data.watch || { since: new Date().toISOString() });
  } catch (error) {
    if (composerClearedForSend) {
      textarea.value = text;
      pendingAttachments = attachmentsToSend;
      composerClearedForSend = false;
      renderAttachmentTray();
      autosize();
    }
    if (queueBehindActiveRun) {
      messageEl('assistant', error.message || '发送失败', { label: 'Codex Go' });
    } else if (activeAssistant) {
      activeAssistant.article.classList.remove('pending');
      setMarkdown(activeAssistant.bubble, error.message || '发送失败');
      activeAssistant = null;
      stopPolling();
    }
    setNotice(error.message || '发送失败', 'error');
  } finally {
    sendButton.disabled = false;
    if (!activeAssistant && !pollTimer) setWorkingDot(false);
    if (hasTextOverride) restoreLayoutAfterKeyboard();
    else textarea.focus({ preventScroll: true });
  }
}

async function stopCodexResponse() {
  if (stopButton.disabled) return;
  const shouldRestoreTextareaFocus = document.activeElement === textarea;
  const stopThreadId = activeWatch?.threadId || selectedThreadId || '';
  stopButton.disabled = true;
  setWorkingDot(true);
  setNotice('正在切到当前 Codex 线程并发送终止指令…', 'ok');
  try {
    const stopThreadId = activeWatch?.threadId || selectedThreadId || '';
    const response = await fetchApi('/codex/stop', {
      method: 'POST',
      headers: { 'content-type': 'application/json', 'x-codex-go-token': token },
      body: JSON.stringify({ threadId: stopThreadId }),
      apiTimeoutMs: 15000,
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok || !data.ok) throw new Error(data.message || '终止失败');
    markThreadLocallyStopped(stopThreadId);
    applyThreadRuntimeState(stopThreadId, {
      status: 'idle',
      active: false,
      startedAt: '',
      completedAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
      turnId: '',
    }, { detectTransitions: false });
    renderThreadMenuIfVisualChanged();
    if (activeAssistant) {
      const preservedSteps = captureVisibleProcessSteps(activeAssistant);
      activeAssistant.article.classList.remove('pending');
      activeAssistant.meta.textContent = 'Codex · 已取消';
      setMarkdown(activeAssistant.bubble, '已取消当前回复。');
      activeAssistant.article.querySelector('details.process')?.remove();
      addDetails(activeAssistant, preservedSteps);
      activeAssistant = null;
    }
    stopPolling();
    serializeMessagesIfStillOnThread(stopThreadId);
    setNotice('已发送终止指令', 'ok');
  } catch (error) {
    setNotice(error.message || '终止失败', 'error');
  } finally {
    stopButton.disabled = false;
    if (!activeAssistant && !pollTimer) setWorkingDot(false);
    if (shouldRestoreTextareaFocus) textarea.focus({ preventScroll: true });
    else restoreLayoutAfterKeyboard();
  }
}

composer.addEventListener('submit', event => { event.preventDefault(); });
textarea.addEventListener('compositionstart', () => {
  composerImeActive = true;
});
textarea.addEventListener('compositionend', () => {
  composerImeActive = false;
  composerImeEndedAt = Date.now();
  autosize();
});
textarea.addEventListener('input', event => {
  if (event.isComposing) composerImeActive = true;
  autosize();
  scheduleComposerDraftSave();
});
textarea.addEventListener('touchstart', prepareTextareaFocus, { passive: false });
composer.addEventListener('touchstart', prepareComposerFocus, { passive: false });
textarea.addEventListener('pointerdown', event => {
  if (event.pointerType === 'touch') prepareTextareaFocus(event);
});
composer.addEventListener('pointerdown', event => {
  if (event.pointerType === 'touch') prepareComposerFocus(event);
});
document.addEventListener('touchstart', noteOutsideComposerTouch, { passive: true, capture: true });
document.addEventListener('pointerdown', event => {
  if (event.pointerType === 'touch') noteOutsideComposerTouch(event);
}, { capture: true });
textarea.addEventListener('keydown', event => {
  if (event.key === 'Enter' && !event.shiftKey) {
    if (isComposerImeEnter(event)) {
      if (!composerImeActive && !event.isComposing && event.cancelable) event.preventDefault();
      return;
    }
    event.preventDefault();
    if (event.isTrusted !== false) sendText({ userInitiated: true });
  }
});
textarea.addEventListener('focus', beginKeyboardAlignment);
textarea.addEventListener('click', scheduleKeyboardAlignment);
textarea.addEventListener('touchend', scheduleKeyboardAlignment, { passive: true });
textarea.addEventListener('blur', () => {
  saveComposerDraftForKey();
  restoreLayoutAfterKeyboard();
});
window.addEventListener('scroll', keepLayoutViewportPinned, { passive: true });
function handleWindowResize() {
  syncMobileKeyboardModeClass();
  alignComposerForKeyboard();
  positionThreadMenuCard();
  positionSettingsCard();
  if (Date.now() < threadStickToBottomUntil && !document.body.classList.contains('keyboard-open')) {
    scrollThreadToBottom(true);
  }
}
window.addEventListener('resize', handleWindowResize);
window.addEventListener('orientationchange', () => window.setTimeout(() => {
  if (usesComposerKeyboardOverlay()) scheduleKeyboardAlignment();
  handleWindowResize();
}, 250));
if (window.visualViewport) {
  window.visualViewport.addEventListener('resize', handleWindowResize);
  window.visualViewport.addEventListener('scroll', () => {
    if (usesComposerKeyboardOverlay()) alignComposerForKeyboard();
    else keepLayoutViewportPinned();
  });
}
if (navigator.virtualKeyboard) {
  navigator.virtualKeyboard.addEventListener('geometrychange', () => {
    if (!usesComposerKeyboardOverlay()) return;
    const rect = navigator.virtualKeyboard.boundingRect;
    virtualKeyboardInset = Math.max(0, Math.round(rect?.height || 0));
    alignComposerForKeyboard();
  });
}
newThreadButton.addEventListener('click', createNewThreadInCurrentProject);
settingsButton.addEventListener('click', event => {
  event.preventDefault();
  event.stopPropagation();
  toggleSettingsCard();
});
themeSelect?.addEventListener('change', event => {
  setAppearanceTheme(event.target.value || 'native');
});

let stopPointerTriggeredAt = 0;
let sendPointerTriggeredAt = 0;
function keepKeyboardForStopButton(event) {
  if (event.cancelable) event.preventDefault();
  event.stopPropagation();
}

function keepKeyboardForSendButton(event) {
  if (event.cancelable) event.preventDefault();
  event.stopPropagation();
}

function triggerStopButtonAction(event) {
  keepKeyboardForStopButton(event);
  stopPointerTriggeredAt = Date.now();
  stopCodexResponse();
}

function triggerSendButtonAction(event) {
  keepKeyboardForSendButton(event);
  if (sendButton.disabled || sendButton.hidden) return;
  sendPointerTriggeredAt = Date.now();
  if (event.isTrusted !== false) sendText({ userInitiated: true });
}

stopButton.addEventListener('pointerdown', keepKeyboardForStopButton, { passive: false });
stopButton.addEventListener('pointerup', triggerStopButtonAction, { passive: false });
stopButton.addEventListener('touchstart', keepKeyboardForStopButton, { passive: false });
stopButton.addEventListener('touchend', event => {
  if (window.PointerEvent) {
    keepKeyboardForStopButton(event);
    return;
  }
  triggerStopButtonAction(event);
}, { passive: false });
stopButton.addEventListener('click', event => {
  event.preventDefault();
  event.stopPropagation();
  if (Date.now() - stopPointerTriggeredAt < 700) return;
  stopCodexResponse();
});
sendButton.addEventListener('pointerdown', keepKeyboardForSendButton, { passive: false });
sendButton.addEventListener('pointerup', triggerSendButtonAction, { passive: false });
sendButton.addEventListener('touchstart', keepKeyboardForSendButton, { passive: false });
sendButton.addEventListener('touchend', event => {
  if (window.PointerEvent) {
    keepKeyboardForSendButton(event);
    return;
  }
  triggerSendButtonAction(event);
}, { passive: false });
sendButton.addEventListener('click', event => {
  event.preventDefault();
  event.stopPropagation();
  if (Date.now() - sendPointerTriggeredAt < 700) return;
  if (sendButton.disabled || sendButton.hidden) return;
  if (event.isTrusted !== false) sendText({ userInitiated: true });
});
attachButton.addEventListener('click', () => {
  fileInput.click();
});
fileInput.addEventListener('change', async () => {
  const files = [...fileInput.files || []];
  try {
    for (const file of files) {
      const dataUrl = await fileToDataUrl(file);
      pendingAttachments.push({ name: file.name || 'attachment', type: file.type || 'application/octet-stream', dataUrl });
    }
    if (files.length) {
      renderAttachmentTray();
      scheduleComposerDraftSave();
      setNotice(`已添加 ${attachmentSummary(pendingAttachments)}，点击发送后会和文字一起发给 Codex`, 'ok');
    }
  } catch (error) {
    setNotice(error.message || '读取附件失败', 'error');
  }
  fileInput.value = '';
  textarea.focus({ preventScroll: true });
});

function keepActionTap(event) {
  if (event.cancelable) event.preventDefault();
  event.stopPropagation();
}

function wireInstantActionButton(button, handler) {
  let pointerTriggeredAt = 0;
  const trigger = event => {
    keepActionTap(event);
    pointerTriggeredAt = Date.now();
    handler();
  };
  button.addEventListener('pointerdown', keepActionTap, { passive: false });
  button.addEventListener('pointerup', trigger, { passive: false });
  button.addEventListener('touchstart', keepActionTap, { passive: false });
  button.addEventListener('touchend', event => {
    if (window.PointerEvent) {
      keepActionTap(event);
      return;
    }
    trigger(event);
  }, { passive: false });
  button.addEventListener('click', event => {
    event.preventDefault();
    event.stopPropagation();
    if (Date.now() - pointerTriggeredAt < 700) return;
    handler();
  });
}

wireInstantActionButton(threadActionArchive, archiveCurrentThread);
wireInstantActionButton(threadActionRename, showRenamePanel);
wireInstantActionButton(threadActionPinToggle, toggleCurrentThreadPin);
wireInstantActionButton(threadRenameCancel, cancelThreadRename);
wireInstantActionButton(threadRenameSave, renameCurrentThread);
wireInstantActionButton(contextQuickCompact, sendContextCompactCommand);
wireInstantActionButton(settingSuperModeSwitch, toggleSuperMode);
let renameKeyboardSubmitAt = 0;
function submitRenameFromKeyboard(event) {
  if (event.cancelable) event.preventDefault();
  event.stopPropagation();
  if (Date.now() - renameKeyboardSubmitAt < 700) return;
  renameKeyboardSubmitAt = Date.now();
  renameCurrentThread();
}
threadRenameInput.addEventListener('beforeinput', event => {
  if (event.inputType === 'insertLineBreak') submitRenameFromKeyboard(event);
});
threadRenameInput.addEventListener('keydown', event => {
  if (event.key === 'Enter' || event.key === 'Return') {
    submitRenameFromKeyboard(event);
  } else if (event.key === 'Escape') {
    event.preventDefault();
    event.stopPropagation();
    cancelThreadRename();
  }
});
threadRenameInput.addEventListener('keyup', event => {
  if (event.key === 'Enter' || event.key === 'Return') {
    submitRenameFromKeyboard(event);
  } else if (event.key === 'Escape') {
    event.preventDefault();
    event.stopPropagation();
    cancelThreadRename();
  }
});
threadActionCard.addEventListener('pointerdown', event => event.stopPropagation());
threadActionCard.addEventListener('touchstart', event => event.stopPropagation(), { passive: true });
threadActionCard.addEventListener('click', event => event.stopPropagation());
settingsCard.addEventListener('pointerdown', event => event.stopPropagation());
settingsCard.addEventListener('touchstart', event => event.stopPropagation(), { passive: true });
settingsCard.addEventListener('click', event => event.stopPropagation());

function cancelThreadLongPress() {
  window.clearTimeout(threadLongPressTimer);
  threadLongPressTimer = null;
  threadLongPressStart = null;
}

function clearNativeSelection() {
  try {
    const selection = window.getSelection && window.getSelection();
    if (selection && !selection.isCollapsed) selection.removeAllRanges();
  } catch {}
  try {
    if (document.activeElement && document.activeElement !== textarea && document.activeElement !== threadRenameInput) {
      document.activeElement.blur();
    }
  } catch {}
}

function threadMenuEdgeGap() {
  const styles = window.getComputedStyle(threadMenu);
  const cssGap = parseFloat(styles.getPropertyValue('--thread-menu-edge-gap'));
  if (Number.isFinite(cssGap) && cssGap > 0) return cssGap;
  const left = parseFloat(styles.left);
  return Number.isFinite(left) && left > 0 ? left : 12;
}

function isThreadRailLayout() {
  return window.matchMedia('(min-width: 900px) and (min-height: 650px)').matches;
}

function positionThreadMenuCard() {
  if (!threadMenu) return;
  threadMenu.style.top = '';
  threadMenu.style.maxHeight = '';
  if (threadMenuScrim) {
    threadMenuScrim.style.top = '';
    threadMenuScrim.style.bottom = '';
    threadMenuScrim.style.left = '';
    threadMenuScrim.style.right = '';
  }
}

function toggleThreadMenuFromTitle() {
  if (isThreadRailLayout()) {
    loadThreads({ detectTransitions: true, renderMenu: 'ifChanged' }).catch(error => setNotice(error.message || '读取线程失败', 'error'));
    return;
  }
  closeReasoningMenu();
  closeModelMenu();
  closeSettingsCard();
  closeThreadActionCard();
  const willOpen = !threadMenu.classList.contains('is-open');
  threadMenu.classList.toggle('is-open');
  if (willOpen) positionThreadMenuCard();
  loadThreads({ detectTransitions: true, renderMenu: 'ifChanged' }).catch(error => setNotice(error.message || '读取线程失败', 'error'));
}

function startThreadLongPress(event) {
  if (!selectedThreadId || event.button > 0) return;
  if (event.cancelable) event.preventDefault();
  event.stopPropagation();
  threadLongPressStart = { x: event.clientX || 0, y: event.clientY || 0 };
  threadLongPressOpened = false;
  window.clearTimeout(threadLongPressTimer);
  threadLongPressTimer = window.setTimeout(() => {
    threadLongPressOpened = true;
    suppressThreadClickUntil = Date.now() + 900;
    clearNativeSelection();
    vibrateForLongPress();
  }, 560);
}

function moveThreadLongPress(event) {
  if (!threadLongPressStart) return;
  const dx = Math.abs((event.clientX || 0) - threadLongPressStart.x);
  const dy = Math.abs((event.clientY || 0) - threadLongPressStart.y);
  if (dx > 10 || dy > 10) cancelThreadLongPress();
}

function finishThreadPress(event) {
  if (event.button !== 0) return;
  const ready = threadLongPressOpened;
  const shouldOpenMenu = Boolean(threadLongPressStart && !ready && Date.now() >= suppressThreadClickUntil);
  cancelThreadLongPress();
  if (ready) {
    if (event.cancelable) event.preventDefault();
    event.stopPropagation();
    suppressThreadClickUntil = Date.now() + 900;
    openThreadActionCard(selectedThreadId);
    return;
  }
  if (!shouldOpenMenu) return;
  if (event.cancelable) event.preventDefault();
  event.stopPropagation();
  suppressThreadClickUntil = Date.now() + 500;
  toggleThreadMenuFromTitle();
}

threadButton.addEventListener('pointerdown', startThreadLongPress);
threadButton.addEventListener('pointermove', moveThreadLongPress);
threadButton.addEventListener('pointerup', finishThreadPress);
threadButton.addEventListener('pointercancel', cancelThreadLongPress);
threadButton.addEventListener('contextmenu', event => {
  event.preventDefault();
  cancelThreadLongPress();
  suppressThreadClickUntil = Date.now() + 900;
  clearNativeSelection();
  openThreadActionCard(selectedThreadId, { vibrate: true });
});
threadButton.addEventListener('click', event => {
  event.preventDefault();
  event.stopPropagation();
  if (Date.now() < suppressThreadClickUntil) return;
  toggleThreadMenuFromTitle();
});
if (threadMenuScrim) {
  threadMenuScrim.addEventListener('click', () => {
    threadMenu.classList.remove('is-open');
  });
}
reasoningMenuCard.addEventListener('pointerdown', event => event.stopPropagation());
reasoningMenuCard.addEventListener('touchstart', event => event.stopPropagation(), { passive: true });
reasoningMenuCard.addEventListener('click', event => event.stopPropagation());
modelMenuCard.addEventListener('pointerdown', event => event.stopPropagation());
modelMenuCard.addEventListener('touchstart', event => event.stopPropagation(), { passive: true });
modelMenuCard.addEventListener('click', event => event.stopPropagation());
document.addEventListener('click', event => {
  if (!threadMenu.contains(event.target) && !threadButton.contains(event.target) && !newThreadButton.contains(event.target) && !settingsButton.contains(event.target) && !reasoningBadge.contains(event.target) && !modelBadge.contains(event.target)) threadMenu.classList.remove('is-open');
  if (!threadActionCard.contains(event.target) && !threadButton.contains(event.target) && !settingsButton.contains(event.target) && !reasoningBadge.contains(event.target) && !modelBadge.contains(event.target)) closeThreadActionCard();
  if (!contextQuickCard.contains(event.target) && !topStatus.contains(event.target)) closeContextQuickCard();
  if (!settingsCard.contains(event.target) && !settingsButton.contains(event.target)) closeSettingsCard();
  if (!reasoningMenuCard.contains(event.target) && !reasoningBadge.contains(event.target)) closeReasoningMenu();
  if (!modelMenuCard.contains(event.target) && !modelBadge.contains(event.target)) closeModelMenu();
});
topStatus.addEventListener('click', event => {
  event.preventDefault();
  event.stopPropagation();
  toggleContextQuickCard();
});
reasoningBadge.addEventListener('pointerdown', startReasoningLongPress);
reasoningBadge.addEventListener('pointermove', moveReasoningLongPress);
reasoningBadge.addEventListener('pointerup', finishReasoningPress);
reasoningBadge.addEventListener('pointercancel', cancelReasoningLongPress);
reasoningBadge.addEventListener('contextmenu', event => {
  event.preventDefault();
  cancelReasoningLongPress();
  suppressReasoningClickUntil = Date.now() + 900;
  clearNativeSelection();
  openReasoningMenu({ vibrate: true });
});
reasoningBadge.addEventListener('click', event => {
  event.preventDefault();
  event.stopPropagation();
  if (Date.now() < suppressReasoningClickUntil) return;
  if (reasoningMenuCard.classList.contains('is-open')) closeReasoningMenu();
  else openReasoningMenu();
});
reasoningBadge.addEventListener('keydown', event => {
  if (event.key === 'Enter' || event.key === ' ') {
    event.preventDefault();
    openReasoningMenu();
  } else if (event.key === 'ArrowDown') {
    event.preventDefault();
    openReasoningMenu();
  }
});
modelBadge.addEventListener('pointerdown', startModelLongPress);
modelBadge.addEventListener('pointermove', moveModelLongPress);
modelBadge.addEventListener('pointerup', finishModelPress);
modelBadge.addEventListener('pointercancel', cancelModelLongPress);
modelBadge.addEventListener('contextmenu', event => {
  event.preventDefault();
  cancelModelLongPress();
  suppressModelClickUntil = Date.now() + 900;
  clearNativeSelection();
  openModelMenu({ vibrate: true });
});
modelBadge.addEventListener('click', event => {
  event.preventDefault();
  event.stopPropagation();
  if (Date.now() < suppressModelClickUntil) return;
  if (modelMenuCard.classList.contains('is-open')) closeModelMenu();
  else openModelMenu();
});
modelBadge.addEventListener('keydown', event => {
  if (event.key === 'Enter' || event.key === ' ') {
    event.preventDefault();
    if (modelMenuCard.classList.contains('is-open')) closeModelMenu();
    else openModelMenu();
  } else if (event.key === 'ArrowDown') {
    event.preventDefault();
    openModelMenu();
  }
});
document.addEventListener('visibilitychange', () => {
  if (!document.hidden) {
    scheduleForegroundStateRefresh();
    scheduleQueuedSendRefresh(0, { force: true });
  }
});
window.addEventListener('pageshow', () => {
  scheduleForegroundStateRefresh();
  scheduleQueuedSendRefresh(0, { force: true });
});
window.addEventListener('focus', () => {
  scheduleForegroundStateRefresh();
  scheduleQueuedSendRefresh(0, { force: true });
});

lockViewportZoom();
lockComposerDrag();
lockPageScrollToThread();
applyAppearanceSettings();
applySuperModeSettings();
alignTopActionsRight();
window.setTimeout(alignTopActionsRight, 120);
renderReasoningBadge(bestReasoningMode(null, selectedThreadId));
renderModelBadge(bestModelInfo(null, selectedThreadId));
loadApiConfig()
  .then(() => chooseApiCandidate({ preferLocal: true, quiet: true }))
  .then(() => loadThreads())
  .then(async () => {
    await loadThreadHistory(selectedThreadId);
    applyComposerDraft(composerDraftKey());
    scheduleThreadScrollToBottom([0, 120, 360, 900]);
    startAutoRefresh();
    startGuiStateWatcher();
    startThreadStateWatcher();
    startQueuedSendMirrorWatcher();
    scheduleQueuedSendRefresh(0, { force: true });
    startRouteMonitor();
  })
  .catch(error => setNotice(error.message || '读取线程失败', 'error'));
syncMobileKeyboardModeClass();
applyViewportSize();
autosize();
if (!window.matchMedia('(max-width: 700px), (pointer: coarse)').matches) {
  textarea.focus({ preventScroll: true });
}
