// Build data from Jinja variables (safe JSON)
  const categoryTotals = {{ category_totals | tojson }};
  const categories = Object.keys(categoryTotals);
  const values = Object.values(categoryTotals);

  // If no categories, set a default to avoid Chart errors
  const labels = categories.length ? categories : ['No data'];
  const dataVals = values.length ? values : [0];

  // Pie Chart
  const pieCtx = document.getElementById('pieChart').getContext('2d');
  const pie = new Chart(pieCtx, {
    type: 'pie',
    data: {
      labels: labels,
      datasets: [{
        data: dataVals,
        backgroundColor: [
          '#3A7AFE', '#D4A857', '#22C55E', '#F97316', '#8B5CF6', '#6B7280'
        ],
        borderWidth: 0
      }]
    },
    options: { responsive: true, maintainAspectRatio: false }
  });

  // Bar Chart
  const barCtx = document.getElementById('barChart').getContext('2d');
  const bar = new Chart(barCtx, {
    type: 'bar',
    data: {
      labels: labels,
      datasets: [{
        label: '₹ Spent',
        data: dataVals,
        backgroundColor: '#3A7AFE'
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        y: { beginAtZero: true }
      }
    }
  });