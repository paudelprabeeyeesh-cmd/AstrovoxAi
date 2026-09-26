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

  // Mock regression chart
  const regCtx = document.getElementById('regressionChart')?.getContext('2d');
  if (regCtx) {
    new Chart(regCtx, {
      type: 'line',
      data: {
        labels: ['v1.0', 'v1.1', 'v1.2', 'v1.3'],
        datasets: [{ label: 'Pass Rate', data: [0.95, 0.94, 0.96, 0.95], borderColor: '#38a169', fill: false }]
      }
    });
  }

  const benchCtx = document.getElementById('benchmarkChart')?.getContext('2d');
  if (benchCtx) {
    new Chart(benchCtx, {
      type: 'bar',
      data: {
        labels: ['MMLU', 'HellaSwag', 'TruthfulQA'],
        datasets: [{ label: 'Accuracy', data: [0.78, 0.82, 0.71], backgroundColor: ['#4299e1', '#48bb78', '#ed8936'] }]
      }
    });
  }

  const humanCtx = document.getElementById('humanChart')?.getContext('2d');
  if (humanCtx) {
    new Chart(humanCtx, {
      type: 'bar',
      data: {
        labels: ['Rater 1', 'Rater 2', 'Rater 3'],
        datasets: [{ label: 'Score', data: [4.2, 4.5, 3.9], backgroundColor: '#9f7aea' }]
      }
    });
  }

  const gradingCtx = document.getElementById('gradingChart')?.getContext('2d');
  if (gradingCtx) {
    new Chart(gradingCtx, {
      type: 'doughnut',
      data: {
        labels: ['Passed', 'Failed'],
        datasets: [{ data: [85, 15], backgroundColor: ['#48bb78', '#f56565'] }]
      }
    });
  }
});
