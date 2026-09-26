document.addEventListener('DOMContentLoaded', () => {
  const tabs = document.querySelectorAll('.tab');
  const contents = document.querySelectorAll('.tab-content');

  tabs.forEach(tab => {
    tab.addEventListener('click', () => {
      tabs.forEach(t => t.classList.remove('active'));
      contents.forEach(c => c.classList.add('hidden'));
      tab.classList.add('active');
      document.getElementById(tab.dataset.tab).classList.remove('hidden');
    });
  });

  const orgCtx = document.getElementById('orgChart')?.getContext('2d');
  if (orgCtx) {
    new Chart(orgCtx, {
      type: 'bar',
      data: {
        labels: ['Acme', 'Globex', 'Initech', 'Umbrella'],
        datasets: [{ label: 'Members', data: [12, 8, 5, 20], backgroundColor: '#4299e1' }]
      }
    });
  }

  const billCtx = document.getElementById('billingChart')?.getContext('2d');
  if (billCtx) {
    new Chart(billCtx, {
      type: 'line',
      data: {
        labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'],
        datasets: [{ label: 'Revenue', data: [1200, 1900, 3000, 5000, 2300, 3400], borderColor: '#38a169', fill: false }]
      }
    });
  }
});
