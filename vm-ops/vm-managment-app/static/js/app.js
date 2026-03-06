(function () {
  function qs(sel, root) {
    return (root || document).querySelector(sel);
  }

  function qsa(sel, root) {
    return Array.from((root || document).querySelectorAll(sel));
  }

  function openDrawer(title) {
    var drawer = qs('#drawer');
    if (!drawer) return;
    drawer.classList.add('open');
    drawer.setAttribute('aria-hidden', 'false');
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

  function bindTableFilters(root) {
    qsa('.table-filter', root).forEach(function (input) {
      var targetSelector = input.getAttribute('data-filter-target');
      var table = targetSelector ? qs(targetSelector) : null;
      if (!table) return;

      input.addEventListener('input', function () {
        var term = input.value.trim().toLowerCase();
        qsa('tbody tr', table).forEach(function (row) {
          var text = row.textContent.toLowerCase();
          row.style.display = !term || text.indexOf(term) !== -1 ? '' : 'none';
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
    return '<pre>' + lines.join('\n') + '</pre>';
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
        var res = await fetch('/api/git/prepare-commit', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
        var data = await res.json();
        if (!res.ok) {
          throw new Error((data && data.detail) || 'Failed to prepare commit.');
        }
        if (resultNode) {
          resultNode.innerHTML = renderGitPrepareResult(data);
        }
      } catch (err) {
        if (resultNode) {
          resultNode.innerHTML = '<div class="flash error">' + err.message + '</div>';
        }
      }
    });
  }

  async function refreshTopStatus() {
    try {
      var res = await fetch('/api/status');
      if (!res.ok) throw new Error('status failed');
      var data = await res.json();

      var changed = (data.changed_files || []).length;
      var validation = (data.validation_errors || []).length;

      var branchNode = qs('#pill-branch');
      var changesNode = qs('#pill-changes');
      var validationNode = qs('#pill-validation');
      var statusText = qs('#top-status-text');

      if (branchNode) branchNode.textContent = 'branch: ' + (data.branch || '-');
      if (changesNode) changesNode.textContent = 'changes: ' + changed;
      if (validationNode) validationNode.textContent = 'validation: ' + (validation ? 'errors' : 'ok');
      if (statusText) {
        statusText.textContent = validation
          ? 'Config validation has issues. Review before saving.'
          : 'Config validation is clean.';
      }
    } catch (_err) {
      var statusText = qs('#top-status-text');
      if (statusText) statusText.textContent = 'Failed to load repo status.';
    }
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
    });
  }

  document.addEventListener('htmx:afterSwap', function (event) {
    if (event.target && event.target.id === 'drawer-body') {
      bindSetupCheckboxes(event.target);
      openDrawer();
    }
  });

  document.addEventListener('DOMContentLoaded', function () {
    bindGlobalClicks();
    bindTableFilters(document);
    bindSetupCheckboxes(document);
    bindGitPrepareForm(document);
    refreshTopStatus();
  });
})();
