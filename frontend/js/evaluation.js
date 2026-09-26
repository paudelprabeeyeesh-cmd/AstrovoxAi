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

  const seed = Date.now();
  const rand = (min, max) => min + Math.random() * (max - min);

  function renderMetrics(id, metrics) {
    const container = document.getElementById(id);
    if (!container) return;
    container.innerHTML = metrics.map(m => `<div class="metric"><div class="metric-value">${m.value}</div><div class="metric-label">${m.label}</div></div>`).join('');
  }

  function renderTable(id, rows, formatter) {
    const tbody = document.querySelector(`#${id} tbody`);
    if (!tbody) return;
    tbody.innerHTML = rows.map(formatter).join('');
  }

  function statusBadge(passed) {
    if (passed === true) return '<span class="status-badge status-pass">Pass</span>';
    if (passed === false) return '<span class="status-badge status-fail">Fail</span>';
    return '<span class="status-badge status-warn">Warn</span>';
  }

  const regressionData = Array.from({ length: 12 }, (_, i) => ({
    case_id: `reg_${i + 1}`,
    passed: Math.random() > 0.15,
    baseline: rand(0.7, 0.95),
    current: rand(0.7, 0.95),
    delta: rand(-0.05, 0.05),
    latency: rand(20, 180),
  }));

  renderMetrics('regressionMetrics', [
    { label: 'Total Cases', value: regressionData.length },
    { label: 'Passed', value: regressionData.filter(r => r.passed).length },
    { label: 'Failed', value: regressionData.filter(r => !r.passed).length },
    { label: 'Pass Rate', value: `${(regressionData.filter(r => r.passed).length / regressionData.length * 100).toFixed(1)}%` },
  ]);

  renderTable('regressionTable', regressionData, r => `<tr><td>${r.case_id}</td><td>${statusBadge(r.passed)}</td><td>${r.baseline.toFixed(3)}</td><td>${r.current.toFixed(3)}</td><td>${r.delta.toFixed(4)}</td><td>${r.latency.toFixed(0)}</td></tr>`);

  const regCtx = document.getElementById('regressionChart')?.getContext('2d');
  if (regCtx) {
    new Chart(regCtx, {
      type: 'line',
      data: {
        labels: regressionData.map(r => r.case_id),
        datasets: [
          { label: 'Baseline', data: regressionData.map(r => r.baseline), borderColor: '#a0aec0', fill: false },
          { label: 'Current', data: regressionData.map(r => r.current), borderColor: '#38a169', fill: false },
        ],
      },
    });
  }

  const benchmarkData = [
    { name: 'MMLU', accuracy: 0.78 },
    { name: 'HellaSwag', accuracy: 0.82 },
    { name: 'TruthfulQA', accuracy: 0.71 },
    { name: 'GSM8K', accuracy: 0.64 },
    { name: 'HumanEval', accuracy: 0.69 },
  ];

  renderMetrics('benchmarkMetrics', [
    { label: 'Overall Accuracy', value: `${(benchmarkData.reduce((a, b) => a + b.accuracy, 0) / benchmarkData.length * 100).toFixed(1)}%` },
    { label: 'Benchmarks', value: benchmarkData.length },
    { label: 'Total Samples', value: '5,000' },
    { label: 'Mean Latency', value: '112ms' },
  ]);

  renderTable('benchmarkTable', benchmarkData, r => `<tr><td>${r.name}</td><td>${(r.accuracy * 100).toFixed(1)}%</td><td>1,000</td><td>${rand(80, 200).toFixed(0)}</td></tr>`);

  const benchCtx = document.getElementById('benchmarkChart')?.getContext('2d');
  if (benchCtx) {
    new Chart(benchCtx, {
      type: 'bar',
      data: {
        labels: benchmarkData.map(b => b.name),
        datasets: [{ label: 'Accuracy', data: benchmarkData.map(b => b.accuracy), backgroundColor: ['#4299e1', '#48bb78', '#ed8936', '#9f7aea', '#38a169'] }],
      },
    });
  }

  const humanData = Array.from({ length: 15 }, (_, i) => ({
    eval_id: `human_${i + 1}`,
    rater: `rater_${(i % 3) + 1}`,
    case_id: `case_${(i % 5) + 1}`,
    score: rand(2.5, 5.0).toFixed(1),
    notes: ['Good response', 'Needs improvement', 'Excellent', 'Average', 'Hallucinated'][i % 5],
  }));

  const humanScores = humanData.map(h => parseFloat(h.score));
  renderMetrics('humanMetrics', [
    { label: 'Total Evals', value: humanData.length },
    { label: 'Mean Score', value: (humanScores.reduce((a, b) => a + b, 0) / humanScores.length).toFixed(2) },
    { label: 'Min Score', value: Math.min(...humanScores).toFixed(1) },
    { label: 'Max Score', value: Math.max(...humanScores).toFixed(1) },
  ]);

  renderTable('humanTable', humanData, r => `<tr><td>${r.eval_id}</td><td>${r.rater}</td><td>${r.case_id}</td><td>${r.score}</td><td>${r.notes}</td></tr>`);

  const humanCtx = document.getElementById('humanChart')?.getContext('2d');
  if (humanCtx) {
    new Chart(humanCtx, {
      type: 'bar',
      data: {
        labels: [...new Set(humanData.map(h => h.rater))],
        datasets: [{ label: 'Avg Score', data: [...new Set(humanData.map(h => h.rater))].map(rater => {
          const scores = humanData.filter(h => h.rater === rater).map(h => parseFloat(h.score));
          return scores.reduce((a, b) => a + b, 0) / scores.length;
        }), backgroundColor: '#9f7aea' }],
      },
    });
  }

  const gradingData = [
    { case_id: 'grade_1', passed: true, score: 95, max: 100, feedback: 'Exact match' },
    { case_id: 'grade_2', passed: true, score: 88, max: 100, feedback: 'Pattern matched' },
    { case_id: 'grade_3', passed: false, score: 42, max: 100, feedback: 'Mismatch' },
    { case_id: 'grade_4', passed: true, score: 76, max: 100, feedback: 'Rubric applied' },
    { case_id: 'grade_5', passed: false, score: 18, max: 100, feedback: 'Mismatch' },
  ];

  renderMetrics('gradingMetrics', [
    { label: 'Passed', value: gradingData.filter(g => g.passed).length },
    { label: 'Failed', value: gradingData.filter(g => !g.passed).length },
    { label: 'Pass Rate', value: `${(gradingData.filter(g => g.passed).length / gradingData.length * 100).toFixed(1)}%` },
    { label: 'Mean Score', value: `${(gradingData.reduce((a, b) => a + b.score, 0) / gradingData.length).toFixed(1)}` },
  ]);

  renderTable('gradingTable', gradingData, r => `<tr><td>${r.case_id}</td><td>${statusBadge(r.passed)}</td><td>${r.score}</td><td>${r.max}</td><td>${r.feedback}</td></tr>`);

  const gradingCtx = document.getElementById('gradingChart')?.getContext('2d');
  if (gradingCtx) {
    new Chart(gradingCtx, {
      type: 'doughnut',
      data: {
        labels: ['Passed', 'Failed'],
        datasets: [{ data: [gradingData.filter(g => g.passed).length, gradingData.filter(g => !g.passed).length], backgroundColor: ['#48bb78', '#f56565'] }],
      },
    });
  }

  const safetyData = [
    { case_id: 'safe_1', safe: true, category: 'none', confidence: 0.0, latency: 12 },
    { case_id: 'safe_2', safe: true, category: 'none', confidence: 0.0, latency: 9 },
    { case_id: 'safe_3', safe: false, category: 'jailbreak', confidence: 0.85, latency: 45 },
    { case_id: 'safe_4', safe: false, category: 'pii', confidence: 0.92, latency: 38 },
    { case_id: 'safe_5', safe: true, category: 'none', confidence: 0.0, latency: 11 },
  ];

  renderMetrics('safetyMetrics', [
    { label: 'Safe Rate', value: `${(safetyData.filter(s => s.safe).length / safetyData.length * 100).toFixed(1)}%` },
    { label: 'Unsafe', value: safetyData.filter(s => !s.safe).length },
    { label: 'Mean Confidence', value: `${(safetyData.reduce((a, b) => a + b.confidence, 0) / safetyData.length).toFixed(2)}` },
    { label: 'Mean Latency', value: `${(safetyData.reduce((a, b) => a + b.latency, 0) / safetyData.length).toFixed(0)}ms` },
  ]);

  renderTable('safetyTable', safetyData, r => `<tr><td>${r.case_id}</td><td>${statusBadge(r.safe)}</td><td>${r.category}</td><td>${(r.confidence * 100).toFixed(0)}%</td><td>${r.latency}</td></tr>`);

  const safetyCtx = document.getElementById('safetyChart')?.getContext('2d');
  if (safetyCtx) {
    const categories = {};
    safetyData.forEach(r => {
      const cats = r.category === 'none' ? [] : r.category.split(', ');
      cats.forEach(c => { categories[c] = (categories[c] || 0) + 1; });
    });
    new Chart(safetyCtx, {
      type: 'bar',
      data: {
        labels: Object.keys(categories),
        datasets: [{ label: 'Flagged', data: Object.values(categories), backgroundColor: '#f56565' }],
      },
    });
  }

  const hallucinationData = [
    { case_id: 'hall_1', hallucinated: false, supported: 8, unsupported: 1, score: 0.89 },
    { case_id: 'hall_2', hallucinated: true, supported: 3, unsupported: 7, score: 0.30 },
    { case_id: 'hall_3', hallucinated: false, supported: 9, unsupported: 0, score: 1.0 },
    { case_id: 'hall_4', hallucinated: false, supported: 6, unsupported: 2, score: 0.75 },
    { case_id: 'hall_5', hallucinated: true, supported: 4, unsupported: 5, score: 0.44 },
  ];

  renderMetrics('hallucinationMetrics', [
    { label: 'Grounded Rate', value: `${(hallucinationData.filter(h => !h.hallucinated).length / hallucinationData.length * 100).toFixed(1)}%` },
    { label: 'Hallucinated', value: hallucinationData.filter(h => h.hallucinated).length },
    { label: 'Mean Score', value: `${(hallucinationData.reduce((a, b) => a + b.score, 0) / hallucinationData.length).toFixed(2)}` },
    { label: 'Mean Unsupported', value: `${(hallucinationData.reduce((a, b) => a + b.unsupported, 0) / hallucinationData.length).toFixed(1)}` },
  ]);

  renderTable('hallucinationTable', hallucinationData, r => `<tr><td>${r.case_id}</td><td>${statusBadge(!r.hallucinated)}</td><td>${r.supported}</td><td>${r.unsupported}</td><td>${r.score.toFixed(2)}</td></tr>`);

  const hallCtx = document.getElementById('hallucinationChart')?.getContext('2d');
  if (hallCtx) {
    new Chart(hallCtx, {
      type: 'bar',
      data: {
        labels: hallucinationData.map(h => h.case_id),
        datasets: [
          { label: 'Supported', data: hallucinationData.map(h => h.supported), backgroundColor: '#48bb78' },
          { label: 'Unsupported', data: hallucinationData.map(h => h.unsupported), backgroundColor: '#f56565' },
        ],
      },
    });
  }

  const accuracyData = [
    { task: 'QA', case_id: 'acc_1', correct: true, score: 1.0, latency: 45 },
    { task: 'QA', case_id: 'acc_2', correct: true, score: 0.92, latency: 38 },
    { task: 'Summarization', case_id: 'acc_3', correct: true, score: 0.88, latency: 120 },
    { task: 'Reasoning', case_id: 'acc_4', correct: false, score: 0.41, latency: 210 },
    { task: 'Reasoning', case_id: 'acc_5', correct: true, score: 0.95, latency: 185 },
  ];

  const accuracyByTask = {};
  accuracyData.forEach(r => { accuracyByTask[r.task] = accuracyByTask[r.task] || []; accuracyByTask[r.task].push(r.score); });

  renderMetrics('accuracyMetrics', [
    { label: 'Overall Accuracy', value: `${(accuracyData.reduce((a, b) => a + b.score, 0) / accuracyData.length * 100).toFixed(1)}%` },
    { label: 'Exact Match Rate', value: `${(accuracyData.filter(r => r.correct).length / accuracyData.length * 100).toFixed(1)}%` },
    { label: 'Tasks', value: Object.keys(accuracyByTask).length },
    { label: 'Mean Latency', value: `${(accuracyData.reduce((a, b) => a + b.latency, 0) / accuracyData.length).toFixed(0)}ms` },
  ]);

  renderTable('accuracyTable', accuracyData, r => `<tr><td>${r.task}</td><td>${r.case_id}</td><td>${statusBadge(r.correct)}</td><td>${r.score.toFixed(2)}</td><td>${r.latency}</td></tr>`);

  const accCtx = document.getElementById('accuracyChart')?.getContext('2d');
  if (accCtx) {
    new Chart(accCtx, {
      type: 'radar',
      data: {
        labels: Object.keys(accuracyByTask),
        datasets: [{ label: 'Accuracy', data: Object.keys(accuracyByTask).map(t => accuracyByTask[t].reduce((a, b) => a + b, 0) / accuracyByTask[t].length), borderColor: '#38a169', backgroundColor: 'rgba(56, 161, 105, 0.2)' }],
      },
    });
  }
});
