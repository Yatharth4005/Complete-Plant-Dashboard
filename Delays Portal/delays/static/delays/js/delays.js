/* JSPL Delays Module — Interactive Charts & UI Handler */

document.addEventListener('DOMContentLoaded', function() {
    initCharts();
});

// Store chart instances globally to allow destroying/updating if needed
let charts = {};

function initCharts() {
    const data = window.delayChartData;
    if (!data) return;

    // Corporate Color Palettes (JSPL Navy & Orange variations)
    const orangePalette = [
        '#F47920', // Primary Corporate Orange
        '#E05300',
        '#FFA059',
        '#FFC296',
        '#FF8A3D'
    ];

    const mixedPalette = [
        '#F47920', // Orange
        '#002855', // Deep Corporate Navy
        '#0A3D62', // Lighter Navy
        '#10B981', // Green
        '#EF4444', // Red
        '#8B5CF6', // Purple
        '#F59E0B', // Amber
        '#3B82F6', // Blue
        '#6B7280'  // Gray
    ];

    // Standard Options
    const commonOptions = {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: {
                labels: {
                    font: {
                        family: "'Sora', sans-serif",
                        size: 11
                    }
                }
            },
            tooltip: {
                titleFont: {
                    family: "'Sora', sans-serif",
                    weight: 'bold'
                },
                bodyFont: {
                    family: "'JetBrains Mono', monospace"
                }
            }
        }
    };

    // ─────────────────────────────────────────────────────────
    // CHART 1: DAILY DOWNTIME TREND (Stacked Bar Chart by Agency)
    const trendCtx = document.getElementById('trendChart');
    if (trendCtx) {
        const dailyDatasets = (data.dailyDatasets || []).map((dataset, index) => {
            const color = mixedPalette[index % mixedPalette.length];
            return {
                label: dataset.label,
                data: dataset.data,
                backgroundColor: color,
                borderColor: color,
                borderWidth: 1,
                borderRadius: 4
            };
        });

        charts.trend = new Chart(trendCtx, {
            type: 'bar',
            data: {
                labels: data.dailyLabels,
                datasets: dailyDatasets
            },
            options: Object.assign({}, commonOptions, {
                plugins: {
                    legend: {
                        display: true,
                        position: 'right',
                        labels: {
                            boxWidth: 12,
                            padding: 10,
                            font: { family: "'Sora', sans-serif" }
                        }
                    }
                },
                scales: {
                    y: {
                        stacked: true,
                        beginAtZero: true,
                        grid: { color: '#E5E7EB' },
                        title: {
                            display: true,
                            text: 'Minutes',
                            font: { family: "'Sora', sans-serif", weight: 'bold' }
                        },
                        ticks: { font: { family: "'JetBrains Mono', monospace" } }
                    },
                    x: {
                        stacked: true,
                        grid: { display: false },
                        ticks: {
                            font: { family: "'JetBrains Mono', monospace", size: 10 },
                            maxRotation: 45,
                            minRotation: 45
                        }
                    }
                }
            })
        });
    }

    // ─────────────────────────────────────────────────────────
    // CHART 2: AGENCY DISTRIBUTION SHARE (Doughnut Chart)
    // ─────────────────────────────────────────────────────────
    const agencyCtx = document.getElementById('agencyChart');
    if (agencyCtx) {
        charts.agency = new Chart(agencyCtx, {
            type: 'doughnut',
            data: {
                labels: data.agencyLabels,
                datasets: [{
                    data: data.agencyData,
                    backgroundColor: mixedPalette,
                    borderWidth: 2,
                    borderColor: '#FFFFFF',
                    hoverOffset: 8
                }]
            },
            options: Object.assign({}, commonOptions, {
                plugins: {
                    legend: {
                        position: 'right',
                        labels: {
                            boxWidth: 12,
                            padding: 15,
                            font: { family: "'Sora', sans-serif" }
                        }
                    }
                },
                cutout: '60%'
            })
        });
    }

    // ─────────────────────────────────────────────────────────
    // CHART 3: TOP BOTTLENECK EQUIPMENTS (Horizontal Bar Chart)
    // ─────────────────────────────────────────────────────────
    const equipCtx = document.getElementById('equipmentChart');
    if (equipCtx) {
        charts.equipment = new Chart(equipCtx, {
            type: 'bar',
            data: {
                labels: data.equipLabels,
                datasets: [{
                    label: 'Cumulative Downtime (Mins)',
                    data: data.equipData,
                    backgroundColor: 'rgba(10, 61, 98, 0.85)',
                    borderColor: '#0A3D62',
                    borderWidth: 1.5,
                    borderRadius: 4,
                    hoverBackgroundColor: '#002855'
                }]
            },
            options: Object.assign({}, commonOptions, {
                indexAxis: 'y', // Makes the bar chart horizontal
                plugins: {
                    legend: { display: false }
                },
                scales: {
                    x: {
                        beginAtZero: true,
                        grid: { color: '#E5E7EB' },
                        title: {
                            display: true,
                            text: 'Minutes',
                            font: { family: "'Sora', sans-serif", weight: 'bold' }
                        },
                        ticks: { font: { family: "'JetBrains Mono', monospace" } }
                    },
                    y: {
                        grid: { display: false },
                        ticks: {
                            font: { family: "'Sora', sans-serif", size: 11 }
                        }
                    }
                }
            })
        });
    }
    // NOTE: Pareto chart is now dynamically handled inside _pareto_content.html and _pareto_agency_content.html
}
