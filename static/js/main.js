/**
 * FitTrack Gym Management System - Frontend JavaScript
 * Handles dynamic workout exercise rows, alert auto-dismiss,
 * confirmation dialogs, and Chart.js initialization for progress tracking.
 */

document.addEventListener("DOMContentLoaded", function () {
  // 1. Mobile Sidebar Toggle
  const sidebarToggle = document.getElementById("sidebar-toggle");
  const sidebar = document.querySelector(".sidebar");
  if (sidebarToggle && sidebar) {
    sidebarToggle.addEventListener("click", function () {
      sidebar.classList.toggle("open");
    });
  }

  // 2. Auto-dismiss Flash Alerts after 5 seconds
  const alerts = document.querySelectorAll(".alert");
  alerts.forEach(function (alert) {
    const closeBtn = alert.querySelector(".alert-close");
    if (closeBtn) {
      closeBtn.addEventListener("click", function () {
        alert.style.opacity = "0";
        setTimeout(() => alert.remove(), 250);
      });
    }
    setTimeout(function () {
      alert.style.transition = "opacity 0.4s ease";
      alert.style.opacity = "0";
      setTimeout(() => alert.remove(), 400);
    }, 6000);
  });

  // 3. Dynamic Exercise Row Management (Workout Logging)
  const container = document.getElementById("exercises-container");
  const addBtn = document.getElementById("btn-add-exercise");

  if (container && addBtn) {
    addBtn.addEventListener("click", function () {
      const row = document.createElement("div");
      row.className = "exercise-row";
      row.innerHTML = `
        <div>
          <input type="text" name="exercise_name[]" class="form-control" placeholder="Exercise name (e.g. Incline Dumbbell Press)" required />
        </div>
        <div>
          <input type="number" name="sets[]" class="form-control" placeholder="Sets" min="1" max="50" required />
        </div>
        <div>
          <input type="number" name="reps[]" class="form-control" placeholder="Reps" min="1" max="200" required />
        </div>
        <div>
          <input type="number" step="0.5" name="weight[]" class="form-control" placeholder="Weight (kg)" min="0" required />
        </div>
        <div>
          <button type="button" class="btn-remove-row" title="Remove Exercise">&times;</button>
        </div>
      `;
      container.appendChild(row);
      attachRemoveHandler(row.querySelector(".btn-remove-row"));
    });

    // Attach listener to any initial remove buttons
    container.querySelectorAll(".btn-remove-row").forEach(attachRemoveHandler);
  }

  function attachRemoveHandler(btn) {
    if (!btn) return;
    btn.addEventListener("click", function () {
      const rows = container.querySelectorAll(".exercise-row");
      if (rows.length > 1) {
        btn.closest(".exercise-row").remove();
      } else {
        alert("A workout log must contain at least one exercise.");
      }
    });
  }

  // 4. Progress Tracker Chart.js Initialization
  const progressCanvas = document.getElementById("progressChart");
  if (progressCanvas && window.Chart && window.progressChartData) {
    const chartData = window.progressChartData;
    new Chart(progressCanvas.getContext("2d"), {
      type: "line",
      data: {
        labels: chartData.dates,
        datasets: [
          {
            label: "Weight (kg)",
            data: chartData.weights,
            borderColor: "#1a8c87",
            backgroundColor: "rgba(26, 140, 135, 0.12)",
            borderWidth: 3,
            fill: true,
            tension: 0.3,
            pointBackgroundColor: "#142239",
            pointBorderColor: "#1a8c87",
            pointRadius: 6,
            pointHoverRadius: 8
          },
          ...(chartData.bodyFats && chartData.bodyFats.length > 0 && chartData.bodyFats[0] !== null
            ? [
                {
                  label: "Body Fat %",
                  data: chartData.bodyFats,
                  borderColor: "#f59e0b",
                  backgroundColor: "rgba(245, 158, 11, 0.08)",
                  borderWidth: 2,
                  borderDash: [5, 5],
                  tension: 0.3,
                  pointBackgroundColor: "#f59e0b",
                  pointRadius: 5
                }
              ]
            : [])
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            display: true,
            position: "top",
            labels: {
              boxWidth: 14,
              font: { weight: "600", family: "Inter" }
            }
          },
          tooltip: {
            backgroundColor: "#142239",
            titleFont: { weight: "bold" },
            padding: 10,
            cornerRadius: 6
          }
        },
        scales: {
          y: {
            beginAtZero: false,
            grid: { color: "#edf2f7" },
            title: { display: true, text: "Metric Value" }
          },
          x: {
            grid: { display: false },
            title: { display: true, text: "Check-in Date" }
          }
        }
      }
    });
  }
});

// Global delete confirmation prompt
function confirmDelete(entityName) {
  return confirm(`Are you sure you want to delete this ${entityName}? This action cannot be undone.`);
}
