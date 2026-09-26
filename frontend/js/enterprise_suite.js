document.addEventListener('DOMContentLoaded', () => {
  const status = document.getElementById('gateway-status');
  if (status) {
    status.innerHTML = '<p>Gateway operational.</p>';
  }
});
