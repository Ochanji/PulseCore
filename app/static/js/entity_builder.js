// Entity field builder — drag-drop canvas

let selectedCard = null;

// --- Add Question menu ---
function toggleAddMenu() {
  const menu = document.getElementById('add-question-menu');
  menu.classList.toggle('hidden');
}

document.addEventListener('click', function(e) {
  const wrapper = document.getElementById('add-question-wrapper');
  if (wrapper && !wrapper.contains(e.target)) {
    document.getElementById('add-question-menu').classList.add('hidden');
  }
});

function addField(fieldType) {
  document.getElementById('add-question-menu').classList.add('hidden');
  addFieldToCanvas(fieldType);
}

// --- Drag from palette (legacy support) ---
document.querySelectorAll('.palette-item').forEach(item => {
  item.addEventListener('dragstart', e => {
    e.dataTransfer.setData('field-type', item.dataset.fieldType);
    e.dataTransfer.setData('source', 'palette');
  });
});

function dropOnCanvas(e) {
  e.preventDefault();
  const source = e.dataTransfer.getData('source');
  if (source === 'palette') {
    addFieldToCanvas(e.dataTransfer.getData('field-type'));
  }
  const hint = document.getElementById('empty-hint');
  if (hint) hint.remove();
}

function addFieldToCanvas(fieldType) {
  const canvas = document.getElementById('field-canvas');
  const hint = document.getElementById('empty-hint');
  if (hint) hint.remove();

  const card = document.createElement('div');
  const label = fieldTypeLabel(fieldType);
  const icon = fieldTypeIcon(fieldType);

  card.className = 'field-card group flex items-center justify-between px-4 py-3 bg-gray-50 border border-gray-200 rounded-lg cursor-pointer hover:border-blue-300 transition-colors';
  card.dataset.id = '';
  card.dataset.name = '';
  card.dataset.label = label;
  card.dataset.fieldType = fieldType;
  card.dataset.required = 'false';
  card.dataset.unique = 'false';
  card.dataset.displayInList = 'false';
  card.dataset.options = '[]';
  card.dataset.lookupEntity = '';
  card.draggable = true;
  card.setAttribute('ondragstart', 'dragStart(event)');
  card.setAttribute('ondragover', 'event.preventDefault()');
  card.setAttribute('ondrop', 'dropReorder(event)');
  card.setAttribute('onclick', 'selectField(this)');

  card.innerHTML = `
    <div class="flex items-center space-x-3 min-w-0">
      <span class="text-gray-300 cursor-grab flex-shrink-0">&#8942;&#8942;</span>
      <span class="flex-shrink-0 w-6 h-6 flex items-center justify-center rounded bg-white border border-gray-200 text-xs font-bold text-gray-500">${icon}</span>
      <div class="min-w-0">
        <p class="text-sm font-medium text-gray-900 truncate">${label}</p>
        <p class="text-xs text-gray-400">${fieldType.replace(/_/g,' ')}</p>
      </div>
    </div>
    <div class="flex items-center space-x-1 flex-shrink-0 ml-2">
      <button onclick="event.stopPropagation(); removeField(this.closest('.field-card'))"
              class="ml-1 opacity-0 group-hover:opacity-100 text-gray-300 hover:text-red-500 transition-opacity text-base leading-none">&times;</button>
    </div>`;

  canvas.appendChild(card);
  updateFieldCount();
  selectField(card);
}

function fieldTypeLabel(type) {
  const map = {
    text: 'Text', textarea: 'Long Text',
    integer: 'Integer', decimal: 'Decimal', phone: 'Phone / Numeric ID',
    date: 'Date', time: 'Time', datetime: 'Date & Time',
    select: 'Single Select', multi_select: 'Checkbox (Multi-select)',
    boolean: 'Yes / No', photo: 'Photo', file: 'File Upload',
    gps: 'GPS Location', lookup: 'Lookup Table',
    label: 'Label / Instruction', hidden: 'Hidden Value',
    barcode: 'Barcode / QR Code', rating: 'Rating',
    group: 'Group', repeat_group: 'Repeat Group'
  };
  return map[type] || type;
}

function fieldTypeIcon(type) {
  const map = {
    text: 'T', textarea: 'T',
    integer: '1', decimal: '.0', phone: '#',
    date: '&#128197;', time: '&#128336;', datetime: '&#128197;',
    select: '&#9776;', multi_select: '&#9776;',
    boolean: 'Y/N', photo: '&#128247;', file: '&#128206;',
    gps: '&#128205;', lookup: '&#128279;',
    label: 'Lb', hidden: '&#128065;',
    barcode: '&#9644;', rating: '&#9733;',
    group: '[]', repeat_group: '[]'
  };
  return map[type] || '?';
}

// --- Reorder by drag ---
let dragSource = null;

function dragStart(e) {
  dragSource = e.currentTarget;
  e.dataTransfer.setData('source', 'canvas');
  e.dataTransfer.effectAllowed = 'move';
}

function dropReorder(e) {
  e.preventDefault();
  const source = e.dataTransfer.getData('source');
  if (source !== 'canvas' || !dragSource) return;
  const target = e.currentTarget;
  if (target === dragSource) return;
  const canvas = document.getElementById('field-canvas');
  const cards = [...canvas.querySelectorAll('.field-card')];
  const srcIdx = cards.indexOf(dragSource);
  const tgtIdx = cards.indexOf(target);
  if (srcIdx < tgtIdx) target.after(dragSource);
  else target.before(dragSource);
}

// --- Select field ---
function selectField(card) {
  document.querySelectorAll('.field-card').forEach(c =>
    c.classList.remove('border-blue-400', 'bg-blue-50'));
  card.classList.add('border-blue-400', 'bg-blue-50');
  selectedCard = card;

  document.getElementById('no-selection').classList.add('hidden');
  document.getElementById('field-props').classList.remove('hidden');

  document.getElementById('prop-label').value = card.dataset.label || '';
  document.getElementById('prop-type').value = card.dataset.fieldType || 'text';
  document.getElementById('prop-required').checked = card.dataset.required === 'true';
  document.getElementById('prop-unique').checked = card.dataset.unique === 'true';
  document.getElementById('prop-display-in-list').checked = card.dataset.displayInList === 'true';

  try {
    const opts = JSON.parse(card.dataset.options || '[]');
    document.getElementById('prop-options').value = opts.join('\n');
  } catch { document.getElementById('prop-options').value = ''; }

  document.getElementById('prop-lookup-entity').value = card.dataset.lookupEntity || '';
  toggleTypeExtras();
}

function toggleTypeExtras() {
  const type = document.getElementById('prop-type').value;
  document.getElementById('options-section').classList.toggle('hidden', !['select', 'multi_select'].includes(type));
  document.getElementById('lookup-section').classList.toggle('hidden', type !== 'lookup');
}

function updateSelectedField() {
  if (!selectedCard) return;
  const label = document.getElementById('prop-label').value;
  const type = document.getElementById('prop-type').value;
  const required = document.getElementById('prop-required').checked;
  const unique = document.getElementById('prop-unique').checked;
  const displayInList = document.getElementById('prop-display-in-list').checked;
  const opts = document.getElementById('prop-options').value.split('\n').map(s => s.trim()).filter(Boolean);
  const lookupEntity = document.getElementById('prop-lookup-entity').value;

  selectedCard.dataset.label = label;
  selectedCard.dataset.fieldType = type;
  selectedCard.dataset.required = required;
  selectedCard.dataset.unique = unique;
  selectedCard.dataset.displayInList = displayInList;
  selectedCard.dataset.options = JSON.stringify(opts);
  selectedCard.dataset.lookupEntity = lookupEntity;

  const nameEl = selectedCard.querySelector('p.text-sm');
  if (nameEl) nameEl.textContent = label || '(unnamed)';
  const typeEl = selectedCard.querySelector('p.text-xs');
  if (typeEl) typeEl.textContent = type.replace(/_/g, ' ');

  // Update badges
  const badgesContainer = selectedCard.querySelector('.flex.items-center.space-x-1');
  badgesContainer.querySelectorAll('span').forEach(b => b.remove());

  if (required) {
    const b = document.createElement('span');
    b.className = 'text-xs bg-red-50 text-red-500 border border-red-200 px-1.5 py-0.5 rounded';
    b.textContent = 'req';
    badgesContainer.prepend(b);
  }
  if (displayInList) {
    const b = document.createElement('span');
    b.className = 'text-xs bg-green-50 text-green-600 border border-green-200 px-1.5 py-0.5 rounded';
    b.textContent = 'list';
    badgesContainer.prepend(b);
  }
}

function removeField(card) {
  if (selectedCard === card) {
    selectedCard = null;
    document.getElementById('no-selection').classList.remove('hidden');
    document.getElementById('field-props').classList.add('hidden');
  }
  card.remove();
  updateFieldCount();
}

function updateFieldCount() {
  const count = document.querySelectorAll('#field-canvas .field-card').length;
  const el = document.getElementById('field-count');
  if (el) el.textContent = count;
}

function saveFields() {
  const cards = document.querySelectorAll('#field-canvas .field-card');
  const fields = [];
  cards.forEach((card, idx) => {
    let opts = [];
    try { opts = JSON.parse(card.dataset.options || '[]'); } catch {}
    fields.push({
      id: card.dataset.id || null,
      label: card.dataset.label || '',
      field_type: card.dataset.fieldType || 'text',
      is_required: card.dataset.required === 'true',
      is_unique: card.dataset.unique === 'true',
      display_in_list: card.dataset.displayInList === 'true',
      options: opts,
      lookup_entity_type_id: card.dataset.lookupEntity || null,
      order: idx,
    });
  });

  document.getElementById('fields-data-input').value = JSON.stringify(fields);
  document.getElementById('save-fields-form').submit();
}

// Init field count on page load
document.addEventListener('DOMContentLoaded', updateFieldCount);
