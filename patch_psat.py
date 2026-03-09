with open('C:/Users/Palak Vardhan/dashboard/index.html', 'r', encoding='utf-8') as f:
    c = f.read()

history_js = r"""
// ─── PSAT HISTORY (last 6 days, seeded + auto-saved) ─────────────────────────
const PSAT_HISTORY_SEED = {
  '2026-02-28': { psat_pct: 72, connected: 46 },
  '2026-03-01': { psat_pct: 75, connected: 75 },
  '2026-03-02': { psat_pct: 79, connected: 52 },
  '2026-03-03': { psat_pct: 88, connected: 32 },
  '2026-03-04': { psat_pct: 75, connected: null }
};

let psatHistoryChart = null;

function getTodayKey() {
  const d = new Date();
  return d.getFullYear() + '-' + String(d.getMonth()+1).padStart(2,'0') + '-' + String(d.getDate()).padStart(2,'0');
}

function getHistory() {
  const hist = psatState['__history__'] || {};
  const merged = Object.assign({}, PSAT_HISTORY_SEED, hist);
  return merged;
}

function saveHistoryToday() {
  let connected = 0, psatScore = 0;
  psatRaw.forEach(r => {
    const s = psatState[r[0]] || {};
    if (s.connected === 'Y') { connected++; if (s.psat === 1) psatScore++; }
  });
  if (connected === 0) return;
  const psat_pct = Math.round((psatScore / connected) * 100);
  if (!psatState['__history__']) psatState['__history__'] = {};
  psatState['__history__'][getTodayKey()] = { psat_pct, connected };
}

function updatePsatHistoryChart() {
  if (!psatHistoryChart) return;
  const hist = getHistory();
  const sorted = Object.entries(hist)
    .sort((a, b) => a[0].localeCompare(b[0]))
    .slice(-7);
  const labels = sorted.map(([d]) => {
    const dt = new Date(d + 'T00:00:00');
    return dt.toLocaleDateString('en-GB', { day: 'numeric', month: 'short' });
  });
  const psatVals = sorted.map(([, v]) => v.psat_pct);
  const connVals = sorted.map(([, v]) => v.connected);
  psatHistoryChart.data.labels = labels;
  psatHistoryChart.data.datasets[0].data = connVals;
  psatHistoryChart.data.datasets[1].data = psatVals;
  psatHistoryChart.update();
}

psatHistoryChart = new Chart(document.getElementById('chart-psat-history'), {
  type: 'bar',
  data: {
    labels: [],
    datasets: [
      {
        label: '# of Calls Connected',
        data: [],
        backgroundColor: 'rgba(200,200,220,0.3)',
        borderColor: 'rgba(200,200,220,0.5)',
        borderWidth: 1,
        borderRadius: 4,
        yAxisID: 'yRight',
        order: 2
      },
      {
        label: 'PSAT %',
        data: [],
        type: 'line',
        borderColor: '#e91e8c',
        backgroundColor: 'transparent',
        borderWidth: 3,
        pointBackgroundColor: '#e91e8c',
        pointRadius: 6,
        pointHoverRadius: 8,
        fill: false,
        tension: 0.3,
        yAxisID: 'yLeft',
        order: 1
      }
    ]
  },
  options: {
    responsive: true, maintainAspectRatio: false,
    plugins: {
      legend: { labels: { color: '#90caf9', font: { size: 11 } } },
      tooltip: { callbacks: {
        label: ctx => ctx.datasetIndex === 1 ? 'PSAT: ' + ctx.raw + '%' : 'Connected: ' + (ctx.raw ?? '—')
      }}
    },
    scales: {
      x: { ticks: { color: '#e0e0e0', font: { size: 12 } }, grid: { color: '#0f3460' } },
      yLeft: {
        type: 'linear', position: 'left',
        min: 60, max: 100,
        ticks: { color: '#e91e8c', font: { size: 10 }, callback: v => v + '%' },
        grid: { color: '#0f3460' },
        title: { display: true, text: 'PSAT', color: '#e91e8c', font: { size: 11 } }
      },
      yRight: {
        type: 'linear', position: 'right',
        beginAtZero: true,
        ticks: { color: '#90caf9', font: { size: 10 } },
        grid: { display: false },
        title: { display: true, text: '# of Calls (Connected)', color: '#90caf9', font: { size: 11 } }
      }
    }
  },
  plugins: [{
    afterDatasetsDraw(chart) {
      const ds = chart.data.datasets[1];
      const meta = chart.getDatasetMeta(1);
      const ctx2 = chart.ctx;
      meta.data.forEach((pt, i) => {
        const val = ds.data[i];
        if (val == null) return;
        ctx2.save();
        ctx2.fillStyle = '#ffffff';
        ctx2.font = 'bold 11px Segoe UI, Arial, sans-serif';
        ctx2.textAlign = 'center';
        ctx2.fillText(val + '%', pt.x, pt.y - 12);
        ctx2.restore();
      });
    }
  }]
});

"""

c = c.replace('init();', history_js + 'init();')
print('PSAT_HISTORY_SEED inserted:', 'PSAT_HISTORY_SEED' in c)

with open('C:/Users/Palak Vardhan/dashboard/index.html', 'w', encoding='utf-8') as f:
    f.write(c)
print('done')
