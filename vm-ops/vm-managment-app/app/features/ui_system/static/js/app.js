(function () {
  var reloadScheduled = false;
  var VERSION_KEY = 'vm_management_seen_realtime_version';
  var NAV_COLLAPSED_KEY = 'vm_management_nav_collapsed';
  var MACHINES_GROUP_BY_KEY = 'vm_management_machines_group_by';
  var MACHINES_DENSITY_KEY = 'vm_management_machines_density';
  var MACHINES_DENSITY_MANUAL_KEY = 'vm_management_machines_density_manual';
  var POPUP_DEFAULT_MS = 4200;

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

  function ensurePopupStack() {
    var stack = qs('#popup-stack');
    if (stack) return stack;
    if (!document || !document.body) return null;
    stack = document.createElement('div');
    stack.id = 'popup-stack';
    stack.className = 'popup-stack';
    stack.setAttribute('aria-live', 'polite');
    document.body.appendChild(stack);
    return stack;
  }

  function showPopup(message, type, options) {
    var text = String(message || '').trim();
    if (!text) return;
    var stack = ensurePopupStack();
    if (!stack) return;
    var popup = document.createElement('div');
    popup.className = 'popup-item ' + (type || 'success');
    popup.innerHTML = '<span class="popup-message">' + asHtml(text) + '</span>';
    var closeBtn = document.createElement('button');
    closeBtn.type = 'button';
    closeBtn.className = 'popup-close';
    closeBtn.textContent = 'x';
    closeBtn.setAttribute('aria-label', 'Dismiss popup');
    closeBtn.addEventListener('click', function () {
      popup.remove();
    });
    popup.appendChild(closeBtn);
    stack.appendChild(popup);

    var opts = options || {};
    var sticky = !!opts.sticky;
    if (!sticky) {
      var timeoutMs = Number(opts.autoDismissMs);
      if (!Number.isFinite(timeoutMs) || timeoutMs <= 0) timeoutMs = POPUP_DEFAULT_MS;
      window.setTimeout(function () {
        popup.classList.add('closing');
        window.setTimeout(function () {
          popup.remove();
        }, 180);
      }, timeoutMs);
    }
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

  function setFlash(message, type, options) {
    var flash = qs('#flash-area');
    if (!flash) return;
    var t = type || 'success';
    flash.innerHTML = '<div class="flash ' + t + '">' + asHtml(message) + '</div>';
    var opts = options || {};
    if (opts.popup !== false) {
      showPopup(message, t, opts);
    }
  }

  function isMutationVerb(verb) {
    var v = String(verb || '').toUpperCase();
    return v === 'POST' || v === 'PUT' || v === 'PATCH' || v === 'DELETE';
  }

  function shouldSkipAutoConfirmPath(path) {
    var p = String(path || '').toLowerCase();
    return p.indexOf('/preview') !== -1 || p.indexOf('/render') !== -1 || p.indexOf('/api/status') !== -1;
  }

  function getRequestVerbFromElement(elt) {
    if (!elt) return 'GET';
    if (elt.getAttribute) {
      if (elt.getAttribute('hx-post')) return 'POST';
      if (elt.getAttribute('hx-put')) return 'PUT';
      if (elt.getAttribute('hx-patch')) return 'PATCH';
      if (elt.getAttribute('hx-delete')) return 'DELETE';
      if (elt.tagName && String(elt.tagName).toLowerCase() === 'form') {
        return String(elt.getAttribute('method') || 'GET').toUpperCase();
      }
    }
    var form = elt.closest ? elt.closest('form') : null;
    if (form) return String(form.getAttribute('method') || 'GET').toUpperCase();
    return 'GET';
  }

  function getRequestPathFromElement(elt) {
    if (!elt || !elt.getAttribute) return '';
    return (
      elt.getAttribute('hx-post') ||
      elt.getAttribute('hx-put') ||
      elt.getAttribute('hx-patch') ||
      elt.getAttribute('hx-delete') ||
      elt.getAttribute('hx-get') ||
      elt.getAttribute('action') ||
      ''
    );
  }

  function getActionLabel(elt) {
    if (!elt) return 'this action';
    if (elt.getAttribute && elt.getAttribute('data-action-label')) {
      return String(elt.getAttribute('data-action-label')).trim() || 'this action';
    }
    var fromText = String(elt.textContent || '').replace(/\s+/g, ' ').trim();
    if (fromText) return fromText;
    return 'this action';
  }

  function shouldConfirmRequest(elt, verb, path) {
    if (!isMutationVerb(verb)) return false;
    if (!elt) return false;
    if (elt.getAttribute && String(elt.getAttribute('data-no-confirm') || '').toLowerCase() === 'true') {
      return false;
    }
    if (elt.closest && elt.closest('[data-no-confirm="true"]')) {
      return false;
    }
    if (elt.getAttribute && elt.getAttribute('data-confirm-message')) {
      return true;
    }
    if (shouldSkipAutoConfirmPath(path)) return false;
    return true;
  }

  function getConfirmMessage(elt, verb, path) {
    if (elt && elt.getAttribute) {
      var explicit = elt.getAttribute('data-confirm-message');
      if (explicit) return explicit;
    }
    var label = getActionLabel(elt);
    var p = String(path || '').trim();
    if (p) {
      return label + ' will call ' + p + '. Continue?';
    }
    return 'This will run ' + label + '. Continue?';
  }

  function requestMetaFromEvent(event) {
    var detail = (event && event.detail) || {};
    var elt = detail.elt || null;
    var config = detail.requestConfig || {};
    var verb = String(config.verb || getRequestVerbFromElement(elt) || 'GET').toUpperCase();
    var path = String(config.path || getRequestPathFromElement(elt) || '');
    return {
      elt: elt,
      verb: verb,
      path: path
    };
  }

  function getSuccessMessage(meta) {
    var elt = meta.elt;
    if (elt && elt.getAttribute) {
      var explicit = elt.getAttribute('data-success-message');
      if (explicit) return explicit;
    }
    return getActionLabel(elt) + ' completed successfully.';
  }

  function getFailureMessage(meta, xhr) {
    var base = getActionLabel(meta.elt) + ' failed.';
    if (!xhr) return base;
    var status = Number(xhr.status || 0);
    var body = String(xhr.responseText || '').trim();
    if (!body) return base + ' HTTP ' + status + '.';
    try {
      var parsed = JSON.parse(body);
      if (parsed && typeof parsed.detail === 'string') return parsed.detail;
      if (parsed && parsed.error && parsed.error.message) return parsed.error.message;
    } catch (_err) {
      // Ignore non-JSON body.
    }
    if (status > 0) return base + ' HTTP ' + status + '.';
    return base;
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

  function bindChecklistBulkActions(root) {
    qsa('[data-checklist-bulk]', root).forEach(function (btn) {
      if (btn.__boundChecklistBulk) return;
      btn.__boundChecklistBulk = true;
      btn.addEventListener('click', function () {
        var action = String(btn.getAttribute('data-checklist-bulk') || '');
        var form = btn.closest('form');
        if (!form) return;
        var group = qs('[data-setup-checks="true"]', form);
        if (!group) return;
        var checkboxes = qsa('input[type="checkbox"]', group);
        var shouldCheck = action === 'select-all';
        checkboxes.forEach(function (cb) {
          cb.checked = shouldCheck;
        });
        updateSetupCsv(form);
      });
    });
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

      function getEnabledSetupValues() {
        var hiddenEnabled = qs('input[name="enabled_setups_csv"][data-setup-csv="true"]', form);
        var fromHidden = hiddenEnabled ? parseCsvList(hiddenEnabled.value) : [];
        if (fromHidden.length) return fromHidden;
        var enabledGroup = qs('[data-setup-checks="true"]', form);
        if (!enabledGroup) return [];
        return qsa('input[type="checkbox"]', enabledGroup)
          .filter(function (el) { return el.checked; })
          .map(function (el) { return el.value; });
      }

      function refreshCatalogAvailability() {
        var allowed = new Set(getEnabledSetupValues());
        catalogChips.forEach(function (chip) {
          var sid = String(chip.getAttribute('data-opset-catalog') || '').trim();
          var isAllowed = sid && allowed.has(sid);
          chip.disabled = !isAllowed;
          chip.title = isAllowed ? '' : 'Enable this setup first in Enabled Setups';
        });
      }

      function syncJson() {
        var allowed = new Set(getEnabledSetupValues());
        var payload = {};
        rows().forEach(function (row) {
          var nameInput = qs('[data-opset-name="true"]', row);
          var setupsInput = qs('[data-opset-setups="true"]', row);
          var descInput = qs('[data-opset-description="true"]', row);
          if (!nameInput || !setupsInput) return;

          var setName = String(nameInput.value || '').trim();
          if (!setName) return;
          var setups = parseCsvList(setupsInput.value).filter(function (sid) {
            return allowed.has(sid);
          });
          setupsInput.value = setups.join(', ');
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
        var allowed = new Set(getEnabledSetupValues());
        if (!allowed.has(setupId)) return;
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

      qsa('[data-setup-checks="true"] input[type="checkbox"]', form).forEach(function (input) {
        input.addEventListener('change', function () {
          refreshCatalogAvailability();
          syncJson();
        });
      });

      refreshCatalogAvailability();
      syncJson();
    });
  }

  function bindTableFilters(root) {
    qsa('.table-filter', root).forEach(function (input) {
      var targetSelector = input.getAttribute('data-filter-target');
      var table = targetSelector ? qs(targetSelector) : null;
      if (!table) return;

      input.addEventListener('input', function () {
        if (table.getAttribute('data-machine-table') === 'true') {
          applyMachineTableFilters(table);
          return;
        }

        var term = input.value.trim().toLowerCase();
        var rows = qsa('tbody tr', table).filter(function (row) {
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

  function getMachineFilterInput(table) {
    var tableId = table && table.id ? ('#' + table.id) : '';
    if (!tableId) return null;
    return qs('.table-filter[data-filter-target="' + tableId + '"]');
  }

  function getActiveQuickFilterValues(table) {
    var tableId = table && table.id ? ('#' + table.id) : '';
    if (!tableId) return [];
    return qsa('.quick-filter-chip.active[data-quick-filter-target="' + tableId + '"]').map(function (btn) {
      return {
        key: String(btn.getAttribute('data-filter-key') || ''),
        value: String(btn.getAttribute('data-filter-value') || '').toLowerCase()
      };
    });
  }

  function applyMachineTableFilters(table) {
    if (!table) return;
    var filterInput = getMachineFilterInput(table);
    var term = filterInput ? String(filterInput.value || '').trim().toLowerCase() : '';
    var quickFilters = getActiveQuickFilterValues(table);
    var rows = qsa('tbody tr[data-machine-row="true"]', table);

    rows.forEach(function (row) {
      var text = String(row.textContent || '').toLowerCase();
      var matchTerm = !term || text.indexOf(term) !== -1;
      var matchQuick = quickFilters.every(function (entry) {
        var rowValue = String(row.getAttribute('data-group-' + entry.key) || '').toLowerCase();
        return rowValue === entry.value;
      });
      var visible = matchTerm && matchQuick;
      row.style.display = visible ? '' : 'none';

      var machineId = String(row.getAttribute('data-machine-id') || '');
      var detailRow = qs('tbody tr[data-machine-detail-for="' + machineId + '"]', table);
      if (!detailRow) return;
      var expanded = detailRow.getAttribute('data-expanded') === 'true';
      detailRow.style.display = visible && expanded ? '' : 'none';
    });

    updateGroupHeaderVisibility(table);
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

  function getMachinesDensity() {
    try {
      return window.localStorage.getItem(MACHINES_DENSITY_KEY) || 'comfortable';
    } catch (_err) {
      return 'comfortable';
    }
  }

  function setMachinesDensity(value) {
    try {
      window.localStorage.setItem(MACHINES_DENSITY_KEY, value || 'comfortable');
    } catch (_err) {
      // Ignore local storage failures.
    }
  }

  function getMachinesDensityManual() {
    try {
      return window.localStorage.getItem(MACHINES_DENSITY_MANUAL_KEY) === '1';
    } catch (_err) {
      return false;
    }
  }

  function setMachinesDensityManual(isManual) {
    try {
      window.localStorage.setItem(MACHINES_DENSITY_MANUAL_KEY, isManual ? '1' : '0');
    } catch (_err) {
      // Ignore local storage failures.
    }
  }

  function autoMachinesDensityMode() {
    return window.innerWidth <= 1480 ? 'compact' : 'comfortable';
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

    var pairs = rows.map(function (row) {
      var machineId = String(row.getAttribute('data-machine-id') || '');
      return {
        row: row,
        detail: qs('tr[data-machine-detail-for="' + machineId + '"]', tbody)
      };
    });

    pairs.sort(function (a, b) {
      var aMachine = (a.row.getAttribute('data-machine-id') || '').toLowerCase();
      var bMachine = (b.row.getAttribute('data-machine-id') || '').toLowerCase();
      if (!groupKey || groupKey === 'none') {
        return aMachine.localeCompare(bMachine);
      }
      var aGroup = (a.row.getAttribute('data-group-' + groupKey) || '').toLowerCase();
      var bGroup = (b.row.getAttribute('data-group-' + groupKey) || '').toLowerCase();
      var groupCmp = aGroup.localeCompare(bGroup);
      return groupCmp !== 0 ? groupCmp : aMachine.localeCompare(bMachine);
    });

    pairs.forEach(function (pair) {
      tbody.appendChild(pair.row);
      if (pair.detail) {
        tbody.appendChild(pair.detail);
      }
    });
    insertGroupHeaders(table, groupKey);
    applyMachineTableFilters(table);
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

  function bindQuickFilters(root) {
    qsa('.quick-filter-chip[data-quick-filter-target]', root).forEach(function (btn) {
      if (btn.__boundQuickFilter) return;
      btn.__boundQuickFilter = true;
      btn.addEventListener('click', function () {
        btn.classList.toggle('active');
        var targetSelector = btn.getAttribute('data-quick-filter-target');
        var table = targetSelector ? qs(targetSelector) : null;
        if (table) applyMachineTableFilters(table);
      });
    });

    qsa('.quick-filter-chip[data-quick-filter-clear]', root).forEach(function (btn) {
      if (btn.__boundQuickFilterClear) return;
      btn.__boundQuickFilterClear = true;
      btn.addEventListener('click', function () {
        var targetSelector = btn.getAttribute('data-quick-filter-clear');
        var table = targetSelector ? qs(targetSelector) : null;
        if (!table) return;
        qsa('.quick-filter-chip.active[data-quick-filter-target="' + targetSelector + '"]', document).forEach(function (node) {
          node.classList.remove('active');
        });
        applyMachineTableFilters(table);
      });
    });
  }

  function applyMachinesDensity(table, mode) {
    if (!table) return;
    table.classList.toggle('table-density-compact', mode === 'compact');
    var targetSelector = table.id ? ('#' + table.id) : '';
    if (!targetSelector) return;
    qsa('[data-density-target="' + targetSelector + '"] [data-density-mode]').forEach(function (btn) {
      var selected = btn.getAttribute('data-density-mode') === mode;
      btn.classList.toggle('active', selected);
    });
  }

  function applyAutoMachinesDensity() {
    if (getMachinesDensityManual()) return;
    var mode = autoMachinesDensityMode();
    setMachinesDensity(mode);
    qsa('table[data-machine-table="true"]', document).forEach(function (table) {
      applyMachinesDensity(table, mode);
    });
  }

  function bindDensityToggles(root) {
    qsa('[data-density-target]', root).forEach(function (group) {
      var targetSelector = group.getAttribute('data-density-target');
      var table = targetSelector ? qs(targetSelector) : null;
      if (!table) return;

      var mode = getMachinesDensityManual() ? getMachinesDensity() : autoMachinesDensityMode();
      mode = mode === 'compact' ? 'compact' : 'comfortable';
      setMachinesDensity(mode);
      applyMachinesDensity(table, mode);

      qsa('[data-density-mode]', group).forEach(function (btn) {
        if (btn.__boundDensityToggle) return;
        btn.__boundDensityToggle = true;
        btn.addEventListener('click', function () {
          var selectedMode = String(btn.getAttribute('data-density-mode') || 'comfortable');
          setMachinesDensityManual(true);
          setMachinesDensity(selectedMode);
          applyMachinesDensity(table, selectedMode);
        });
      });
    });
  }

  function bindMachineRowExpanders(root) {
    qsa('[data-toggle-machine-detail]', root).forEach(function (btn) {
      if (btn.__boundMachineDetailToggle) return;
      btn.__boundMachineDetailToggle = true;
      btn.addEventListener('click', function () {
        var machineId = btn.getAttribute('data-toggle-machine-detail');
        if (!machineId) return;
        var detailRow = qs('tr[data-machine-detail-for="' + machineId + '"]', document);
        var mainRow = qs('tr[data-machine-row="true"][data-machine-id="' + machineId + '"]', document);
        if (!detailRow || !mainRow) return;
        if (mainRow.style.display === 'none') return;

        var expanded = detailRow.getAttribute('data-expanded') === 'true';
        var next = !expanded;
        detailRow.setAttribute('data-expanded', next ? 'true' : 'false');
        detailRow.style.display = next ? '' : 'none';

        qsa('[data-toggle-machine-detail="' + machineId + '"]', document).forEach(function (ctrl) {
          ctrl.setAttribute('aria-expanded', next ? 'true' : 'false');
          if (ctrl.classList.contains('row-expand-btn')) {
            ctrl.textContent = next ? '▾' : '▸';
          }
        });
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
      if (btn.__boundDeleteEntity) return;
      btn.__boundDeleteEntity = true;
      btn.addEventListener('click', function () {
        var entityType = btn.getAttribute('data-entity-type');
        var entityId = btn.getAttribute('data-entity-id');
        var ok = window.confirm('Analyze delete impact for ' + entityType + ':' + entityId + '?');
        if (!ok) {
          showPopup('Delete analysis cancelled.', 'warn');
          return;
        }
        previewDelete(entityType, entityId).catch(function (err) {
          setFlash(err.message, 'error');
        });
      });
    });
  }

  function bindGitPrepareForm(root) {
    var form = qs('form[data-git-prepare="true"]', root);
    if (!form || form.__boundGitPrepare) return;
    form.__boundGitPrepare = true;

    form.addEventListener('submit', async function (e) {
      e.preventDefault();
      var ok = window.confirm('Prepare branch + commit for config changes?');
      if (!ok) {
        showPopup('Prepare commit cancelled.', 'warn');
        return;
      }
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
        showPopup('Branch + commit prepared successfully.', 'success');
      } catch (err) {
        if (resultNode) {
          resultNode.innerHTML = '<div class="flash error">' + asHtml(err.message) + '</div>';
        }
        showPopup(err.message, 'error');
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
      var branchNode = qs('#pill-config-branch');
      var changeNode = qs('#pill-change-count');
      var validationNode = qs('#pill-validation-status');
      var backupNode = qs('#pill-backup-status');
      var prNode = qs('#pill-open-pr-count');
      var statusText = qs('#top-status-text');
      if (timezoneNode) timezoneNode.textContent = 'Global Time Zone: ' + (data.app_timezone || 'UTC');

      var configBranch = String(data.preferred_config_branch || data.branch || '-');
      var configChangeCount = Number.isFinite(Number(data.config_changed_count)) ? Number(data.config_changed_count) : 0;
      var validationErrors = Array.isArray(data.validation_errors) ? data.validation_errors.length : 0;
      var backupState = String((data.backup_status && data.backup_status.state) || '');
      var backupLabel = backupState === 'backed_up' || backupState === 'backed_up_restored'
        ? 'Up To Date'
        : 'Not Backed Up';
      var openPrCount = data.related_open_pr_count === null || typeof data.related_open_pr_count === 'undefined'
        ? '-'
        : String(data.related_open_pr_count);

      if (branchNode) branchNode.textContent = 'Config Branch: ' + configBranch;
      if (changeNode) changeNode.textContent = 'Change Count: ' + String(configChangeCount);
      if (validationNode) validationNode.textContent = 'Validation Status: ' + (validationErrors > 0 ? 'Errors' : 'OK');
      if (backupNode) backupNode.textContent = 'Backup Status: ' + backupLabel;
      if (prNode) prNode.textContent = 'Open PR Count: ' + openPrCount;

      [branchNode, changeNode, validationNode, backupNode, prNode].forEach(function (node) {
        if (!node) return;
        node.classList.remove('hidden', 'ok', 'warn');
      });
      if (changeNode && configChangeCount > 0) {
        changeNode.classList.add('warn');
      }
      if (validationNode) {
        validationNode.classList.add(validationErrors > 0 ? 'warn' : 'ok');
      }
      if (backupNode) {
        backupNode.classList.add(backupLabel === 'Up To Date' ? 'ok' : 'warn');
      }
      if (prNode && openPrCount !== '-' && Number(openPrCount) > 0) {
        prNode.classList.add('ok');
      }

      if (statusText) {
        if (navMode === 'config') {
          statusText.textContent = 'Config Management workspace. Top labels show live config branch, change, validation, backup, and PR state.';
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

  function bindHtmxGlobalConfirmAndResult() {
    document.addEventListener('htmx:beforeRequest', function (event) {
      var meta = requestMetaFromEvent(event);
      if (!shouldConfirmRequest(meta.elt, meta.verb, meta.path)) return;
      var ok = window.confirm(getConfirmMessage(meta.elt, meta.verb, meta.path));
      if (!ok) {
        event.preventDefault();
        showPopup('Action cancelled.', 'warn');
      }
    });

    document.addEventListener('htmx:afterRequest', function (event) {
      var meta = requestMetaFromEvent(event);
      if (!isMutationVerb(meta.verb) || shouldSkipAutoConfirmPath(meta.path)) return;
      var xhr = event && event.detail ? event.detail.xhr : null;
      if (!xhr) return;
      var status = Number(xhr.status || 0);
      if (status >= 200 && status < 300) {
        showPopup(getSuccessMessage(meta), 'success');
      }
    });

    document.addEventListener('htmx:responseError', function (event) {
      var meta = requestMetaFromEvent(event);
      var xhr = event && event.detail ? event.detail.xhr : null;
      showPopup(getFailureMessage(meta, xhr), 'error', { sticky: true });
    });

    document.addEventListener('htmx:sendError', function (_event) {
      showPopup('Request failed to send. Check network/server and retry.', 'error', { sticky: true });
    });

    document.addEventListener('htmx:timeout', function (_event) {
      showPopup('Request timed out. Please retry.', 'error', { sticky: true });
    });
  }

  document.addEventListener('htmx:afterSwap', function (event) {
    if (event.target && event.target.id === 'drawer-body') {
      bindSetupCheckboxes(event.target);
      bindChecklistBulkActions(event.target);
      bindOperationSetBuilders(event.target);
      openDrawer();
    }
    bindDeleteButtons(document);
    bindGithubClipboardCode(document);
    bindMachinesGrouping(document);
    bindQuickFilters(document);
    bindDensityToggles(document);
    bindMachineRowExpanders(document);
  });

  document.addEventListener('DOMContentLoaded', function () {
    applyNavCollapsed(getNavCollapsed());
    bindNavToggle();
    bindGlobalClicks();
    bindHtmxGlobalConfirmAndResult();
    bindTableFilters(document);
    bindMachinesGrouping(document);
    bindQuickFilters(document);
    bindDensityToggles(document);
    bindMachineRowExpanders(document);
    bindSetupCheckboxes(document);
    bindChecklistBulkActions(document);
    bindOperationSetBuilders(document);
    bindDeleteButtons(document);
    bindGitPrepareForm(document);
    bindGithubClipboardCode(document);
    bindRealtime();
    refreshTopStatus();
    applyAutoMachinesDensity();

    window.addEventListener('resize', function () {
      applyAutoMachinesDensity();
    });

    window.setInterval(function () {
      refreshTopStatus();
    }, 30000);
  });
})();
