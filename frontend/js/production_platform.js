document.addEventListener('DOMContentLoaded', () => {
  const list = document.getElementById('deployment-list');
  if (list) {
    list.innerHTML = '<p>No deployments yet.</p>';
  }
});
