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

  const modCtx = document.getElementById('moderationChart')?.getContext('2d');
  if (modCtx) {
    new Chart(modCtx, {
      type: 'line',
      data: {
        labels: ['00:00', '04:00', '08:00', '12:00', '16:00', '20:00'],
        datasets: [
          { label: 'Flagged', data: [2, 1, 5, 8, 6, 3], borderColor: '#f56565', fill: false },
          { label: 'Blocked', data: [1, 0, 2, 4, 3, 1], borderColor: '#c53030', fill: false }
        ]
      }
    });
  }

  const jbCtx = document.getElementById('jailbreakChart')?.getContext('2d');
  if (jbCtx) {
    new Chart(jbCtx, {
      type: 'bar',
      data: {
        labels: ['DAN', 'Developer Mode', 'God Mode', 'Other'],
        datasets: [{ label: 'Attempts', data: [12, 8, 5, 3], backgroundColor: '#e53e3e' }]
      }
    });
  }

  const piiCtx = document.getElementById('piiChart')?.getContext('2d');
  if (piiCtx) {
    new Chart(piiCtx, {
      type: 'doughnut',
      data: {
        labels: ['API Keys', 'SSN', 'Credit Card', 'Clean'],
        datasets: [{ data: [4, 2, 1, 93], backgroundColor: ['#e53e3e', '#dd6b20', '#d69e2e', '#48bb78'] }]
      }
    });
  }

  const constCtx = document.getElementById('constitutionalChart')?.getContext('2d');
  if (constCtx) {
    new Chart(constCtx, {
      type: 'radar',
      data: {
        labels: ['No Harm', 'No Hate', 'No Deception', 'Privacy', 'Accuracy'],
        datasets: [{ label: 'Compliance', data: [0.9, 0.85, 0.8, 0.95, 0.75], fill: true, backgroundColor: 'rgba(66, 153, 225, 0.2)', borderColor: '#4299e1' }]
      }
    });
  }
});
