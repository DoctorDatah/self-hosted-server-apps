(function () {
  var reloadScheduled = false;
  var VERSION_KEY = 'vm_management_seen_realtime_version';
  var NAV_COLLAPSED_KEY = 'vm_management_nav_collapsed';
  var MACHINES_GROUP_BY_KEY = 'vm_management_machines_group_by';

  function qs(sel, root) {
    return (root || document).querySelector(sel);
  }

  function getSeenVersion() {
    try {
      var raw = window.sessionStorage.getItem(VERSION_KEY);
      var parsed = parseInt(raw || '-1', 10);
      return Number.isFinite(parsed) ? parsed : -1;
    } catch (_err) {
      return -1;
    }
  }

  function setSeenVersion(version) {
    var value = parseInt(String(version), 10);
    if (!Number.isFinite(value)) return;
    try {
      window.sessionStorage.setItem(VERSION_KEY, String(value));
    } catch (_err) {
      // Ignore session storage failures.
    }
  }

  function getNavCollapsed() {
    try {
      return window.localStorage.getItem(NAV_COLLAPSED_KEY) === '1';
    } catch (_err) {
      return false;
    }
  }

  function setNavCollapsed(collapsed) {
    try {
      window.localStorage.setItem(NAV_COLLAPSED_KEY, collapsed ? '1' : '0');
    } catch (_err) {
      // Ignore local storage failures.
    }
  }

  function applyNavCollapsed(collapsed) {
    var shell = qs('.app-shell');
    if (shell) {
      shell.classList.toggle('nav-collapsed', !!collapsed);
    }

    var btn = qs('#nav-toggle-btn');
    if (!btn) return;
    var expandedLabel = btn.getAttribute('data-expanded-label') || 'Hide Menu';
    var collapsedLabel = btn.getAttribute('data-collapsed-label') || 'Show Menu';
    btn.textContent = collapsed ? collapsedLabel : expandedLabel;
    btn.setAttribute('aria-expanded', collapsed ? 'false' : 'true');
  }

  function bindNavToggle() {
    var btn = qs('#nav-toggle-btn');
    if (!btn || btn.__boundNavToggle) return;
    btn.__boundNavToggle = true;
    btn.addEventListener('click', function () {
      var next = !getNavCollapsed();
      setNavCollapsed(next);
      applyNavCollapsed(next);
    });
  }

  function markReloadScheduled() {
    reloadScheduled = true;
  }

  function softReload() {
    if (reloadScheduled) return;
    markReloadScheduled();
    window.setTimeout(function () {
      window.location.reload();
    }, 700);
  }

  function qsa(sel, root) {
    return Array.from((root || document).querySelectorAll(sel));
  }

  function asHtml(text) {
    return String(text || '').replace(/[&<>"']/g, function (ch) {
      return {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#39;'
      }[ch] || ch;
    });
  }

  function openDrawer(title) {
    var drawer = qs('#drawer');
    if (!drawer) return;
    drawer.classList.add('open');
    drawer.setAttribute('aria-hidden', 'false');
    if (document && document.body) {
      document.body.classList.add('drawer-open');
    }
    if (title) {
      var t = qs('#drawer-title');
      if (t) t.textContent = title;
    }
  }

  function closeDrawer() {
    var drawer = qs('#drawer');
    if (!drawer) return;
    drawer.classList.remove('open');
    drawer.setAttribute('aria-hidden', 'true');
    if (document && document.body) {
      document.body.classList.remove('drawer-open');
    }
  }

  function openIntegrityModal() {
    var modal = qs('#integrity-modal');
    if (!modal) return;
    modal.classList.add('open');
    modal.setAttribute('aria-hidden', 'false');
    if (document && document.body) {
      document.body.classList.add('drawer-open');
    }
  }

  function closeIntegrityModal() {
    var modal = qs('#integrity-modal');
    if (!modal) return;
    modal.classList.remove('open');
    modal.setAttribute('aria-hidden', 'true');
    if (document && document.body) {
      if (!(qs('#drawer') && qs('#drawer').classList.contains('open'))) {
        document.body.classList.remove('drawer-open');
      }
    }
  }

  function setFlash(message, type) {
    var flash = qs('#flash-area');
    if (!flash) return;
    flash.innerHTML = '<div class="flash ' + (type || 'success') + '">' + asHtml(message) + '</div>';
  }

  function updateSetupCsv(container) {
    qsa('[data-setup-checks="true"]', container).forEach(function (group) {
      var form = group.closest('form');
      if (!form) return;
      var hidden = qs('input[data-setup-csv="true"]', form);
      if (!hidden) return;
      var values = qsa('input[type="checkbox"]', group)
        .filter(function (el) { return el.checked; })
        .map(function (el) { return el.value; });
      hidden.value = values.join(',');
    });
  }

  function bindSetupCheckboxes(root) {
    qsa('[data-setup-checks="true"] input[type="checkbox"]', root).forEach(function (input) {
      input.addEventListener('change', function () {
        updateSetupCsv(root);
      });
    });
    updateSetupCsv(root);
  }

  function parseCsvList(raw) {
    return String(raw || '')
      .split(',')
      .map(function (x) { return x.trim(); })
      .filter(Boolean);
  }

  function bindOperationSetBuilders(root) {
    qsa('[data-operation-sets="true"]', root).forEach(function (container) {
      if (container.__boundOperationSets) return;
      container.__boundOperationSets = true;

      var form = container.closest('form');
      if (!form) return;
      var hidden = qs('input[data-operation-sets-json="true"]', form);
      var rowsWrap = qs('[data-operation-set-rows="true"]', container);
      var template = qs('template[data-operation-set-template="true"]', container);
      var addBtn = qs('[data-opset-add="true"]', container);
      var catalogChips = qsa('[data-opset-catalog]', container);
      var activeSetupsInput = null;

      if (!rowsWrap || !hidden) return;

      function rows() {
        return qsa('[data-operation-set-row="true"]', rowsWrap);
      }

      function syncJson() {
        var payload = {};
        rows().forEach(function (row) {
          var nameInput = qs('[data-opset-name="true"]', row);
          var setupsInput = qs('[data-opset-setups="true"]', row);
          var descInput = qs('[data-opset-description="true"]', row);
          if (!nameInput || !setupsInput) return;

          var setName = String(nameInput.value || '').trim();
          if (!setName) return;
          var setups = parseCsvList(setupsInput.value);
          if (!setups.length) return;

          var entry = { setups: setups };
          if (descInput && String(descInput.value || '').trim()) {
            entry.description = String(descInput.value || '').trim();
          }
          payload[setName] = entry;
        });
        hidden.value = JSON.stringify(payload);
      }

      function appendSetupToActive(setupId) {
        if (!setupId) return;
        if (!activeSetupsInput) {
          var first = rows()[0];
          activeSetupsInput = first ? qs('[data-opset-setups="true"]', first) : null;
        }
        if (!activeSetupsInput) return;

        var items = parseCsvList(activeSetupsInput.value);
        items.push(setupId);
        activeSetupsInput.value = items.join(', ');
        activeSetupsInput.dispatchEvent(new Event('input', { bubbles: true }));
        activeSetupsInput.focus();
      }

      function bindRow(row) {
        if (!row || row.__boundOpSetRow) return;
        row.__boundOpSetRow = true;

        var nameInput = qs('[data-opset-name="true"]', row);
        var setupsInput = qs('[data-opset-setups="true"]', row);
        var descInput = qs('[data-opset-description="true"]', row);
        var removeBtn = qs('[data-opset-remove="true"]', row);
        [nameInput, setupsInput, descInput].forEach(function (el) {
          if (!el) return;
          el.addEventListener('input', syncJson);
        });
        if (setupsInput) {
          setupsInput.addEventListener('focus', function () {
            activeSetupsInput = setupsInput;
          });
        }
        if (removeBtn) {
          removeBtn.addEventListener('click', function () {
            row.remove();
            if (activeSetupsInput === setupsInput) {
              activeSetupsInput = null;
            }
            syncJson();
          });
        }
      }

      rows().forEach(bindRow);

      if (addBtn && template) {
        addBtn.addEventListener('click', function () {
          var fragment = template.content.cloneNode(true);
          rowsWrap.appendChild(fragment);
          var allRows = rows();
          var lastRow = allRows[allRows.length - 1];
          bindRow(lastRow);
          var setupsInput = lastRow ? qs('[data-opset-setups="true"]', lastRow) : null;
          if (setupsInput) {
            activeSetupsInput = setupsInput;
          }
          syncJson();
        });
      }

      catalogChips.forEach(function (chip) {
        chip.addEventListener('click', function () {
          appendSetupToActive(chip.getAttribute('data-opset-catalog') || '');
        });
      });

      syncJson();
    });
  }

  function bindTableFilters(root) {
    qsa('.table-filter', root).forEach(function (input) {
      var targetSelector = input.getAttribute('data-filter-target');
      var table = targetSelector ? qs(targetSelector) : null;
      if (!table) return;

      input.addEventListener('input', function () {
        var term = input.value.trim().toLowerCase();
        var dataRows = qsa('tbody tr[data-machine-row="true"]', table);
        var rows = dataRows.length
          ? dataRows
          : qsa('tbody tr', table).filter(function (row) {
              return row.getAttribute('data-group-header') !== 'true';
            });
        rows.forEach(function (row) {
          var text = row.textContent.toLowerCase();
          row.style.display = !term || text.indexOf(term) !== -1 ? '' : 'none';
        });
        updateGroupHeaderVisibility(table);
      });
    });
  }

  function getMachinesGroupBy() {
    try {
      return window.localStorage.getItem(MACHINES_GROUP_BY_KEY) || 'none';
    } catch (_err) {
      return 'none';
    }
  }

  function setMachinesGroupBy(value) {
    try {
      window.localStorage.setItem(MACHINES_GROUP_BY_KEY, value || 'none');
    } catch (_err) {
      // Ignore local storage failures.
    }
  }

  function clearGroupHeaders(table) {
    qsa('tbody tr[data-group-header="true"]', table).forEach(function (row) {
      row.remove();
    });
  }

  function updateGroupHeaderVisibility(table) {
    var headers = qsa('tbody tr[data-group-header="true"]', table);
    if (!headers.length) return;

    headers.forEach(function (header) {
      var next = header.nextElementSibling;
      var hasVisibleRows = false;
      while (next && next.getAttribute('data-group-header') !== 'true') {
        if (next.getAttribute('data-machine-row') === 'true' && next.style.display !== 'none') {
          hasVisibleRows = true;
          break;
        }
        next = next.nextElementSibling;
      }
      header.style.display = hasVisibleRows ? '' : 'none';
    });
  }

  function insertGroupHeaders(table, groupKey) {
    clearGroupHeaders(table);
    if (!groupKey || groupKey === 'none') {
      return;
    }

    var tbody = qs('tbody', table);
    if (!tbody) return;
    var rows = qsa('tr[data-machine-row="true"]', tbody);
    if (!rows.length) return;

    var thCount = qsa('thead th', table).length || 1;
    var lastGroup = null;
    rows.forEach(function (row) {
      var groupValue = (row.getAttribute('data-group-' + groupKey) || '-').trim() || '-';
      if (groupValue !== lastGroup) {
        lastGroup = groupValue;
        var headerRow = document.createElement('tr');
        headerRow.className = 'group-header-row';
        headerRow.setAttribute('data-group-header', 'true');
        var td = document.createElement('td');
        td.colSpan = thCount;
        td.textContent = groupKey.replace('_', ' ') + ': ' + groupValue;
        headerRow.appendChild(td);
        tbody.insertBefore(headerRow, row);
      }
    });
    updateGroupHeaderVisibility(table);
  }

  function applyMachinesGrouping(table, groupKey) {
    var tbody = qs('tbody', table);
    if (!tbody) return;
    var rows = qsa('tr[data-machine-row="true"]', tbody);
    if (!rows.length) return;

    rows.sort(function (a, b) {
      var aMachine = (a.getAttribute('data-machine-id') || '').toLowerCase();
      var bMachine = (b.getAttribute('data-machine-id') || '').toLowerCase();
      if (!groupKey || groupKey === 'none') {
        return aMachine.localeCompare(bMachine);
      }
      var aGroup = (a.getAttribute('data-group-' + groupKey) || '').toLowerCase();
      var bGroup = (b.getAttribute('data-group-' + groupKey) || '').toLowerCase();
      var groupCmp = aGroup.localeCompare(bGroup);
      return groupCmp !== 0 ? groupCmp : aMachine.localeCompare(bMachine);
    });

    rows.forEach(function (row) {
      tbody.appendChild(row);
    });
    insertGroupHeaders(table, groupKey);
  }

  function bindMachinesGrouping(root) {
    qsa('select[data-group-target]', root).forEach(function (select) {
      if (select.__boundGroupBy) return;
      select.__boundGroupBy = true;
      var targetSelector = select.getAttribute('data-group-target');
      var table = targetSelector ? qs(targetSelector) : null;
      if (!table) return;

      var selected = getMachinesGroupBy();
      if (!selected || !qsa('option', select).some(function (opt) { return opt.value === selected; })) {
        selected = 'none';
      }
      select.value = selected;
      applyMachinesGrouping(table, selected);

      select.addEventListener('change', function () {
        var value = String(select.value || 'none');
        setMachinesGroupBy(value);
        applyMachinesGrouping(table, value);

        // Reapply active filter term to keep grouped headers aligned with visible rows.
        var filter = qs('.table-filter[data-filter-target="' + targetSelector + '"]');
        if (filter) {
          filter.dispatchEvent(new Event('input', { bubbles: true }));
        }
      });
    });
  }

  function renderGitPrepareResult(result) {
    if (!result) return 'No response received.';
    var lines = [];
    lines.push('Branch: ' + result.branch);
    lines.push('Commit: ' + result.commit_sha);
    lines.push('Files:');
    (result.changed_files || []).forEach(function (f) {
      lines.push('  - ' + f);
    });
    lines.push('Next commands:');
    (result.next_commands || []).forEach(function (c) {
      lines.push('  ' + c);
    });
    return '<pre>' + asHtml(lines.join('\n')) + '</pre>';
  }

  function getErrorMessage(data, fallback) {
    if (!data) return fallback;
    if (typeof data.detail === 'string') return data.detail;
    if (data.detail && data.detail.error && data.detail.error.message) return data.detail.error.message;
    if (data.error && data.error.message) return data.error.message;
    return fallback;
  }

  async function postJson(url, payload) {
    var res = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    var data = null;
    try {
      data = await res.json();
    } catch (_err) {
      data = null;
    }

    if (!res.ok) {
      throw new Error(getErrorMessage(data, 'Request failed: ' + url));
    }
    return data;
  }

  function renderDependencies(report) {
    var dependents = report.direct_dependents || [];
    if (!dependents.length) {
      return '<p>No dependent entities found.</p>';
    }

    var rows = dependents.map(function (d) {
      return '<li><code>' + asHtml(d.entity_type + ':' + d.entity_id) + '</code></li>';
    }).join('');

    return '<p>Direct dependents:</p><ul class="simple-list">' + rows + '</ul>';
  }

  function renderDiffs(diffs) {
    var keys = Object.keys(diffs || {});
    if (!keys.length) {
      return '<p class="muted">No file diffs generated yet.</p>';
    }

    return keys.map(function (path) {
      return '<details class="details-block"><summary>' + asHtml(path) + '</summary><pre class="diff-view">' + asHtml(diffs[path]) + '</pre></details>';
    }).join('');
  }

  function renderIntegrityModal(preview, entityType, entityId) {
    var report = preview.report || {};
    var blockers = report.blockers || [];
    var warnings = report.warnings || [];
    var changedFiles = preview.changed_files || [];

    var warningHtml = warnings.length
      ? '<div class="flash warn"><strong>Warnings:</strong><ul class="simple-list">' + warnings.map(function (w) { return '<li>' + asHtml(w) + '</li>'; }).join('') + '</ul></div>'
      : '';

    var blockerHtml = blockers.length
      ? '<div class="flash error"><strong>Blockers:</strong><ul class="simple-list">' + blockers.map(function (b) { return '<li>' + asHtml(b.message || b.code || 'blocked') + '</li>'; }).join('') + '</ul></div>'
      : '<div class="flash success">No blockers detected.</div>';

    var filesHtml = changedFiles.length
      ? '<p>Affected files: ' + changedFiles.map(function (f) { return '<code>' + asHtml(f) + '</code>'; }).join(', ') + '</p>'
      : '<p>Affected files will be computed after cascade preview.</p>';

    var confirmLabel = blockers.length ? 'Confirm Cascade Delete' : 'Confirm Delete';

    var body = [
      '<p>You are deleting <code>' + asHtml(entityType + ':' + entityId) + '</code>.</p>',
      warningHtml,
      blockerHtml,
      renderDependencies(report),
      filesHtml,
      renderDiffs(preview.diffs || {}),
      '<div class="actions-row">',
      '<button class="btn danger" type="button" id="integrity-confirm-btn">' + confirmLabel + '</button>',
      '<button class="btn ghost" type="button" data-close-integrity="true">Cancel</button>',
      '</div>'
    ].join('');

    var container = qs('#integrity-body');
    if (container) {
      container.innerHTML = body;
      var confirmBtn = qs('#integrity-confirm-btn', container);
      if (confirmBtn) {
        confirmBtn.addEventListener('click', function () {
          applyDelete(entityType, entityId, blockers.length > 0);
        });
      }
    }
    openIntegrityModal();
  }

  async function previewDelete(entityType, entityId) {
    var data = await postJson('/api/config/integrity/delete-preview', {
      entity_type: entityType,
      entity_id: entityId,
      cascade: false
    });
    renderIntegrityModal(data, entityType, entityId);
  }

  async function applyDelete(entityType, entityId, useCascade) {
    try {
      var result = await postJson('/api/config/integrity/delete-apply', {
        entity_type: entityType,
        entity_id: entityId,
        cascade: !!useCascade,
        confirm: true
      });
      closeIntegrityModal();
      setFlash('Delete applied successfully for ' + entityType + ':' + entityId, 'success');
      if (result && typeof result.realtime_version !== 'undefined') {
        setSeenVersion(result.realtime_version);
      }
      if ((result.changed_files || []).length) {
        if (!reloadScheduled) {
          markReloadScheduled();
          window.setTimeout(function () {
            window.location.reload();
          }, 300);
        }
      }
    } catch (err) {
      setFlash(err.message, 'error');
    }
  }

  function bindDeleteButtons(root) {
    qsa('.delete-entity-btn', root).forEach(function (btn) {
      btn.addEventListener('click', function () {
        var entityType = btn.getAttribute('data-entity-type');
        var entityId = btn.getAttribute('data-entity-id');
        previewDelete(entityType, entityId).catch(function (err) {
          setFlash(err.message, 'error');
        });
      });
    });
  }

  function bindGitPrepareForm(root) {
    var form = qs('form[data-git-prepare="true"]', root);
    if (!form) return;

    form.addEventListener('submit', async function (e) {
      e.preventDefault();
      var resultNode = qs('#git-prepare-result');
      if (resultNode) {
        resultNode.innerHTML = 'Preparing commit...';
      }

      var payload = {
        branch_name: (form.branch_name && form.branch_name.value) || '',
        commit_message: (form.commit_message && form.commit_message.value) || ''
      };

      try {
        var data = await postJson('/api/git/prepare-commit', payload);
        if (resultNode) {
          resultNode.innerHTML = renderGitPrepareResult(data);
        }
      } catch (err) {
        if (resultNode) {
          resultNode.innerHTML = '<div class="flash error">' + asHtml(err.message) + '</div>';
        }
      }
    });
  }

  function bindGithubClipboardCode(root) {
    var btn = qs('#github-clipboard-code-btn', root || document);
    if (!btn || btn.__boundClipboardCode) return;
    btn.__boundClipboardCode = true;

    btn.addEventListener('click', async function () {
      var resultNode = qs('#github-connection-result');
      if (!resultNode) return;

      if (!navigator.clipboard || !navigator.clipboard.readText) {
        resultNode.innerHTML = '<div class="flash warn">Browser clipboard read is unavailable. Use "Server Fallback Code".</div>';
        return;
      }

      try {
        var clip = await navigator.clipboard.readText();
        var match = String(clip || '').toUpperCase().match(/\b[A-Z0-9]{4}-[A-Z0-9]{4}\b/);
        if (match && match[0]) {
          var code = match[0];
          resultNode.innerHTML = (
            '<div class="flash success">Device Code: <code style="font-size:1.1rem;">' + asHtml(code) + '</code>. ' +
            '<button type="button" class="btn ghost small" id="github-copy-device-code-btn">Copy Code</button></div>'
          );
          var copyBtn = qs('#github-copy-device-code-btn', resultNode);
          if (copyBtn) {
            copyBtn.addEventListener('click', function () {
              if (navigator.clipboard && navigator.clipboard.writeText) {
                navigator.clipboard.writeText(code);
              }
            });
          }
          return;
        }
        resultNode.innerHTML = '<div class="flash warn">No device code pattern found in clipboard. Click Connect To GitHub again and retry.</div>';
      } catch (_err) {
        resultNode.innerHTML = '<div class="flash warn">Clipboard permission denied. Allow clipboard access, then retry.</div>';
      }
    });
  }

  async function refreshTopStatus() {
    try {
      var res = await fetch('/api/status');
      if (!res.ok) throw new Error('status failed');
      var data = await res.json();
      var navMode = (document.body && document.body.getAttribute('data-nav-mode')) || 'home';
      var timezoneNode = qs('#pill-timezone');
      var statusText = qs('#top-status-text');
      if (timezoneNode) timezoneNode.textContent = 'Global Time Zone: ' + (data.app_timezone || 'UTC');
      if (statusText) {
        if (navMode === 'config') {
          statusText.textContent = 'Config Management workspace. Use each page tools for details, actions, and status.';
        } else {
          statusText.textContent = 'Global settings apply across all sections.';
        }
      }
    } catch (_err) {
      var statusText = qs('#top-status-text');
      if (statusText) statusText.textContent = 'Failed to load repo status.';
    }
  }

  function showRealtimeBanner(message, level) {
    var banner = qs('#realtime-banner');
    if (!banner) return;
    banner.classList.remove('hidden', 'success', 'error', 'warn');
    banner.classList.add(level || 'warn');
    banner.innerHTML = asHtml(message) + ' <button class="btn ghost small" type="button" id="realtime-refresh-btn">Reload</button>';
    var btn = qs('#realtime-refresh-btn', banner);
    if (btn) {
      btn.addEventListener('click', function () {
        window.location.reload();
      });
    }
  }

  function bindRealtime() {
    if (!window.EventSource) return;

    var source = new EventSource('/api/realtime/config-events');
    source.addEventListener('config_changed', function (ev) {
      if (reloadScheduled) {
        return;
      }

      var drawerOpen = qs('#drawer') && qs('#drawer').classList.contains('open');
      var integrityOpen = qs('#integrity-modal') && qs('#integrity-modal').classList.contains('open');
      var data = null;
      try {
        data = JSON.parse(ev.data || '{}');
      } catch (_err) {
        data = {};
      }

      var incomingVersion = parseInt(String((data && data.version) || -1), 10);
      if (Number.isFinite(incomingVersion)) {
        var seenVersion = getSeenVersion();
        if (incomingVersion <= seenVersion) {
          return;
        }
        setSeenVersion(incomingVersion);
      }

      if (drawerOpen || integrityOpen) {
        showRealtimeBanner('Configuration files changed while you are editing. Reload to avoid stale writes.', 'warn');
        return;
      }

      var files = (data && data.data && data.data.files) || [];
      if (!Array.isArray(files) || files.length === 0) {
        showRealtimeBanner('Configuration changed. Refreshing view...', 'warn');
      }
      softReload();
    });

    source.addEventListener('watch_error', function (ev) {
      var payload = null;
      try {
        payload = JSON.parse(ev.data || '{}');
      } catch (_err) {
        payload = {};
      }
      showRealtimeBanner('Realtime watch error: ' + ((payload.data && payload.data.error) || 'unknown'), 'error');
    });
  }

  function bindGlobalClicks() {
    document.addEventListener('click', function (event) {
      var openBtn = event.target.closest('[data-open-drawer="true"]');
      if (openBtn) {
        openDrawer(openBtn.getAttribute('data-drawer-title') || 'Editor');
      }

      var closeBtn = event.target.closest('[data-close-drawer="true"]');
      if (closeBtn) {
        closeDrawer();
      }

      var closeIntegrity = event.target.closest('[data-close-integrity="true"]');
      if (closeIntegrity) {
        closeIntegrityModal();
      }
    });
  }

  document.addEventListener('htmx:afterSwap', function (event) {
    if (event.target && event.target.id === 'drawer-body') {
      bindSetupCheckboxes(event.target);
      bindOperationSetBuilders(event.target);
      openDrawer();
    }
    bindGithubClipboardCode(document);
    bindMachinesGrouping(document);
  });

  document.addEventListener('DOMContentLoaded', function () {
    applyNavCollapsed(getNavCollapsed());
    bindNavToggle();
    bindGlobalClicks();
    bindTableFilters(document);
    bindMachinesGrouping(document);
    bindSetupCheckboxes(document);
    bindOperationSetBuilders(document);
    bindDeleteButtons(document);
    bindGitPrepareForm(document);
    bindGithubClipboardCode(document);
    bindRealtime();
    refreshTopStatus();
  });
})();
