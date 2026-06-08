from __future__ import annotations

import json


def js_literal(value: object) -> str:
    return json.dumps("" if value is None else str(value))


def visible_helper_source() -> str:
    return """el => {
    const rect = el.getBoundingClientRect();
    const style = getComputedStyle(el);
    return rect.width > 0 && rect.height > 0 && style.display !== 'none' && style.visibility !== 'hidden';
  }"""


def dom_click_helper_source() -> str:
    return """el => {
    if (!el) return;
    const resetHorizontalLayoutScroll = () => {
      const candidates = [document.scrollingElement, document.documentElement, document.body, ...document.querySelectorAll('*')];
      for (const node of candidates) {
        try {
          if (!node || !node.scrollLeft) continue;
          const rect = typeof node.getBoundingClientRect === 'function' ? node.getBoundingClientRect() : { width: window.innerWidth, height: window.innerHeight };
          const className = String(node.className || '');
          const isShell = /app-shell|main-content|overflow-hidden|isolate/.test(className)
            || rect.width >= Math.min(520, window.innerWidth * 0.45)
            || node === document.scrollingElement
            || node === document.documentElement
            || node === document.body;
          if (isShell) node.scrollLeft = 0;
        } catch {}
      }
    };
    resetHorizontalLayoutScroll();
    el.scrollIntoView?.({ block: 'nearest', inline: 'nearest' });
    const rect = el.getBoundingClientRect();
    const base = {
      bubbles: true,
      cancelable: true,
      view: window,
      button: 0,
      clientX: rect.left + Math.max(1, Math.min(rect.width - 1, rect.width / 2)),
      clientY: rect.top + Math.max(1, Math.min(rect.height - 1, rect.height / 2)),
    };
    const pointer = type => new PointerEvent(type, {
      ...base,
      pointerId: 1,
      pointerType: 'mouse',
      isPrimary: true,
      buttons: type === 'pointerdown' ? 1 : 0,
    });
    const mouse = type => new MouseEvent(type, {
      ...base,
      buttons: type === 'mousedown' ? 1 : 0,
    });
    for (const event of [
      pointer('pointerover'),
      pointer('pointerenter'),
      mouse('mouseover'),
      mouse('mouseenter'),
      pointer('pointermove'),
      mouse('mousemove'),
      pointer('pointerdown'),
      mouse('mousedown'),
      pointer('pointerup'),
      mouse('mouseup'),
      mouse('click'),
    ]) {
      el.dispatchEvent(event);
    }
    resetHorizontalLayoutScroll();
    window.requestAnimationFrame(resetHorizontalLayoutScroll);
    setTimeout(resetHorizontalLayoutScroll, 0);
  }"""


def intelligence_trigger_helpers_source() -> str:
    return """(() => {
    const reasoningLabels = ['极低', '低', '中', '高', '超高'];
    const reasoningFromEffort = effort => ({
      low: '低',
      medium: '中',
      high: '高',
      xhigh: '超高',
    }[String(effort || '').toLowerCase()] || '');
    const normalize = text => String(text || '').replace(/\\s+/g, ' ').trim();
    const normalizeMenuName = text => normalize(text).replace(/\\s+/g, '-');
    const footerLabelFromMenuText = menuText => {
      const text = normalize(menuText);
      const match = text.match(/^GPT[-\\s]+(.+)$/i);
      return match ? normalizeMenuName(match[1]) : text;
    };
    const readIntelligenceTrigger = button => {
      if (!button) {
        return { footerText: '', modelLabel: '', reasoningLabel: '', textContent: '' };
      }
      const textContent = normalize(button.textContent || '');
      const modelLabel = normalize(button.querySelector('.text-token-foreground')?.textContent || '');
      const reasoningSpan = normalize(button.querySelector('[class*="labelSm"]')?.textContent || '');
      const reasoningLabel = reasoningLabels.includes(reasoningSpan)
        ? reasoningSpan
        : reasoningFromEffort(button.getAttribute('data-selected-reasoning-effort'));
      const footerText = normalize([modelLabel, reasoningLabel].filter(Boolean).join(' ') || textContent);
      return { footerText, modelLabel, reasoningLabel, textContent };
    };
    const footerConfirmsMenuModel = (menuText, triggerState) => {
      const expected = footerLabelFromMenuText(menuText);
      const actual = normalize(triggerState?.modelLabel || triggerState?.textContent || '');
      if (!expected || !actual) return false;
      return actual.toLowerCase() === expected.toLowerCase();
    };
    const menuNamesMatch = (left, right) => {
      const a = normalizeMenuName(left).toLowerCase();
      const b = normalizeMenuName(right).toLowerCase();
      return Boolean(a && b && a === b);
    };
    return {
      reasoningLabels,
      normalize,
      normalizeMenuName,
      footerLabelFromMenuText,
      readIntelligenceTrigger,
      footerConfirmsMenuModel,
      menuNamesMatch,
    };
  })()"""


def read_gui_status_expression(thread_id: str = "") -> str:
    return f"""(() => {{
      const wantedThreadId = {js_literal(thread_id)};
      const visible = {visible_helper_source()};
      const helpers = {intelligence_trigger_helpers_source()};
      const normalize = helpers.normalize;
      const normalizeThreadId = value => String(value || '').trim().replace(/^local:/, '').replace(/^cloud:/, '');
      const activeRow = [...document.querySelectorAll('[data-app-action-sidebar-thread-row],[data-app-action-sidebar-thread-id]')]
        .filter(el => el.getAttribute('role') === 'button' || el.hasAttribute('data-app-action-sidebar-thread-row'))
        .find(el => el.getAttribute('data-app-action-sidebar-thread-active') === 'true' || el.getAttribute('aria-current') === 'page' || el.getAttribute('aria-selected') === 'true') || null;
      const rawActiveThreadId = activeRow ? (activeRow.getAttribute('data-app-action-sidebar-thread-id') || '') : '';
      const activeThreadId = normalizeThreadId(rawActiveThreadId);
      const activeThreadText = activeRow ? normalize(activeRow.innerText).slice(0, 180) : '';
      const permissionPromptPattern = /权限|授权|批准|请求批准|确认|是否|是否应用这些更改|应用这些更改|应用更改|应用补丁|应用修改|allow|approve|approval|permission|confirm|do you want|may i|apply (these )?(changes|edits|patch)|apply changes|apply patch/i;
      const allowActionPattern = /^(\\d+[.。]\\s*)?(是|允许|继续|应用|确认|同意|allow|approve|continue|apply|yes)(\\b|$)|应用.*(更改|修改|补丁)|apply.*(changes|edits|patch)|continue|approve|allow/i;
      const alwaysActionPattern = /总是|始终|不再询问|以后.*不再|always|remember|以后.*允许|此类/;
      const denyActionPattern = /^(\\d+[.。]\\s*)?(否|跳过|拒绝|取消|不允许|不应用|deny|reject|skip|cancel|no)(\\b|$)|跳过|拒绝|不允许|不应用|deny|reject|skip|cancel|do not apply|don't apply/i;
      const submitActionPattern = /^提交(\\s|$)|提交\\s*⏎|^应用(\\s|$)|应用更改|submit|confirm|apply changes|apply/i;
      const actionText = el => normalize([el.innerText, el.getAttribute('aria-label'), el.title].filter(Boolean).join(' '));
      const hashText = value => {{
        let hash = 0;
        const text = String(value || '');
        for (let index = 0; index < text.length; index += 1) hash = ((hash << 5) - hash + text.charCodeAt(index)) | 0;
        return Math.abs(hash).toString(36);
      }};
      const findGuiPermissionRequest = () => {{
        const containers = [
          ...document.querySelectorAll('[role="dialog"],[role="alertdialog"],[data-state="open"],[popover],form,section,div')
        ].filter(visible).map(el => {{
          const rect = el.getBoundingClientRect();
          const text = normalize(el.innerText || el.textContent || '');
          const controls = [...el.querySelectorAll('button,[role="button"],[role="radio"],[role="menuitemradio"],label')]
            .filter(visible)
            .map(control => {{
              const controlRect = control.getBoundingClientRect();
              const controlText = actionText(control);
              return {{
                control,
                text: controlText,
                rect: controlRect,
                allow: allowActionPattern.test(controlText),
                always: alwaysActionPattern.test(controlText),
                deny: denyActionPattern.test(controlText),
                submit: submitActionPattern.test(controlText),
              }};
            }});
          const isBroadShell = rect.width > window.innerWidth * 0.96 && rect.height > window.innerHeight * 0.72;
          const hasPrompt = permissionPromptPattern.test(text);
          const hasAllow = controls.some(item => item.allow && !item.deny);
          const hasDeny = controls.some(item => item.deny);
          const hasSubmit = controls.some(item => item.submit);
          let score = 0;
          if (el.getAttribute('role') === 'dialog' || el.getAttribute('role') === 'alertdialog') score += 90;
          if (el.getAttribute('data-state') === 'open') score += 30;
          if (hasPrompt) score += 90;
          if (hasAllow) score += 45;
          if (hasDeny) score += 25;
          if (hasSubmit) score += 12;
          if (rect.width >= 180 && rect.height >= 70) score += 8;
          if (isBroadShell && el.getAttribute('role') !== 'dialog' && el.getAttribute('role') !== 'alertdialog') score -= 120;
          if (text.length > 3500 && el.getAttribute('role') !== 'dialog' && el.getAttribute('role') !== 'alertdialog') score -= 80;
          return {{ el, rect, text, controls, score, hasPrompt, hasAllow, hasDeny }};
        }})
          .filter(item => item.score >= 120 && item.hasPrompt && item.hasAllow)
          .sort((a, b) => b.score - a.score || a.rect.y - b.rect.y || a.rect.x - b.rect.x);
        const target = containers[0] || null;
        if (!target) return null;
        const hasAlways = target.controls.some(item => item.always && item.allow);
        const hasDeny = target.controls.some(item => item.deny);
        const actions = [
          {{ id: 'allow', label: /应用/.test(target.text) || /apply/i.test(target.text) ? '应用' : '允许' }},
          ...(hasAlways ? [{{ id: 'allow_always', label: '总是' }}] : []),
          ...(hasDeny ? [{{ id: 'deny', label: '跳过' }}] : [{{ id: 'deny', label: '取消' }}]),
        ];
        const justification = target.text.slice(0, 280);
        return {{
          callId: `gui:${{hashText(justification)}}`,
          toolName: 'codex_gui',
          command: '',
          subject: '',
          prefixRule: [],
          justification,
          text: justification,
          pending: true,
          source: 'gui',
          actions,
        }};
      }};
      const triggers = [...document.querySelectorAll('button[data-codex-intelligence-trigger]')]
        .filter(visible)
        .map(button => ({{ button, rect: button.getBoundingClientRect(), state: helpers.readIntelligenceTrigger(button) }}))
        .filter(item => item.state.footerText || item.state.modelLabel || item.state.textContent)
        .sort((a, b) => b.rect.y - a.rect.y || b.rect.x - a.rect.x);
      const footerState = triggers[0]?.state || {{ footerText: '', modelLabel: '', reasoningLabel: '', textContent: '' }};
      return {{
        ok: true,
        activeThreadId,
        rawActiveThreadId,
        activeThreadText,
        requestedThreadId: wantedThreadId,
        activeThreadMatches: wantedThreadId ? activeThreadId === wantedThreadId : null,
        footerText: footerState.footerText,
        modelDisplayName: footerState.modelLabel,
        reasoningLabel: footerState.reasoningLabel,
        triggerCount: triggers.length,
        permissionRequest: findGuiPermissionRequest(),
      }};
    }})()"""


def title_status_expression(payload: dict[str, object]) -> str:
    return f"""(() => {{
      const payload = {json.dumps(payload, ensure_ascii=False)};
      const ROOT_ID = 'codex-go-title-status-root';
      const UI_VERSION = 'codex-go-title-status-v2';
      let host = document.getElementById(ROOT_ID);
      if (!host) {{
        host = document.createElement('div');
        host.id = ROOT_ID;
        document.documentElement.appendChild(host);
      }}
      host.style.cssText = [
        'position:fixed',
        'top:9px',
        'left:180px',
        'z-index:2147483647',
        'width:max-content',
        'height:26px',
        'pointer-events:none',
        '-webkit-app-region:no-drag',
        'user-select:none'
      ].join(';');
      const root = host.shadowRoot || host.attachShadow({{ mode: 'open' }});
      if (root.__codexGoUiVersion !== UI_VERSION) {{
        if (host.__codexGoCompactTimer) clearInterval(host.__codexGoCompactTimer);
        if (host.__codexGoCompactRaf) cancelAnimationFrame(host.__codexGoCompactRaf);
        host.__codexGoMutationObserver?.disconnect?.();
        host.__codexGoFastListenersInstalled = false;
        root.innerHTML = `
          <style>
            :host {{ all: initial; }}
            .wrap {{
              display: inline-flex;
              align-items: center;
              gap: 5px;
              height: 26px;
              font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "Helvetica Neue", Arial, sans-serif;
              -webkit-font-smoothing: antialiased;
            }}
            .service-pill {{
              height: 26px;
              box-sizing: border-box;
              display: inline-flex;
              align-items: center;
              gap: 5px;
              padding: 0 8px;
              border-radius: 999px;
              color: rgba(235, 255, 241, .96);
              background: rgba(43, 185, 84, .22);
              border: 1px solid rgba(74, 222, 128, .40);
              box-shadow: 0 0 14px rgba(34, 197, 94, .12), inset 0 1px 0 rgba(255,255,255,.10);
              font-size: 11.5px;
              font-weight: 750;
              line-height: 1;
              letter-spacing: 0;
              white-space: nowrap;
              pointer-events: none;
              cursor: default;
              -webkit-app-region: no-drag;
            }}
            .dot {{
              width: 7px;
              height: 7px;
              flex: 0 0 auto;
              border-radius: 999px;
              background: #3ee56f;
              box-shadow: 0 0 9px rgba(62, 229, 111, .75);
            }}
          </style>
          <div class="wrap" part="wrap">
            <span class="service-pill" data-service title="Codex Go" aria-label="Codex Go"><span class="dot"></span><span data-service-text>Go</span></span>
          </div>
        `;
        root.__codexGoUiVersion = UI_VERSION;
      }}
      const visible = el => {{
        if (!el) return false;
        const rect = el.getBoundingClientRect();
        const style = getComputedStyle(el);
        return rect.width > 0 && rect.height > 0 && style.display !== 'none' && style.visibility !== 'hidden';
      }};
      const updateCompact = () => {{
        const rows = [...document.querySelectorAll('[data-app-action-sidebar-thread-row],[data-app-action-sidebar-thread-id]')]
          .filter(el => {{
            const rect = el.getBoundingClientRect();
            return visible(el) && rect.left < 280 && rect.width > 120 && rect.top > 40;
          }});
        host.style.display = rows.length ? 'block' : 'none';
        host.style.left = '180px';
        host.style.top = '9px';
      }};
      const scheduleCompactUpdate = () => {{
        if (host.__codexGoCompactRaf) cancelAnimationFrame(host.__codexGoCompactRaf);
        host.__codexGoCompactRaf = requestAnimationFrame(() => {{
          host.__codexGoCompactRaf = 0;
          updateCompact();
        }});
      }};
      if (host.__codexGoCompactTimer) clearInterval(host.__codexGoCompactTimer);
      host.__codexGoCompactTimer = setInterval(updateCompact, 120);
      if (!host.__codexGoFastListenersInstalled) {{
        window.addEventListener('resize', scheduleCompactUpdate, {{ passive: true }});
        document.addEventListener('click', () => {{
          scheduleCompactUpdate();
          setTimeout(scheduleCompactUpdate, 80);
          setTimeout(scheduleCompactUpdate, 240);
        }}, true);
        const observer = new MutationObserver(() => scheduleCompactUpdate());
        observer.observe(document.documentElement, {{ childList: true, subtree: true, attributes: true, attributeFilter: ['style', 'class', 'aria-expanded', 'aria-hidden', 'data-state'] }});
        host.__codexGoMutationObserver = observer;
        host.__codexGoFastListenersInstalled = true;
      }}
      window.__codexGoTitleStatusUpdate = nextPayload => {{
        window.__codexGoTitleStatusPayload = nextPayload;
        const serviceText = root.querySelector('[data-service-text]');
        if (serviceText) serviceText.textContent = nextPayload.service?.online ? (nextPayload.service?.label || 'Go') : (nextPayload.service?.fallbackLabel || 'Go');
        updateCompact();
      }};
      window.__codexGoTitleStatusUpdate(payload);
      return {{ ok: true, injected: true, version: UI_VERSION }};
    }})()"""


def click_thread_expression(thread_id: str, title: str = "") -> str:
    return f"""(async () => {{
      const threadId = {js_literal(thread_id)};
      const wanted = {js_literal(title)};
      const visible = {visible_helper_source()};
      const domClick = {dom_click_helper_source()};
      const normalize = text => String(text || '').replace(/\\s+/g, ' ').trim();
      const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));
      const normalizeThreadId = value => String(value || '').trim().replace(/^local:/, '').replace(/^cloud:/, '');
      const attrMatches = el => normalizeThreadId(el.getAttribute('data-app-action-sidebar-thread-id') || '') === threadId;
      const activeMatches = el => Boolean(el && attrMatches(el) && (
        el.getAttribute('data-app-action-sidebar-thread-active') === 'true' ||
        el.getAttribute('aria-current') === 'page' ||
        el.getAttribute('aria-selected') === 'true'
      ));
      const allRows = () => [...document.querySelectorAll('[data-app-action-sidebar-thread-row],[data-app-action-sidebar-thread-id]')]
        .filter(el => el.getAttribute('role') === 'button' || el.hasAttribute('data-app-action-sidebar-thread-row'));
      const exactRow = () => allRows().find(attrMatches) || null;
      const titleRow = () => {{
        if (!wanted) return null;
        return [...document.querySelectorAll('[role="button"],[data-app-action-sidebar-thread-row],button,.group')]
          .filter(el => visible(el) && normalize(el.innerText).includes(wanted))[0] || null;
      }};

      let row = null;
      const findDeadline = Date.now() + 2400;
      while (!row && Date.now() < findDeadline) {{
        row = exactRow() || titleRow();
        if (!row) await sleep(120);
      }}
      if (!row) return {{ ok: false, reason: '没有在 Codex DOM 中找到目标线程行', threadId, wanted }};
      const beforeActive = activeMatches(row);
      if (!beforeActive) domClick(row);
      let activeRow = beforeActive ? row : null;
      const deadline = Date.now() + 2400;
      while (!activeRow && Date.now() < deadline) {{
        await sleep(120);
        activeRow = allRows().find(activeMatches) || null;
      }}
      if (!activeRow) return {{ ok: false, reason: 'CDP 已点击目标线程，但 Codex 没有确认切换成功', threadId }};
      return {{
        ok: true,
        threadId,
        title: wanted || activeRow.getAttribute('data-app-action-sidebar-thread-title') || '',
        alreadyActive: beforeActive,
        activeId: activeRow.getAttribute('data-app-action-sidebar-thread-id') || '',
        clickedText: normalize(activeRow.innerText).slice(0, 160),
      }};
    }})()"""


def focus_composer_expression(clear: bool = False) -> str:
    clear_code = """
    document.execCommand('selectAll', false, null);
    document.execCommand('delete', false, null);
    editor.dispatchEvent(new InputEvent('input', { bubbles: true, inputType: 'deleteContentBackward', data: null }));
    """ if clear else ""
    return f"""(() => {{
      const visible = {visible_helper_source()};
      const editor = [...document.querySelectorAll('.ProseMirror,[contenteditable="true"],textarea,input')]
        .find(visible);
      if (!editor) return {{ ok: false, reason: '找不到 Codex 输入框' }};
      editor.focus();
      {clear_code}
      return {{
        ok: true,
        activeTag: document.activeElement && document.activeElement.tagName,
        activeClass: document.activeElement ? String(document.activeElement.className || '') : '',
        text: (editor.innerText || editor.value || '').slice(0, 200),
      }};
    }})()"""


def attachment_drop_target_expression() -> str:
    return f"""(() => {{
      const visible = {visible_helper_source()};
      const queryAllDeep = selector => {{
        const results = [];
        const seen = new Set();
        const visit = root => {{
          if (!root || typeof root.querySelectorAll !== 'function') return;
          for (const el of root.querySelectorAll(selector)) {{
            if (!seen.has(el)) {{
              seen.add(el);
              results.push(el);
            }}
          }}
          for (const host of root.querySelectorAll('*')) {{
            if (host.shadowRoot) visit(host.shadowRoot);
          }}
        }};
        visit(document);
        return results;
      }};
      const editor = queryAllDeep('.ProseMirror,[contenteditable="true"],textarea,input')
        .find(el => visible(el) && el.type !== 'file') || null;
      if (!editor) return {{ ok: false, reason: '找不到 Codex 输入框' }};
      editor.focus();
      const root = editor.closest('form') || editor.closest('[data-testid]') || editor.closest('.relative') || editor.parentElement || editor;
      const rootRect = root.getBoundingClientRect();
      const editorRect = editor.getBoundingClientRect();
      const rect = rootRect.width > 0 && rootRect.height > 0 ? rootRect : editorRect;
      return {{
        ok: true,
        x: Math.round(rect.left + rect.width / 2),
        y: Math.round(rect.top + rect.height / 2),
        tag: root.tagName || editor.tagName || '',
        editorTag: editor.tagName || '',
      }};
    }})()"""


def attachment_snapshot_expression(file_payloads: list[dict[str, object]]) -> str:
    return f"""(() => {{
      const filesPayload = {json.dumps(file_payloads, ensure_ascii=False)};
      const visible = {visible_helper_source()};
      const queryAllDeep = selector => {{
        const results = [];
        const seen = new Set();
        const visit = root => {{
          if (!root || typeof root.querySelectorAll !== 'function') return;
          for (const el of root.querySelectorAll(selector)) {{
            if (!seen.has(el)) {{
              seen.add(el);
              results.push(el);
            }}
          }}
          for (const host of root.querySelectorAll('*')) {{
            if (host.shadowRoot) visit(host.shadowRoot);
          }}
        }};
        visit(document);
        return results;
      }};
      const normalize = text => String(text || '').replace(/\\s+/g, ' ').trim();
      const normalizeKey = text => normalize(text).toLowerCase();
      const names = filesPayload.map(item => String(item.name || '')).filter(Boolean);
      const editor = queryAllDeep('.ProseMirror,[contenteditable="true"],textarea,input')
        .find(el => visible(el) && el.type !== 'file') || null;
      const root = editor && (editor.closest('form') || editor.closest('[data-testid]') || editor.closest('.relative') || editor.parentElement);
      const candidates = queryAllDeep('button,[role="button"],a,div,span,img,svg,canvas,picture,[aria-label],[data-testid]')
        .filter(el => {{
          if (!visible(el)) return false;
          if (!root) return true;
          const rect = el.getBoundingClientRect();
          const rootRect = root.getBoundingClientRect();
          return rect.bottom >= rootRect.top - 260 && rect.top <= rootRect.bottom + 220;
        }})
        .map(el => ({{
          tag: el.tagName || '',
          text: normalize(el.innerText || el.getAttribute('aria-label') || el.title || el.alt || '').slice(0, 220),
          aria: el.getAttribute('aria-label') || '',
          title: el.title || '',
          alt: el.alt || '',
          src: el.tagName === 'IMG' ? (el.currentSrc || el.src || '').slice(0, 120) : '',
          cls: String(el.className || '').slice(0, 160),
        }}));
      const haystack = candidates.map(item => [item.text, item.aria, item.title, item.alt, item.src, item.cls].join(' ')).join('\\n');
      const haystackKey = normalizeKey(haystack);
      const matchedNames = names.filter(name => name && haystackKey.includes(normalizeKey(name)));
      const likely = candidates.filter(item => /attach|attachment|file|image|upload|preview|remove|删除|移除|附件|文件|图片|照片/i.test([item.text, item.aria, item.title, item.alt, item.src, item.cls].join(' ')));
      return {{
        ok: Boolean(editor),
        matchedNames,
        likelyCount: likely.length,
        imageCount: candidates.filter(item => item.tag === 'IMG').length,
        previewCount: candidates.filter(item => /^(IMG|CANVAS|PICTURE)$/.test(item.tag)).length,
        sample: likely.slice(0, 20),
        editorText: editor ? normalize(editor.innerText || editor.value || '').slice(0, 200) : '',
      }};
    }})()"""


def prepare_file_input_expression(expected_count: int) -> str:
    return f"""(() => {{
      const expectedCount = {int(expected_count)};
      const visible = {visible_helper_source()};
      const queryAllDeep = selector => {{
        const results = [];
        const seen = new Set();
        const visit = root => {{
          if (!root || typeof root.querySelectorAll !== 'function') return;
          for (const el of root.querySelectorAll(selector)) {{
            if (!seen.has(el)) {{
              seen.add(el);
              results.push(el);
            }}
          }}
          for (const host of root.querySelectorAll('*')) {{
            if (host.shadowRoot) visit(host.shadowRoot);
          }}
        }};
        visit(document);
        return results;
      }};
      const editors = queryAllDeep('.ProseMirror,[contenteditable="true"],textarea,input')
        .filter(el => visible(el) && el.type !== 'file');
      const editor = editors[0] || null;
      if (!editor) return {{ ok: false, reason: '找不到 Codex 输入框' }};
      editor.focus();
      const root = editor.closest('form') || editor.closest('.relative') || editor.parentElement || document.body;
      const inputs = queryAllDeep('input[type="file"]').filter(input => !input.disabled);
      const score = input => {{
        const accept = String(input.getAttribute('accept') || '').toLowerCase();
        let value = 0;
        if (root && (root === input || root.contains(input))) value += 80;
        if (accept.includes('*') || accept.includes('image') || accept.includes('application') || accept.includes('text') || accept.includes('video')) value += 40;
        if (!accept) value += 6;
        if (input.multiple) value += 4;
        return value;
      }};
      let input = inputs.sort((a, b) => score(b) - score(a))[0] || null;
      let injected = false;
      if (!input) {{
        const owner = root.getRootNode && root.getRootNode() instanceof ShadowRoot ? root.getRootNode() : document.body;
        input = document.createElement('input');
        input.type = 'file';
        input.multiple = expectedCount !== 1;
        input.setAttribute('data-codex-go-attachment-input', 'true');
        input.style.cssText = 'position:fixed;left:-10000px;top:-10000px;width:1px;height:1px;opacity:0;pointer-events:none;';
        owner.appendChild(input);
        injected = true;
      }}
      window.__codexGoAttachmentInput = input;
      window.__codexGoAttachmentEditor = editor;
      window.__codexGoAttachmentRoot = root;
      window.__codexGoAttachmentInjected = injected;
      window.__codexGoAttachmentInitialImageCount = queryAllDeep('img').filter(visible).length;
      window.__codexGoAttachmentInitialPreviewCount = queryAllDeep('img,canvas,picture').filter(visible).length;
      return {{
        ok: true,
        injected,
        expectedCount,
        existingInputCount: inputs.length,
        accept: input.getAttribute('accept') || '',
        multiple: Boolean(input.multiple),
        editorTag: editor.tagName,
        editorClass: String(editor.className || '').slice(0, 160),
      }};
    }})()"""


def attach_files_after_set_expression(expected_count: int) -> str:
    return f"""(async () => {{
      const expectedCount = {int(expected_count)};
      const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));
      const visible = {visible_helper_source()};
      const queryAllDeep = selector => {{
        const results = [];
        const seen = new Set();
        const visit = root => {{
          if (!root || typeof root.querySelectorAll !== 'function') return;
          for (const el of root.querySelectorAll(selector)) {{
            if (!seen.has(el)) {{
              seen.add(el);
              results.push(el);
            }}
          }}
          for (const host of root.querySelectorAll('*')) {{
            if (host.shadowRoot) visit(host.shadowRoot);
          }}
        }};
        visit(document);
        return results;
      }};
      const input = window.__codexGoAttachmentInput || null;
      if (!input) return {{ ok: false, reason: '找不到附件 input' }};
      const injected = Boolean(window.__codexGoAttachmentInjected);
      const initialImageCount = Number(window.__codexGoAttachmentInitialImageCount || 0);
      const initialPreviewCount = Number(window.__codexGoAttachmentInitialPreviewCount || initialImageCount);
      const files = Array.from(input.files || []);
      if (files.length < expectedCount) return {{ ok: false, reason: 'CDP 没有把图片文件放进附件 input', fileCount: files.length, expectedCount }};
      const editor = window.__codexGoAttachmentEditor || queryAllDeep('.ProseMirror,[contenteditable="true"],textarea,input').find(el => visible(el) && el.type !== 'file') || null;
      const root = window.__codexGoAttachmentRoot || (editor && (editor.closest('form') || editor.closest('.relative') || editor.parentElement)) || document.body;
      const dropTarget = editor || root || document.activeElement || document.body;
      const names = files.map(file => file.name || '').filter(Boolean);
      const dispatch = (target, event) => {{
        try {{
          const result = target.dispatchEvent(event);
          return {{ type: event.type, target: target.tagName || target.nodeName || 'node', defaultPrevented: event.defaultPrevented, accepted: result === false }};
        }} catch (error) {{
          return {{ type: event.type, target: target.tagName || target.nodeName || 'node', error: String(error && error.message || error) }};
        }}
      }};
      const events = [];
      events.push(dispatch(input, new Event('input', {{ bubbles: true, composed: true }})));
      events.push(dispatch(input, new Event('change', {{ bubbles: true, composed: true }})));
      let dataTransferReady = false;
      if (injected && dropTarget) try {{
        const dataTransfer = new DataTransfer();
        for (const file of files) dataTransfer.items.add(file);
        dataTransferReady = dataTransfer.files.length >= expectedCount;
        for (const type of ['dragenter', 'dragover', 'drop']) {{
          events.push(dispatch(dropTarget, new DragEvent(type, {{ bubbles: true, cancelable: true, composed: true, dataTransfer }})));
        }}
      }} catch (error) {{
        events.push({{ type: 'dataTransfer', error: String(error && error.message || error) }});
      }}
      await sleep(600);
      const bodyText = String(document.body?.innerText || '');
      const matchedNames = names.filter(name => name && bodyText.includes(name));
      const imageCount = queryAllDeep('img').filter(visible).length;
      const imageCountDelta = imageCount - initialImageCount;
      const previewCount = queryAllDeep('img,canvas,picture').filter(visible).length;
      const previewCountDelta = previewCount - initialPreviewCount;
      const acceptedByEvent = events.some(event => event.defaultPrevented || event.accepted);
      const accepted = matchedNames.length > 0 || imageCountDelta > 0 || previewCountDelta > 0;
      return {{
        ok: accepted,
        reason: accepted ? '' : 'Codex Desktop 没有接收附件事件，已取消发送以避免只发送文字。',
        injected,
        fileCount: files.length,
        expectedCount,
        dataTransferReady,
        acceptedByEvent,
        matchedNames,
        imageCount,
        imageCountDelta,
        previewCount,
        previewCountDelta,
        events: events.slice(0, 20),
      }};
    }})()"""


def click_send_expression() -> str:
    return f"""(() => {{
      const visible = {visible_helper_source()};
      const normalize = text => String(text || '').replace(/\\s+/g, ' ').trim();
      const editor = [...document.querySelectorAll('.ProseMirror,[contenteditable="true"],textarea,input')]
        .find(visible);
      const root = editor && (editor.closest('form') || editor.closest('.relative') || editor.parentElement);
      const buttons = root ? [...root.querySelectorAll('button,[role="button"]')].filter(button => {{
        const rect = button.getBoundingClientRect();
        return visible(button) && rect.width <= 52 && rect.height <= 52 && !button.disabled && button.getAttribute('aria-disabled') !== 'true';
      }}) : [];
      const sendButton = buttons.find(button => /发送|Send|Submit/i.test(normalize([button.innerText, button.getAttribute('aria-label'), button.title].filter(Boolean).join(' ')))) || buttons.at(-1);
      if (!sendButton) return {{ ok: false, reason: '找不到可用发送按钮' }};
      sendButton.click();
      return {{ ok: true, aria: sendButton.getAttribute('aria-label') || '' }};
    }})()"""


def stop_response_expression() -> str:
    return f"""(() => {{
      const visible = {visible_helper_source()};
      const buttons = [...document.querySelectorAll('button,[role="button"]')].filter(visible);
      const stop = buttons.find(button => /停止|取消|Stop|Cancel/i.test(button.getAttribute('aria-label') || button.innerText || ''));
      if (!stop) return {{ ok: false, reason: '找不到停止按钮' }};
      stop.click();
      return {{ ok: true, aria: stop.getAttribute('aria-label') || '' }};
    }})()"""


def new_thread_expression(project_name: str = "") -> str:
    return f"""(() => {{
      const projectName = {js_literal(project_name)};
      const visible = {visible_helper_source()};
      const normalize = text => String(text || '').replace(/\\s+/g, ' ').trim();
      const buttons = [...document.querySelectorAll('button,[role="button"]')].filter(visible);
      let button = null;
      if (projectName) {{
        button = buttons.find(item => (item.getAttribute('aria-label') || '').includes('在 ' + projectName + ' 中开始新对话'));
      }}
      button = button || buttons.find(item => normalize(item.innerText).startsWith('新对话'));
      if (!button) return {{ ok: false, reason: '找不到新对话按钮', projectName }};
      const rect = button.getBoundingClientRect();
      button.click();
      return {{ ok: true, projectName, text: normalize(button.innerText), aria: button.getAttribute('aria-label') || '', rect: {{ x: rect.x, y: rect.y, w: rect.width, h: rect.height }} }};
    }})()"""


def pending_sends_expression() -> str:
    return f"""(() => {{
      const visible = {visible_helper_source()};
      const normalize = text => String(text || '').replace(/\\s+/g, ' ').trim();
      const buttonText = button => normalize([button.innerText, button.getAttribute('aria-label'), button.title].filter(Boolean).join(' '));
      const guidePattern = /引导|指导|guide/i;
      const deletePattern = /删除排队的消息|删除|移除|取消排队|delete|remove|cancel/i;
      const noisePattern = /Draggable item [\\s\\S]*?was dropped over droppable area [\\w-]+/gi;

      const textWithoutControls = root => {{
        const controls = [...root.querySelectorAll('button,[role="button"],svg,[aria-hidden="true"]')];
        const chunks = [];
        const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
        while (walker.nextNode()) {{
          const node = walker.currentNode;
          const parent = node.parentElement;
          if (!parent) continue;
          if (controls.some(control => control === parent || control.contains(parent))) continue;
          if (parent.closest('.sr-only,[hidden],[aria-hidden="true"]')) continue;
          const style = getComputedStyle(parent);
          if (style.display === 'none' || style.visibility === 'hidden') continue;
          const text = normalize(String(node.nodeValue || '').replace(noisePattern, ' '));
          if (text) chunks.push(text);
        }}
        return normalize(chunks.join(' ')).replace(noisePattern, ' ');
      }};

      const rowFromButton = button => {{
        let node = button;
        let best = null;
        for (let depth = 0; node && depth < 9; depth += 1, node = node.parentElement) {{
          if (!(node instanceof HTMLElement) || !visible(node)) continue;
          const buttons = [...node.querySelectorAll('button,[role="button"]')].filter(visible);
          const labels = buttons.map(buttonText).filter(Boolean);
          const hasGuide = labels.some(text => guidePattern.test(text));
          const hasDelete = labels.some(text => deletePattern.test(text));
          if (!hasGuide || !hasDelete) continue;
          const rect = node.getBoundingClientRect();
          const rawText = normalize((node.innerText || node.textContent || '').replace(noisePattern, ' '));
          const messageText = textWithoutControls(node);
          const isBroadShell = rect.width > window.innerWidth * 0.82 && rect.height > 160;
          let score = 0;
          if (messageText) score += 130;
          else score -= 120;
          score += Math.max(0, 42 - depth * 4);
          if (rect.height >= 24 && rect.height <= 96) score += 26;
          if (rawText.includes('排队') || labels.some(text => /排队/.test(text))) score += 8;
          if (isBroadShell) score -= 80;
          const candidate = {{ node, text: messageText || rawText, rawText, labels, score, rect }};
          if (!best || candidate.score > best.score) best = candidate;
        }}
        return best;
      }};

      const rows = [];
      const seen = new Set();
      const guideButtons = [...document.querySelectorAll('button,[role="button"]')]
        .filter(visible)
        .filter(button => {{
          const text = buttonText(button);
          return guidePattern.test(text) && !deletePattern.test(text);
        }});

      for (const button of guideButtons) {{
        const row = rowFromButton(button);
        if (!row || seen.has(row.node)) continue;
        seen.add(row.node);
        const text = normalize(row.text);
        if (!text || guidePattern.test(text) && text.length <= 8) continue;
        rows.push({{
          text,
          summary: text,
          order: 0,
          actions: {{ guide: true, delete: true }},
          labels: row.labels.slice(0, 8),
          rect: {{ x: row.rect.x, y: row.rect.y, w: row.rect.width, h: row.rect.height }},
        }});
      }}

      rows.sort((a, b) => a.rect.y - b.rect.y || a.rect.x - b.rect.x);
      rows.forEach((item, index) => {{ item.order = index; }});
      return {{ ok: true, items: rows }};
    }})()"""


def pending_send_action_expression(action: str, text_hint: str = "") -> str:
    return f"""(async () => {{
      const action = {js_literal(action)};
      const textHint = {js_literal(text_hint)};
      const visible = {visible_helper_source()};
      const domClick = {dom_click_helper_source()};
      const normalize = text => String(text || '').replace(/\\s+/g, ' ').trim();
      const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));
      const buttonText = button => normalize([button.innerText, button.getAttribute('aria-label'), button.title].filter(Boolean).join(' '));
      const guidePattern = /引导|指导|guide/i;
      const deletePattern = /删除排队的消息|删除|移除|取消排队|delete|remove|cancel/i;
      const queueTextPattern = /排队|待发送|queued|queue|pending/i;
      const hint = normalize(textHint).slice(0, 180);
      const hintHead = hint.slice(0, 60);
      const actionPattern = action === 'delete' ? deletePattern : guidePattern;
      const oppositePattern = action === 'delete' ? guidePattern : deletePattern;

      const rowFromButton = button => {{
        let node = button;
        let best = null;
        for (let depth = 0; node && depth < 9; depth += 1, node = node.parentElement) {{
          if (!(node instanceof HTMLElement) || !visible(node)) continue;
          const buttons = [...node.querySelectorAll('button,[role="button"]')].filter(visible);
          const labels = buttons.map(buttonText).filter(Boolean);
          const hasGuide = labels.some(text => guidePattern.test(text));
          const hasDelete = labels.some(text => deletePattern.test(text));
          if (!hasGuide || !hasDelete) continue;
          const rect = node.getBoundingClientRect();
          const text = normalize(node.innerText || node.textContent || '');
          const isTooBroad = rect.width > window.innerWidth * 0.82 && rect.height > 160;
          let score = 80;
          score += Math.max(0, 40 - depth * 4);
          if (queueTextPattern.test([node.getAttribute('aria-label'), text, labels.join(' ')].join(' '))) score += 20;
          if (hint && text.includes(hint)) score += 100;
          else if (hintHead && text.includes(hintHead)) score += 70;
          else if (hintHead && normalize(text).includes(hintHead)) score += 45;
          if (rect.height >= 24 && rect.height <= 90) score += 18;
          if (isTooBroad) score -= 50;
          const candidate = {{ node, text, labels, score, rect, depth }};
          if (!best || candidate.score > best.score) best = candidate;
        }}
        return best;
      }};

      const candidates = [];
      for (const button of [...document.querySelectorAll('button,[role="button"]')].filter(visible)) {{
        const text = buttonText(button);
        if (!actionPattern.test(text) || oppositePattern.test(text)) continue;
        const row = rowFromButton(button);
        if (!row) continue;
        const rect = button.getBoundingClientRect();
        let score = row.score;
        if (action === 'guide' && normalize(button.innerText) === '引导') score += 45;
        if (action === 'delete' && /删除排队的消息/.test(text)) score += 55;
        if (hint && row.text.includes(hint)) score += 80;
        else if (hintHead && row.text.includes(hintHead)) score += 45;
        candidates.push({{ button, row, text, score, rect }});
      }}

      candidates.sort((a, b) => b.score - a.score || a.rect.y - b.rect.y || a.rect.x - b.rect.x);
      const target = candidates[0] || null;
      if (!target || target.score < 95) {{
        return {{
          ok: false,
          reason: action === 'delete' ? '没有在 Codex 页面找到这条排队消息的删除按钮' : '没有在 Codex 页面找到这条排队消息的引导按钮',
          action,
          textHint: hint,
          candidates: candidates.slice(0, 8).map(item => ({{
            score: item.score,
            button: item.text,
            rowText: item.row.text.slice(0, 220),
            labels: item.row.labels.slice(0, 8),
            rect: {{ x: item.rect.x, y: item.rect.y, w: item.rect.width, h: item.rect.height }},
          }})),
        }};
      }}

      const clickedText = target.text;
      const rowText = target.row.text.slice(0, 260);
      domClick(target.button);
      await sleep(260);
      return {{
        ok: true,
        action,
        clickedText,
        rowText,
        score: target.score,
        rect: {{ x: target.rect.x, y: target.rect.y, w: target.rect.width, h: target.rect.height }},
      }};
    }})()"""


def permission_action_expression(action: str, command: str = "", justification: str = "") -> str:
    return f"""(async () => {{
      const action = {js_literal(action)};
      const expectedCommand = {js_literal(command)};
      const expectedJustification = {js_literal(justification)};
      const visible = {visible_helper_source()};
      const domClick = {dom_click_helper_source()};
      const normalize = text => String(text || '').replace(/\\s+/g, ' ').trim();
      const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));
      const buttonText = button => normalize([button.innerText, button.getAttribute('aria-label'), button.title].filter(Boolean).join(' '));
      const isDisabled = button => Boolean(
        button?.disabled ||
        button?.getAttribute?.('disabled') !== null ||
        button?.getAttribute?.('aria-disabled') === 'true' ||
        button?.getAttribute?.('data-disabled') === 'true'
      );
      const isInViewport = rect => rect.bottom >= -8 && rect.top <= window.innerHeight + 80 && rect.right >= -8 && rect.left <= window.innerWidth + 80;
      const permissionTextPattern = /权限|授权|允许|继续|拒绝|批准|请求批准|询问|不再询问|跳过|是否|是否运行|是否打开|是否启动|是否使用|是否应用|应用这些更改|应用更改|应用补丁|应用修改|执行此命令|运行此命令|打开浏览器|使用浏览器|工具|应用|网站|链接|deny|allow|approve|approval|permission|continue|run|execute|open|launch|browser|tool|sandbox|escalat|submit|skip|apply (these )?(changes|edits|patch)|apply changes|apply patch/i;
      const allowPattern = /^(\\d+[.。]\\s*)?(是|允许|继续|运行|执行|打开|启动|使用|应用|确认|同意|allow|approve|continue|run|execute|open|launch|use|apply|yes)(\\b|$)|允许.*(本次|一次|继续)|应用.*(更改|修改|补丁)|continue|approve|allow|open|launch|apply.*(changes|edits|patch)/i;
      const alwaysPattern = /总是|始终|不再询问|以后.*不再|always|remember|以后.*允许|此类命令/;
      const denyPattern = /^(\\d+[.。]\\s*)?(否|跳过|拒绝|取消|不允许|不应用|deny|reject|skip|cancel|no)(\\b|$)|跳过|拒绝|不允许|不应用|deny|reject|skip|cancel|do not apply|don't apply/i;
      const submitPattern = /^提交(\\s|$)|提交\\s*⏎|^应用(\\s|$)|应用更改|submit|confirm|apply changes|apply/i;
      const containers = [
        ...document.querySelectorAll('[role="dialog"],[data-state="open"],[role="alertdialog"],[popover],section,form,div')
      ].filter(visible).map(el => {{
        const rect = el.getBoundingClientRect();
        const text = normalize(el.innerText || el.textContent || '');
        const isBroadShell = rect.width > window.innerWidth * 0.96 && rect.height > window.innerHeight * 0.72;
        let score = 0;
        if (el.getAttribute('role') === 'dialog' || el.getAttribute('role') === 'alertdialog') score += 80;
        if (el.getAttribute('data-state') === 'open') score += 25;
        if (permissionTextPattern.test(text)) score += 60;
        if (expectedCommand && text.includes(expectedCommand)) score += 80;
        if (expectedJustification && text.includes(expectedJustification.slice(0, 60))) score += 60;
        if (rect.width >= 180 && rect.height >= 80) score += 10;
        if (rect.left < window.innerWidth && rect.top < window.innerHeight) score += 5;
        if (isBroadShell && el.getAttribute('role') !== 'dialog' && el.getAttribute('role') !== 'alertdialog') score -= 90;
        if (text.length > 4000 && el.getAttribute('role') !== 'dialog' && el.getAttribute('role') !== 'alertdialog') score -= 60;
        return {{ el, rect, text, score }};
      }}).filter(item => item.score >= 60).sort((a, b) => b.score - a.score);

      const searchRoots = (containers.length ? containers.map(item => item.el) : [document.body])
        .filter((el, index, list) => el && list.indexOf(el) === index);

      const submitNear = (optionButton, includeDisabled = false, root = null) => {{
        const optionRect = optionButton.getBoundingClientRect();
        const rootElement = root instanceof HTMLElement ? root : null;
        const submitButtonsIn = node => [...node.querySelectorAll('button,[role="button"]')]
          .filter(button => visible(button) && (includeDisabled || !isDisabled(button)))
          .map(button => ({{ button, text: buttonText(button), rect: button.getBoundingClientRect() }}))
          .filter(item => submitPattern.test(item.text) && !/提交或推送/.test(item.text));
        for (let node = optionButton.parentElement, depth = 0; node && depth < 9; depth += 1, node = node.parentElement) {{
          if (rootElement && !rootElement.contains(node)) break;
          if (!(node instanceof HTMLElement) || !visible(node)) continue;
          const nodeRect = node.getBoundingClientRect();
          if (nodeRect.height > Math.max(360, window.innerHeight * 0.58) || nodeRect.width > window.innerWidth * 0.96) continue;
          const submit = submitButtonsIn(node)
            .sort((a, b) => Math.abs(a.rect.y - optionRect.y) - Math.abs(b.rect.y - optionRect.y))[0];
          if (submit) return submit;
        }}
        if (!rootElement || rootElement === document.body || rootElement === document.documentElement) return null;
        const rootRect = rootElement.getBoundingClientRect();
        if (rootRect.height > Math.max(460, window.innerHeight * 0.72) || rootRect.width > window.innerWidth * 0.96) return null;
        return submitButtonsIn(rootElement)
          .filter(item => Math.abs(item.rect.x - optionRect.x) < 520 && item.rect.y >= optionRect.y - 8 && item.rect.y <= optionRect.y + 240)
          .sort((a, b) => Math.abs(a.rect.y - optionRect.y) - Math.abs(b.rect.y - optionRect.y) || b.rect.x - a.rect.x)[0] || null;
      }};
      const enabledSubmitNear = async (optionButton, fallbackSubmit = null, root = null) => {{
        const deadline = Date.now() + 1500;
        while (Date.now() < deadline) {{
          const submit = submitNear(optionButton, true, root) || fallbackSubmit;
          if (submit && visible(submit.button) && !isDisabled(submit.button)) return submit;
          await sleep(80);
        }}
        return null;
      }};
      const nativeActivateOption = optionButton => {{
        if (!(optionButton instanceof HTMLElement)) return false;
        const control = optionButton.control || optionButton.querySelector?.('input,[role="radio"],[role="checkbox"]') || null;
        const isSelected = control && (
          control.checked === true ||
          control.getAttribute?.('aria-checked') === 'true' ||
          control.getAttribute?.('data-state') === 'checked'
        );
        if (isSelected) return false;
        if (typeof optionButton.click === 'function') optionButton.click();
        if (control instanceof HTMLElement && typeof control.click === 'function') {{
          const selectedAfterLabel = control.checked === true || control.getAttribute?.('aria-checked') === 'true' || control.getAttribute?.('data-state') === 'checked';
          if (!selectedAfterLabel) control.click();
        }}
        return true;
      }};

      const selectableOptionSelector = '[role="radio"],[role="menuitemradio"],label';
      const optionCandidates = [];
      for (const root of searchRoots) {{
        for (const button of [...root.querySelectorAll(selectableOptionSelector)].filter(button => visible(button) && !isDisabled(button))) {{
          const text = buttonText(button);
          if (!text || submitPattern.test(text) || /提交或推送/.test(text)) continue;
          const container = containers.find(item => item.el === root || item.el.contains(button));
          if (!container) continue;
          const rect = button.getBoundingClientRect();
          if (!isInViewport(rect)) continue;
          if (rect.x < 240 || rect.y < 40 || rect.y > window.innerHeight + 80) continue;
          let score = container ? Math.min(90, Math.max(0, container.score)) : 0;
          let noSubmit = false;
          if (action === 'deny') {{
            if (denyPattern.test(text)) {{
              score += 120;
              noSubmit = /跳过|skip/i.test(text);
            }}
            if (allowPattern.test(text)) score -= 80;
          }} else if (action === 'allow_always') {{
            if (alwaysPattern.test(text)) score += 130;
            if (allowPattern.test(text)) score += 25;
            if (denyPattern.test(text)) score -= 90;
          }} else {{
            if (allowPattern.test(text)) score += 120;
            if (normalize(text) === '是' || /^\\d+[.。]\\s*是\\b/.test(text)) score += 40;
            if (alwaysPattern.test(text)) score -= 55;
            if (denyPattern.test(text)) score -= 90;
          }}
          if (rect.width >= 36 && rect.height >= 24) score += 6;
          if (score > 95) optionCandidates.push({{ button, text, score, rect, noSubmit, submit: noSubmit ? null : submitNear(button, true, container.el), container: container.el }});
        }}
      }}
      optionCandidates.sort((a, b) => b.score - a.score || a.rect.y - b.rect.y || a.rect.x - b.rect.x);
      const optionTarget = optionCandidates.find(item => item.noSubmit || item.submit) || null;
      if (optionTarget) {{
        const beforeText = optionTarget.text;
        domClick(optionTarget.button);
        await sleep(180);
        let submitText = '';
        if (!optionTarget.noSubmit) {{
          let submit = submitNear(optionTarget.button, false, optionTarget.container) || await enabledSubmitNear(optionTarget.button, optionTarget.submit, optionTarget.container);
          if (!submit && nativeActivateOption(optionTarget.button)) {{
            await sleep(180);
            submit = submitNear(optionTarget.button, false, optionTarget.container) || await enabledSubmitNear(optionTarget.button, optionTarget.submit, optionTarget.container);
          }}
          if (!submit) {{
            return {{
              ok: true,
              action,
              clickedText: beforeText,
              submittedText: '',
              optionFlow: true,
              resolvedWithoutSubmit: true,
              score: optionTarget.score,
              rect: {{ x: optionTarget.rect.x, y: optionTarget.rect.y, w: optionTarget.rect.width, h: optionTarget.rect.height }},
            }};
          }}
          submitText = submit.text;
          domClick(submit.button);
          await sleep(240);
          return {{
            ok: true,
            action,
            clickedText: beforeText,
            submittedText: submitText,
            optionFlow: true,
            score: optionTarget.score,
            rect: {{ x: optionTarget.rect.x, y: optionTarget.rect.y, w: optionTarget.rect.width, h: optionTarget.rect.height }},
          }};
        }} else {{
          return {{
            ok: true,
            action,
            clickedText: beforeText,
            submittedText: submitText,
            optionFlow: true,
            score: optionTarget.score,
            rect: {{ x: optionTarget.rect.x, y: optionTarget.rect.y, w: optionTarget.rect.width, h: optionTarget.rect.height }},
          }};
        }}
      }}

      const candidates = [];
      for (const root of searchRoots) {{
        for (const button of [...root.querySelectorAll('button,[role="button"]')].filter(button => visible(button) && !isDisabled(button))) {{
          const text = buttonText(button);
          if (!text) continue;
          let score = 0;
          if (action === 'deny') {{
            if (denyPattern.test(text)) score += 100;
            if (allowPattern.test(text)) score -= 60;
          }} else if (action === 'allow_always') {{
            if (alwaysPattern.test(text) && allowPattern.test(text)) score += 120;
            else if (alwaysPattern.test(text)) score += 95;
            if (denyPattern.test(text)) score -= 80;
          }} else {{
            if (allowPattern.test(text)) score += 100;
            if (alwaysPattern.test(text)) score -= 35;
            if (denyPattern.test(text)) score -= 80;
          }}
          const container = containers.find(item => item.el === root || item.el.contains(button));
          if (container) score += Math.min(80, Math.max(0, container.score));
          const rect = button.getBoundingClientRect();
          if (!isInViewport(rect)) continue;
          if (rect.width >= 36 && rect.height >= 24) score += 5;
          if (score > 0) candidates.push({{ button, text, score, rect }});
        }}
      }}
      candidates.sort((a, b) => b.score - a.score || b.rect.x - a.rect.x);
      const target = candidates[0] || null;
      if (!target || target.score < 90) {{
        return {{
          ok: false,
          reason: '没有在 Codex 页面找到可点击的权限按钮',
          action,
          expectedCommand,
          containers: containers.slice(0, 5).map(item => ({{ score: item.score, text: item.text.slice(0, 240), rect: {{ x: item.rect.x, y: item.rect.y, w: item.rect.width, h: item.rect.height }} }})),
          buttons: candidates.slice(0, 12).map(item => ({{ score: item.score, text: item.text }})),
        }};
      }}
      const beforeText = target.text;
      domClick(target.button);
      await sleep(260);
      return {{
        ok: true,
        action,
        clickedText: beforeText,
        score: target.score,
        rect: {{ x: target.rect.x, y: target.rect.y, w: target.rect.width, h: target.rect.height }},
      }};
    }})()"""


def list_model_options_expression() -> str:
    return f"""(async () => {{
      const visible = {visible_helper_source()};
      const domClick = {dom_click_helper_source()};
      const helpers = {intelligence_trigger_helpers_source()};
      const normalize = helpers.normalize;
      const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));
      const closeMenus = () => {{
        [0, 1, 2].forEach(() => {{
          document.dispatchEvent(new KeyboardEvent('keydown', {{ key: 'Escape', code: 'Escape', keyCode: 27, which: 27, bubbles: true, cancelable: true }}));
        }});
      }};
      const reasoningLabels = helpers.reasoningLabels;
      const modelTextPattern = /GPT|5\\.\\d|模型|Codex|Mini/i;
      const collectModelNames = () => {{
        const items = [...document.querySelectorAll('[role="menuitem"]')]
          .filter(visible)
          .map(item => ({{ text: normalize(item.textContent || ''), popup: item.getAttribute('aria-haspopup') || '' }}))
          .filter(entry => entry.text && !entry.popup && !reasoningLabels.includes(entry.text) && modelTextPattern.test(entry.text))
          .map(entry => entry.text);
        return [...new Set(items)];
      }};
      const getTrigger = () => [...document.querySelectorAll('button[data-codex-intelligence-trigger]')]
        .filter(visible)
        .map(button => ({{ button, rect: button.getBoundingClientRect(), state: helpers.readIntelligenceTrigger(button) }}))
        .filter(item => item.state.footerText || item.state.modelLabel || item.state.textContent)
        .sort((a, b) => b.rect.y - a.rect.y || b.rect.x - a.rect.x)[0];

      closeMenus();
      await sleep(120);
      const trigger = getTrigger();
      if (!trigger) return {{ ok: false, reason: '找不到模型/推理菜单按钮' }};

      domClick(trigger.button);
      await sleep(280);

      let names = collectModelNames();
      if (!names.length) {{
        const submenuTrigger = [...document.querySelectorAll('[role="menuitem"][aria-haspopup="menu"]')]
          .filter(visible)
          .map(item => ({{ item, text: normalize(item.textContent || ''), rect: item.getBoundingClientRect() }}))
          .filter(entry => modelTextPattern.test(entry.text) || entry.rect.y > window.innerHeight * 0.55)
          .sort((a, b) => b.rect.y - a.rect.y || b.rect.x - a.rect.x)[0]?.item || null;
        if (!submenuTrigger) {{
          closeMenus();
          return {{ ok: false, reason: '找不到模型子菜单入口' }};
        }}
        domClick(submenuTrigger);
        const deadline = Date.now() + 1800;
        while (!names.length && Date.now() < deadline) {{
          await sleep(120);
          names = collectModelNames();
        }}
      }}

      closeMenus();
      if (!names.length) return {{ ok: false, reason: '模型菜单为空' }};
      return {{ ok: true, displayNames: names }};
    }})()"""


def switch_model_expression(target_display_name: str) -> str:
    return f"""(async () => {{
      const targetDisplayName = {js_literal(target_display_name)};
      const visible = {visible_helper_source()};
      const domClick = {dom_click_helper_source()};
      const helpers = {intelligence_trigger_helpers_source()};
      const normalize = helpers.normalize;
      const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));
      const resetHorizontalLayoutScroll = () => {{
        for (const node of [document.scrollingElement, document.documentElement, document.body, ...document.querySelectorAll('*')]) {{
          try {{
            if (!node || !node.scrollLeft) continue;
            const rect = typeof node.getBoundingClientRect === 'function' ? node.getBoundingClientRect() : {{ width: window.innerWidth }};
            const className = String(node.className || '');
            if (/app-shell|main-content|overflow-hidden|isolate/.test(className) || rect.width >= Math.min(520, window.innerWidth * 0.45)) node.scrollLeft = 0;
          }} catch {{}}
        }}
      }};
      const modelTextPattern = /GPT|5\\.\\d|模型/i;
      const getTrigger = () => [...document.querySelectorAll('button[data-codex-intelligence-trigger]')]
        .filter(visible)
        .map(button => ({{ button, rect: button.getBoundingClientRect(), state: helpers.readIntelligenceTrigger(button) }}))
        .filter(item => item.state.footerText || item.state.modelLabel || item.state.textContent)
        .sort((a, b) => b.rect.y - a.rect.y || b.rect.x - a.rect.x)[0];
      const hasOpenMenu = () => [...document.querySelectorAll('[role="menu"]')].filter(visible).some(menu => menu.getAttribute('data-state') === 'open' || normalize(menu.textContent || ''));
      const hasModelTargetItem = () => [...document.querySelectorAll('[role="menuitem"]')]
        .filter(visible)
        .some(item => helpers.menuNamesMatch(normalize(item.textContent || ''), targetDisplayName));

      resetHorizontalLayoutScroll();
      let trigger = getTrigger();
      if (!trigger) return {{ ok: false, reason: '找不到模型/推理菜单按钮' }};
      const beforeFooter = trigger.state;
      const reasoningBefore = beforeFooter.reasoningLabel;

      if (!hasModelTargetItem()) {{
        if (hasOpenMenu()) {{
          document.dispatchEvent(new KeyboardEvent('keydown', {{ key: 'Escape', code: 'Escape', keyCode: 27, which: 27, bubbles: true, cancelable: true }}));
          document.body.dispatchEvent(new MouseEvent('pointerdown', {{ bubbles: true, cancelable: true, view: window, clientX: 1, clientY: 1 }}));
          document.body.dispatchEvent(new MouseEvent('mousedown', {{ bubbles: true, cancelable: true, view: window, clientX: 1, clientY: 1 }}));
          document.body.dispatchEvent(new MouseEvent('mouseup', {{ bubbles: true, cancelable: true, view: window, clientX: 1, clientY: 1 }}));
          document.body.dispatchEvent(new MouseEvent('click', {{ bubbles: true, cancelable: true, view: window, clientX: 1, clientY: 1 }}));
          await sleep(140);
          resetHorizontalLayoutScroll();
          trigger = getTrigger() || trigger;
        }}
        domClick(trigger.button);
        await sleep(280);
      }}

      let submenuTrigger = [...document.querySelectorAll('[role="menuitem"][aria-haspopup="menu"]')]
        .filter(visible)
        .map(item => ({{ item, text: normalize(item.textContent || ''), rect: item.getBoundingClientRect() }}))
        .filter(entry => modelTextPattern.test(entry.text) || entry.rect.y > window.innerHeight * 0.55)
        .sort((a, b) => b.rect.y - a.rect.y || b.rect.x - a.rect.x)[0]?.item || null;
      if (!submenuTrigger) {{
        return {{
          ok: false,
          reason: '找不到模型子菜单入口',
          targetDisplayName,
          menuText: [...document.querySelectorAll('[role="menu"]')].map(item => normalize(item.textContent || '')).join(' | ').slice(0, 800),
          menuItems: [...document.querySelectorAll('[role="menuitem"]')].filter(visible).map(item => normalize(item.textContent || '')).filter(Boolean).slice(0, 40),
        }};
      }}

      let target = null;
      const findTarget = () => {{
        const modelItems = [...document.querySelectorAll('[role="menuitem"]')]
          .filter(visible)
          .map(item => ({{ item, text: normalize(item.textContent || ''), selected: item.getAttribute('data-model-selected') === 'true', popup: item.getAttribute('aria-haspopup') || '' }}))
          .filter(entry => entry.text && !entry.popup);
        return modelItems.find(entry => helpers.menuNamesMatch(entry.text, targetDisplayName)) || null;
      }};

      target = findTarget();
      if (!target) {{
        domClick(submenuTrigger);
        const deadline = Date.now() + 1800;
        while (!target && Date.now() < deadline) {{
          await sleep(120);
          target = findTarget();
        }}
      }}
      if (!target) {{
        return {{
          ok: false,
          reason: '找不到目标模型菜单项',
          targetDisplayName,
          submenuText: normalize(submenuTrigger.textContent || ''),
          items: [...document.querySelectorAll('[role="menuitem"]')].filter(visible).map(item => normalize(item.textContent || '')).filter(Boolean).slice(0, 60),
        }};
      }}

      if (target.selected) {{
        return {{
          ok: true,
          targetDisplayName,
          clickedText: target.text,
          alreadySelected: true,
          footerText: beforeFooter.footerText,
          afterText: beforeFooter.footerText,
          modelDisplayName: beforeFooter.modelLabel,
          expectedFooterLabel: helpers.footerLabelFromMenuText(target.text),
          submenuText: normalize(submenuTrigger.textContent || ''),
        }};
      }}

      domClick(target.item);
      let afterFooter = beforeFooter;
      const expectedFooterLabel = helpers.footerLabelFromMenuText(target.text);
      const deadlineAfterClick = Date.now() + 3200;
      while (Date.now() < deadlineAfterClick) {{
        await sleep(140);
        resetHorizontalLayoutScroll();
        trigger = getTrigger() || trigger;
        afterFooter = trigger?.state || helpers.readIntelligenceTrigger(trigger?.button);
        if (helpers.footerConfirmsMenuModel(target.text, afterFooter)) break;
      }}
      if (!helpers.footerConfirmsMenuModel(target.text, afterFooter)) {{
        return {{
          ok: false,
          reason: '已点击目标模型，但 Codex 页脚没有确认切换成功',
          targetDisplayName,
          clickedText: target.text,
          expectedFooterLabel,
          footerText: afterFooter.footerText,
          afterText: afterFooter.footerText,
          modelDisplayName: afterFooter.modelLabel,
          beforeModelDisplayName: beforeFooter.modelLabel,
          submenuText: normalize(submenuTrigger.textContent || ''),
        }};
      }}
      let restoredReasoning = null;
      const reasoningAfterModelClick = afterFooter.reasoningLabel;
      if (reasoningBefore && reasoningAfterModelClick && reasoningAfterModelClick !== reasoningBefore) {{
        trigger = getTrigger() || trigger;
        domClick(trigger.button);
        await sleep(260);
        const reasoningTarget = [...document.querySelectorAll('[role="menuitem"]')]
          .filter(visible)
          .map(item => ({{ item, text: normalize(item.textContent || '') }}))
          .find(entry => entry.text === reasoningBefore);
        if (reasoningTarget) {{
          domClick(reasoningTarget.item);
          restoredReasoning = {{ from: reasoningAfterModelClick, to: reasoningBefore, clickedText: reasoningTarget.text }};
        }} else {{
          restoredReasoning = {{ from: reasoningAfterModelClick, to: reasoningBefore, reason: '找不到原推理档位菜单项' }};
        }}
      }}
      return {{
        ok: true,
        targetDisplayName,
        clickedText: target.text,
        alreadySelected: target.selected,
        expectedFooterLabel,
        footerText: afterFooter.footerText,
        afterText: afterFooter.footerText,
        modelDisplayName: afterFooter.modelLabel,
        restoredReasoning,
        submenuText: normalize(submenuTrigger.textContent || ''),
      }};
    }})()"""


def switch_reasoning_expression(target_display_name: str) -> str:
    return f"""(async () => {{
      const targetDisplayName = {js_literal(target_display_name)};
      const visible = {visible_helper_source()};
      const domClick = {dom_click_helper_source()};
      const normalize = text => String(text || '').replace(/\\s+/g, ' ').trim();
      const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));
      const reasoningFromFooterText = text => {{
        const parts = normalize(text).split(' ').filter(Boolean);
        const last = parts[parts.length - 1] || '';
        return ['极低', '低', '中', '高', '超高'].includes(last) ? last : '';
      }};
      const trigger = [...document.querySelectorAll('button[data-codex-intelligence-trigger]')]
        .filter(visible)
        .map(button => ({{ button, rect: button.getBoundingClientRect(), text: normalize(button.innerText) }}))
        .filter(item => item.rect.x > 300 && item.rect.y > window.innerHeight * 0.55)
        .sort((a, b) => b.rect.y - a.rect.y || b.rect.x - a.rect.x)[0];
      if (!trigger) return {{ ok: false, reason: '找不到模型/推理菜单按钮' }};

      domClick(trigger.button);
      await sleep(260);

      const reasoningItems = [...document.querySelectorAll('[role="menuitem"]')]
        .filter(visible)
        .map(item => ({{ item, text: normalize(item.innerText), selected: item.getAttribute('data-reasoning-selected') === 'true' }}))
        .filter(entry => ['低', '中', '高', '超高'].includes(entry.text));
      const target = reasoningItems.find(entry => entry.text === targetDisplayName);
      if (!target) return {{ ok: false, reason: '找不到目标推理模式菜单项', targetDisplayName, items: reasoningItems.map(entry => entry.text) }};
      domClick(target.item);
      let triggerAfter = null;
      const deadline = Date.now() + 1800;
      while (Date.now() < deadline) {{
        await sleep(140);
        triggerAfter = [...document.querySelectorAll('button[data-codex-intelligence-trigger]')]
          .filter(visible)
          .map(button => ({{ text: normalize(button.innerText), effort: button.getAttribute('data-selected-reasoning-effort') }}))
          .find(item => reasoningFromFooterText(item.text) === targetDisplayName || item.effort);
        if (triggerAfter && reasoningFromFooterText(triggerAfter.text) === targetDisplayName) break;
      }}
      if (!triggerAfter || reasoningFromFooterText(triggerAfter.text) !== targetDisplayName) {{
        return {{ ok: false, reason: '已点击目标推理模式，但 Codex 页脚没有确认切换成功', targetDisplayName, clickedText: target.text, triggerText: triggerAfter?.text || '', selectedReasoningEffort: triggerAfter?.effort || '' }};
      }}
      return {{ ok: true, targetDisplayName, clickedText: target.text, alreadySelected: target.selected, triggerText: triggerAfter?.text || '', selectedReasoningEffort: triggerAfter?.effort || '' }};
    }})()"""


def thread_action_expression(command: str, action_label: str, name: str = "") -> str:
    return f"""(async () => {{
      const command = {js_literal(command)};
      const actionLabel = {js_literal(action_label)};
      const newName = {js_literal(name)};
      const visible = {visible_helper_source()};
      const domClick = {dom_click_helper_source()};
      const normalize = text => String(text || '').replace(/\\s+/g, ' ').trim();
      const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));
      const menuButton = [...document.querySelectorAll('button[aria-label="对话操作"]')]
        .filter(visible)
        .map(button => ({{ button, rect: button.getBoundingClientRect() }}))
        .filter(item => item.rect.x > 300 && item.rect.y < 80)
        .sort((a, b) => a.rect.x - b.rect.x)[0]?.button;
      if (!menuButton) return {{ ok: false, reason: '找不到顶部“对话操作”按钮' }};

      const findActionItem = () => {{
        const items = [...document.querySelectorAll('[role="menuitem"]')].filter(visible);
        let item = items.find(entry => normalize(entry.innerText).startsWith(actionLabel));
        if (!item && command === 'pin' && actionLabel === '取消置顶对话') {{
          item = items.find(entry => /^取消置顶/.test(normalize(entry.innerText)));
        }}
        if (!item && command === 'pin' && actionLabel === '置顶对话') {{
          item = items.find(entry => /^置顶/.test(normalize(entry.innerText)));
        }}
        return {{ item, items }};
      }};

      let {{ item: actionItem, items: menuItems }} = findActionItem();
      if (!actionItem) {{
        domClick(menuButton);
        await sleep(220);
        ({{ item: actionItem, items: menuItems }} = findActionItem());
      }}
      if (!actionItem) {{
        return {{ ok: false, reason: '找不到' + actionLabel + '菜单项', items: menuItems.map(item => normalize(item.innerText)).filter(Boolean).slice(0, 30) }};
      }}
      const rect = actionItem.getBoundingClientRect();
      domClick(actionItem);
      await sleep(260);

      if (command === 'rename') {{
        const input = [...document.querySelectorAll('input[aria-label="对话标题"],input,textarea')]
          .filter(visible)
          .find(item => item.closest('[role="dialog"]') || item.getAttribute('aria-label') === '对话标题');
        if (!input) return {{ ok: false, reason: '找不到重命名对话标题输入框' }};
        input.focus();
        const valueSetter = Object.getOwnPropertyDescriptor(input.constructor.prototype, 'value')?.set;
        if (valueSetter) valueSetter.call(input, newName);
        else input.value = newName;
        input.dispatchEvent(new InputEvent('input', {{ bubbles: true, data: newName, inputType: 'insertText' }}));
        input.dispatchEvent(new Event('change', {{ bubbles: true }}));
        await sleep(80);
        const saveButton = [...document.querySelectorAll('button')]
          .filter(visible)
          .find(button => normalize(button.innerText) === '保存' && (button.closest('[role="dialog"]') || button.type === 'submit'));
        if (!saveButton) return {{ ok: false, reason: '找不到重命名保存按钮' }};
        domClick(saveButton);
        await sleep(360);
        return {{ ok: true, command, text: normalize(actionItem.innerText), name: newName, rect: {{ x: rect.x, y: rect.y, w: rect.width, h: rect.height }} }};
      }}
      return {{ ok: true, command, actionLabel, text: normalize(actionItem.innerText), rect: {{ x: rect.x, y: rect.y, w: rect.width, h: rect.height }} }};
    }})()"""
