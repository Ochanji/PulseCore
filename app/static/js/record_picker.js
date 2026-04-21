// AJAX record lookup search for lookup fields

document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.lookup-field').forEach(initLookupField);
  document.querySelectorAll('.record-picker-component').forEach(initRecordPicker);
});

function initLookupField(container) {
  const search = container.querySelector('.lookup-search');
  const results = container.querySelector('.lookup-results');
  const valueInput = container.querySelector('.lookup-value');
  const entityTypeId = container.dataset.entityTypeId;

  if (!search || !results) return;

  let debounce;
  search.addEventListener('input', () => {
    clearTimeout(debounce);
    const q = search.value.trim();
    if (q.length < 2) { results.classList.add('hidden'); return; }
    debounce = setTimeout(() => fetchRecords(q, entityTypeId, results, search, valueInput), 300);
  });

  document.addEventListener('click', e => {
    if (!container.contains(e.target)) results.classList.add('hidden');
  });
}

function initRecordPicker(container) {
  const search = container.querySelector('.record-picker-search');
  const results = container.querySelector('.record-picker-results');
  const targetInput = document.getElementById('link-target-id');

  if (!search || !results) return;

  let debounce;
  search.addEventListener('input', () => {
    clearTimeout(debounce);
    const q = search.value.trim();
    if (q.length < 2) { results.classList.add('hidden'); return; }
    debounce = setTimeout(() => fetchAllRecords(q, results, search, targetInput), 300);
  });

  document.addEventListener('click', e => {
    if (!container.contains(e.target)) results.classList.add('hidden');
  });
}

function fetchRecords(q, entityTypeId, results, search, valueInput) {
  const url = entityTypeId
    ? `/api/v1/records/${entityTypeId}/?q=${encodeURIComponent(q)}`
    : `/api/v1/records/?q=${encodeURIComponent(q)}`;

  fetch(url, { headers: getAuthHeaders() })
    .then(r => r.json())
    .then(data => renderResults(data.data || [], results, search, valueInput))
    .catch(() => { results.classList.add('hidden'); });
}

function fetchAllRecords(q, results, search, valueInput) {
  fetch(`/api/v1/records/?q=${encodeURIComponent(q)}`, { headers: getAuthHeaders() })
    .then(r => r.json())
    .then(data => renderResults(data.data || [], results, search, valueInput))
    .catch(() => { results.classList.add('hidden'); });
}

function renderResults(records, results, search, valueInput) {
  results.innerHTML = '';
  if (!records.length) {
    results.innerHTML = '<div class="px-4 py-3 text-sm text-gray-400">No records found</div>';
    results.classList.remove('hidden');
    return;
  }
  records.forEach(rec => {
    const item = document.createElement('div');
    item.className = 'px-4 py-3 text-sm cursor-pointer hover:bg-blue-50 border-b border-gray-100 last:border-0';
    item.innerHTML = `<p class="font-medium text-gray-900">${rec.display_label || 'Record #' + rec.id}</p>
                      <p class="text-xs text-gray-400">${rec.entity_type || ''} · ${rec.org_unit || ''}</p>`;
    item.addEventListener('click', () => {
      if (valueInput) valueInput.value = rec.id;
      search.value = rec.display_label || 'Record #' + rec.id;
      results.classList.add('hidden');
    });
    results.appendChild(item);
  });
  results.classList.remove('hidden');
}

function getAuthHeaders() {
  // For web UI, session-based auth is used — API calls are made in same session context
  return { 'Content-Type': 'application/json' };
}
