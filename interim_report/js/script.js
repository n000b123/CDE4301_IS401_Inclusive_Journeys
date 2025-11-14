function openTab(evt, tabName) {
  // Hide all tab contents
  const contents = document.querySelectorAll('.tab-content');
  contents.forEach(c => c.style.display = 'none');

  // Remove "active" class from all buttons
  const tabs = document.querySelectorAll('.tab-link');
  tabs.forEach(t => t.classList.remove('active'));

  // Show selected tab and mark button as active
  document.getElementById(tabName).style.display = 'block';
  evt.currentTarget.classList.add('active');
}