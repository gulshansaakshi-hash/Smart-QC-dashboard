/**
 * Chart.js renderer for the single-page dashboard (6 metric graphs).
 */

const chartRegistry = {};

function renderOrUpdateChart(canvasId, config) {
  const ctx = document.getElementById(canvasId);
  if (!ctx) return;

  if (chartRegistry[canvasId]) {
    chartRegistry[canvasId].destroy();
  }
  chartRegistry[canvasId] = new Chart(ctx, config);
}

function updateDashboardCharts(data) {
  const kpis = data.kpis || {};
  const machineStats = data.machine_stats || [];
  const machines = data.machines || [];
  const alerts = data.recent_alerts || [];

  // 1. Good vs Defective Parts (Doughnut)
  renderOrUpdateChart("chartGoodVsDefective", {
    type: "doughnut",
    data: {
      labels: ["Good Quality Parts", "Defective Parts"],
      datasets: [{
        data: [kpis.good_parts || 0, kpis.defective_parts || 0],
        backgroundColor: ["#16a34a", "#dc2626"],
      }],
    },
    options: { responsive: true, maintainAspectRatio: false },
  });

  // 2. Machine-Wise Production (Bar)
  renderOrUpdateChart("chartMachineProd", {
    type: "bar",
    data: {
      labels: machineStats.map((m) => m.machine_name),
      datasets: [{
        label: "Total Production",
        data: machineStats.map((m) => m.total_production),
        backgroundColor: "#2563eb",
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: { y: { beginAtZero: true } },
    },
  });

  // 3. Machine Temperature (°C) (Bar)
  renderOrUpdateChart("chartMachineTemp", {
    type: "bar",
    data: {
      labels: machines.map((m) => m.machine_name),
      datasets: [{
        label: "Temperature (°C)",
        data: machines.map((m) => (m.latest_sensor ? m.latest_sensor.temperature : 0)),
        backgroundColor: machines.map((m) => {
          const t = m.latest_sensor ? m.latest_sensor.temperature : 0;
          return t > 85 ? "#dc2626" : t > 80 ? "#ea580c" : "#2563eb";
        }),
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: { y: { beginAtZero: true } },
    },
  });

  // 4. Machine Vibration (mm/s) (Bar)
  renderOrUpdateChart("chartMachineVib", {
    type: "bar",
    data: {
      labels: machines.map((m) => m.machine_name),
      datasets: [{
        label: "Vibration (mm/s)",
        data: machines.map((m) => (m.latest_sensor ? m.latest_sensor.vibration : 0)),
        backgroundColor: machines.map((m) => {
          const v = m.latest_sensor ? m.latest_sensor.vibration : 0;
          return v > 7 ? "#dc2626" : v > 6 ? "#ea580c" : "#16a34a";
        }),
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: { y: { beginAtZero: true } },
    },
  });

  // 5. Machine-Wise Defect Rate (%) (Bar)
  renderOrUpdateChart("chartMachineDefect", {
    type: "bar",
    data: {
      labels: machineStats.map((m) => m.machine_name),
      datasets: [{
        label: "Defect %",
        data: machineStats.map((m) => m.defect_percentage || 0),
        backgroundColor: "#ea580c",
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: { y: { beginAtZero: true } },
    },
  });

  // 6. Anomalies by Severity (Doughnut)
  const sevCounts = { Critical: 0, High: 0, Medium: 0, Low: 0 };
  alerts.forEach((a) => {
    if (sevCounts[a.severity] !== undefined) sevCounts[a.severity] += 1;
  });

  renderOrUpdateChart("chartSeverity", {
    type: "doughnut",
    data: {
      labels: ["Critical", "High", "Medium", "Low"],
      datasets: [{
        data: [sevCounts.Critical, sevCounts.High, sevCounts.Medium, sevCounts.Low],
        backgroundColor: ["#dc2626", "#ea580c", "#f59e0b", "#16a34a"],
      }],
    },
    options: { responsive: true, maintainAspectRatio: false },
  });
}
