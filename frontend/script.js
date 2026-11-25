/**
 * Basic Single-Page Dashboard Controller.
 * Connects to Flask (/api/*) if running, or automatically uses a randomized
 * local dataset so it works immediately in any browser.
 */

let pollingTimer = null;
let useLocalDemo = window.location.protocol === "file:";
let localStore = null;

const DEMO_MACHINES = [
  { machine_id: "M001", machine_name: "CNC Machine 01", line_name: "Gear Manufacturing", rpmMin: 1200, rpmMax: 1800, faultProb: 0.08 },
  { machine_id: "M002", machine_name: "Gear Cutting Machine 01", line_name: "Gear Manufacturing", rpmMin: 800, rpmMax: 1400, faultProb: 0.30 },
  { machine_id: "M003", machine_name: "Bearing Assembly Machine 01", line_name: "Bearing Manufacturing", rpmMin: 1000, rpmMax: 1600, faultProb: 0.08 },
  { machine_id: "M004", machine_name: "Grinding Machine 01", line_name: "Bearing Manufacturing", rpmMin: 1800, rpmMax: 2600, faultProb: 0.25 },
  { machine_id: "M005", machine_name: "CNC Machine 02", line_name: "Precision Components", rpmMin: 1300, rpmMax: 1900, faultProb: 0.32 },
];

function randFloat(min, max) {
  return Number((Math.random() * (max - min) + min).toFixed(2));
}

function randInt(min, max) {
  return Math.floor(Math.random() * (max - min + 1)) + min;
}

function formatTs(date) {
  const p = (n) => String(n).padStart(2, "0");
  return `${date.getFullYear()}-${p(date.getMonth() + 1)}-${p(date.getDate())} ${p(date.getHours())}:${p(date.getMinutes())}:${p(date.getSeconds())}`;
}

function createSensorReading(machine, ts, forceFault = false) {
  let temperature = randFloat(50, 76);
  let vibration = randFloat(1.2, 4.9);
  let pressure = randFloat(4.8, 8.3);
  let rpm = randInt(machine.rpmMin + 40, machine.rpmMax - 40);

  if (forceFault || Math.random() < machine.faultProb) {
    const pick = randInt(1, 4);
    if (pick === 1) {
      temperature = randFloat(86.5, 95.0);
      vibration = randFloat(7.4, 9.5);
    } else if (pick === 2) {
      vibration = randFloat(7.3, 9.2);
      rpm = machine.rpmMax + randInt(120, 300);
    } else if (pick === 3) {
      pressure = randFloat(2.3, 3.7);
    } else {
      pressure = randFloat(9.3, 11.0);
    }
  }

  return { temperature, vibration, pressure, rpm, timestamp: formatTs(ts) };
}

function evaluateAnomalies(machine, reading) {
  const list = [];
  let cause = "Unusual operating condition";
  let action = "Inspect machine parameters.";

  if (reading.temperature > 85 && reading.vibration > 7) {
    cause = "Bearing wear or friction";
    action = "Inspect bearing lubrication.";
  } else if (reading.vibration > 7 && (reading.rpm < machine.rpmMin || reading.rpm > machine.rpmMax)) {
    cause = "Shaft misalignment";
    action = "Check shaft alignment.";
  } else if (reading.pressure < 4) {
    cause = "Hydraulic pressure loss";
    action = "Inspect hydraulic connections.";
  } else if (reading.pressure > 9) {
    cause = "Excessive hydraulic pressure";
    action = "Check pressure regulator.";
  }

  const add = (sensor_type, observed_value, severity) => {
    list.push({
      anomaly_id: `ANOM-${Math.random().toString(16).slice(2, 8).toUpperCase()}`,
      machine_id: machine.machine_id,
      machine_name: machine.machine_name,
      sensor_type,
      observed_value,
      severity,
      possible_cause: cause,
      recommended_action: action,
      detection_timestamp: reading.timestamp,
      alert_status: "Unresolved",
    });
  };

  if (reading.temperature > 85) add("Temperature", `${reading.temperature} °C`, "Critical");
  else if (reading.temperature > 80) add("Temperature", `${reading.temperature} °C`, "Medium");

  if (reading.vibration > 7) add("Vibration", `${reading.vibration} mm/s`, "Critical");
  else if (reading.vibration > 6) add("Vibration", `${reading.vibration} mm/s`, "Medium");

  if (reading.pressure < 4 || reading.pressure > 9) add("Pressure", `${reading.pressure} bar`, "High");
  if (reading.rpm < machine.rpmMin || reading.rpm > machine.rpmMax) add("RPM", `${reading.rpm} RPM`, "High");

  return list;
}

function initLocalStore() {
  const now = new Date();
  const anomalies = [];
  const machines = DEMO_MACHINES.map((m, idx) => {
    const forceFault = m.machine_id === "M002" || m.machine_id === "M005";
    const latest = createSensorReading(m, now, forceFault);
    const found = evaluateAnomalies(m, latest);
    anomalies.push(...found);

    const status = found.some((a) => a.severity === "Critical" || a.severity === "High")
      ? "Critical"
      : found.length ? "Warning" : "Normal";

    return {
      ...m,
      operating_status: status,
      latest_sensor: latest,
      total_production: randInt(80, 120) + idx * 4,
      defective_parts: randInt(6, 16),
    };
  });

  localStore = { machines, anomalies, simulationRunning: false };
}

function addNewLocalReadings() {
  if (!localStore) initLocalStore();
  const now = new Date();
  localStore.machines.forEach((m) => {
    const latest = createSensorReading(m, now, false);
    m.latest_sensor = latest;
    m.total_production += randInt(1, 5);
    if (Math.random() < 0.15) m.defective_parts += 1;

    const found = evaluateAnomalies(m, latest);
    if (found.length) {
      localStore.anomalies.unshift(...found);
      m.operating_status = found.some((a) => a.severity === "Critical" || a.severity === "High") ? "Critical" : "Warning";
    } else {
      m.operating_status = "Normal";
    }
  });
}

async function apiFetch(url, options = undefined) {
  if (!useLocalDemo) {
    try {
      const res = await fetch(url, options);
      const data = await res.json();
      if (data && data.status === "ok") return data;
      throw new Error(data.message || "Backend error");
    } catch (err) {
      useLocalDemo = true;
      if (!localStore) initLocalStore();
      showToast("Running with randomized demo data (CSV dataset saved in data/).");
    }
  }
  if (!localStore) initLocalStore();

  if (url === "/api/dashboard") {
    const totalProd = localStore.machines.reduce((s, m) => s + m.total_production, 0);
    const defective = localStore.machines.reduce((s, m) => s + m.defective_parts, 0);
    const good = totalProd - defective;
    const activeAnoms = localStore.anomalies.filter((a) => a.alert_status === "Unresolved").length;

    return {
      status: "ok",
      kpis: {
        total_production: totalProd,
        good_parts: good,
        defective_parts: defective,
        quality_pass_rate: totalProd ? Number(((good * 100) / totalProd).toFixed(1)) : 0,
        active_anomalies: activeAnoms,
      },
      machine_stats: localStore.machines.map((m) => ({
        machine_name: m.machine_name,
        total_production: m.total_production,
        defect_percentage: m.total_production
          ? Number(((m.defective_parts * 100) / m.total_production).toFixed(1))
          : 0,
      })),
      machines: localStore.machines,
      recent_alerts: localStore.anomalies.slice(0, 10),
      simulation_running: localStore.simulationRunning,
    };
  }

  if (url === "/api/generate-data") {
    const body = options && options.body ? JSON.parse(options.body) : {};
    if (body.action === "reset") {
      initLocalStore();
      return { status: "ok", message: "Demo data reset." };
    }
    addNewLocalReadings();
    return { status: "ok", message: "Generated new randomized machine readings." };
  }

  if (url === "/api/start-simulation") {
    localStore.simulationRunning = true;
    return { status: "ok", message: "Live simulation started." };
  }

  if (url === "/api/stop-simulation") {
    localStore.simulationRunning = false;
    return { status: "ok", message: "Live simulation stopped." };
  }

  if (url === "/api/resolve-alert") {
    const body = options && options.body ? JSON.parse(options.body) : {};
    const target = localStore.anomalies.find((a) => a.anomaly_id === body.anomaly_id);
    if (target) target.alert_status = "Resolved";
    return { status: "ok", message: `Alert ${body.anomaly_id} resolved.` };
  }

  return { status: "ok" };
}

document.addEventListener("DOMContentLoaded", () => {
  loadDashboard();
});

async function loadDashboard() {
  try {
    const data = await apiFetch("/api/dashboard");
    const k = data.kpis;
    document.getElementById("kpiTotalProd").textContent = k.total_production;
    document.getElementById("kpiPassRate").textContent = `${k.quality_pass_rate}%`;
    document.getElementById("kpiDefectiveParts").textContent = k.defective_parts;
    document.getElementById("kpiActiveAnomalies").textContent = k.active_anomalies;

    updateDashboardCharts(data);

    document.getElementById("machinesTableBody").innerHTML = (data.machines || []).map((m) => {
      const s = m.latest_sensor || {};
      return `
        <tr>
          <td>${m.machine_id}</td>
          <td><strong>${m.machine_name}</strong></td>
          <td>${m.line_name}</td>
          <td>${statusBadge(m.operating_status)}</td>
          <td>${s.temperature ?? "—"}</td>
          <td>${s.vibration ?? "—"}</td>
          <td>${s.pressure ?? "—"}</td>
          <td>${s.rpm ?? "—"}</td>
          <td>${s.timestamp || "—"}</td>
        </tr>
      `;
    }).join("");

    document.getElementById("alertsTableBody").innerHTML = (data.recent_alerts || []).map((a) => `
      <tr>
        <td>${a.machine_name}</td>
        <td>${a.sensor_type}</td>
        <td>${a.observed_value}</td>
        <td>${statusBadge(a.severity)}</td>
        <td><strong>${a.possible_cause}</strong><br /><small style="color:#64748b;">${a.recommended_action}</small></td>
        <td>${statusBadge(a.alert_status)}</td>
        <td>
          ${a.alert_status === "Unresolved"
            ? `<button class="btn btn-success btn-sm" onclick="resolveAlert('${a.anomaly_id}')">Resolve</button>`
            : "—"}
        </td>
      </tr>
    `).join("") || "<tr><td colspan='7'>No anomalies detected.</td></tr>";

    setSimulationUI(Boolean(data.simulation_running));
  } catch (err) {
    showToast("Error: " + err.message, true);
  }
}

async function triggerDataGeneration(action) {
  const data = await apiFetch("/api/generate-data", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ action }),
  });
  showToast(data.message);
  loadDashboard();
}

async function startSimulation() {
  const data = await apiFetch("/api/start-simulation", { method: "POST" });
  setSimulationUI(true);
  showToast(data.message);
}

async function stopSimulation() {
  const data = await apiFetch("/api/stop-simulation", { method: "POST" });
  setSimulationUI(false);
  showToast(data.message);
}

async function resolveAlert(anomalyId) {
  const data = await apiFetch("/api/resolve-alert", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ anomaly_id: anomalyId }),
  });
  showToast(data.message);
  loadDashboard();
}

function setSimulationUI(isRunning) {
  const indicator = document.getElementById("liveIndicator");
  const statusText = document.getElementById("liveStatusText");
  const btnStart = document.getElementById("btnStartSim");
  const btnStop = document.getElementById("btnStopSim");

  indicator.classList.toggle("active", isRunning);
  statusText.textContent = isRunning ? "Live Monitoring Active" : "Simulation Stopped";
  btnStart.disabled = isRunning;
  btnStop.disabled = !isRunning;

  if (isRunning && !pollingTimer) {
    pollingTimer = setInterval(() => {
      if (useLocalDemo) addNewLocalReadings();
      loadDashboard();
    }, 4500);
  } else if (!isRunning && pollingTimer) {
    clearInterval(pollingTimer);
    pollingTimer = null;
  }
}

function statusBadge(value) {
  const lower = String(value || "").toLowerCase();
  return `<span class="badge badge-${lower}">${value}</span>`;
}

function showToast(message, isError = false) {
  const toast = document.getElementById("toastMessage");
  toast.textContent = message;
  toast.className = isError ? "toast error" : "toast info";
  setTimeout(() => {
    toast.className = "toast";
  }, 4000);
}
