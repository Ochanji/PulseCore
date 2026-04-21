// Form builder — field selection and ordering

document.addEventListener('DOMContentLoaded', () => {
  // Toggle help text input visibility when checkbox changes
  document.querySelectorAll('input[name="field_ids"]').forEach(cb => {
    cb.addEventListener('change', function () {
      const fieldId = this.value;
      let helpContainer = document.getElementById('help_container_' + fieldId);
      if (!helpContainer) {
        helpContainer = document.createElement('div');
        helpContainer.id = 'help_container_' + fieldId;
        helpContainer.className = 'mt-2';
        helpContainer.innerHTML = `<input type="text" name="help_${fieldId}"
          placeholder="Optional help text..."
          class="w-full px-2 py-1.5 text-xs border border-gray-200 rounded-lg focus:outline-none focus:ring-1 focus:ring-blue-500">`;
        this.closest('.flex').querySelector('.ml-3').appendChild(helpContainer);
      }
      helpContainer.style.display = this.checked ? 'block' : 'none';
    });
  });
});
