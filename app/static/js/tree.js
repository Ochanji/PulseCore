// Org unit tree expand/collapse

function toggleNode(btn) {
  const li = btn.closest('li');
  const children = li.querySelector('.tree-children');
  if (!children) return;
  const isOpen = children.style.display !== 'none';
  children.style.display = isOpen ? 'none' : 'block';
  btn.textContent = isOpen ? '▸' : '▾';
}

function expandAll() {
  document.querySelectorAll('.tree-children').forEach(el => el.style.display = 'block');
  document.querySelectorAll('.tree-toggle').forEach(btn => btn.textContent = '▾');
}

function collapseAll() {
  document.querySelectorAll('.tree-children').forEach(el => {
    // Keep root level open
    const depth = el.closest('ul').dataset.depth;
    if (depth !== '0') el.style.display = 'none';
  });
  document.querySelectorAll('.tree-toggle').forEach(btn => btn.textContent = '▸');
}
