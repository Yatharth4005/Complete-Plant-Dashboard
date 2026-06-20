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

    // Helper to format minutes with commas
    function formatMins(mins) {
        return Math.round(mins).toLocaleString() + ' mins';
    }

    // ─────────────────────────────────────────────────────────
    // CHART 1: DAILY DOWNTIME TREND (Stacked Bar Chart by Agency)
    const trendCtx = document.getElementById('trendChart');
    const backBtn = document.getElementById('backToOverallBtn');
    const trendTitle = document.getElementById('trendChartTitle');
    const chartContainer = document.getElementById('trendChartContainer');

    if (trendCtx) {
        const dailyDatasets = (data.dailyDatasets || []).map((dataset, index) => {
            const color = mixedPalette[index % mixedPalette.length];
            const sum = dataset.data.reduce((a, b) => a + b, 0);
            return {
                label: `${dataset.label} (${formatMins(sum)})`,
                originalLabel: dataset.label,
                data: dataset.data,
                backgroundColor: color,
                borderColor: color,
                borderWidth: 1,
                borderRadius: 4
            };
        });

        let currentView = 'overall';

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
                        position: window.innerWidth > 1024 ? 'right' : 'bottom',
                        labels: {
                            boxWidth: 12,
                            padding: 15,
                            font: { family: "'Sora', sans-serif", size: 11 }
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
                },
                onClick: (event, elements) => {
                    // Check if we have drill-down data and are in overall view
                    if (!data.deptTrends || currentView !== 'overall') return;
                    
                    if (elements && elements.length > 0) {
                        const index = elements[0].index;
                        const deptCode = charts.trend.data.labels[index];
                        showDeptDetail(deptCode);
                    }
                }
            })
        });

        function showDeptDetail(deptCode) {
            const deptData = data.deptTrends[deptCode];
            if (!deptData) return;

            currentView = 'dept';

            // Swipe off (slide left and fade out)
            if (chartContainer) {
                chartContainer.style.transform = 'translateX(-100%)';
                chartContainer.style.opacity = '0';
            }

            setTimeout(() => {
                if (trendTitle) {
                    trendTitle.textContent = `📈 Daily Downtime Trend: ${deptData.dept_name} (Mins)`;
                }
                if (backBtn) {
                    backBtn.style.display = 'inline-block';
                }

                // Rebuild datasets with correct sums for the legend values
                const newDatasets = deptData.datasets.map((dataset, index) => {
                    const color = mixedPalette[index % mixedPalette.length];
                    const sum = dataset.data.reduce((a, b) => a + b, 0);
                    return {
                        label: `${dataset.label} (${formatMins(sum)})`,
                        originalLabel: dataset.label,
                        data: dataset.data,
                        backgroundColor: color,
                        borderColor: color,
                        borderWidth: 1,
                        borderRadius: 4
                    };
                });

                charts.trend.data.labels = deptData.labels;
                charts.trend.data.datasets = newDatasets;
                charts.trend.update();

                // Swipe on (slide in from right)
                if (chartContainer) {
                    chartContainer.style.transform = 'translateX(0)';
                    chartContainer.style.opacity = '1';
                }
            }, 400);
        }

        if (backBtn) {
            backBtn.addEventListener('click', () => {
                currentView = 'overall';

                // Swipe off (slide right and fade out)
                if (chartContainer) {
                    chartContainer.style.transform = 'translateX(100%)';
                    chartContainer.style.opacity = '0';
                }

                setTimeout(() => {
                    if (trendTitle) {
                        trendTitle.textContent = '📈 Department Downtime Comparison (Mins)';
                    }
                    if (backBtn) {
                        backBtn.style.display = 'none';
                    }

                    charts.trend.data.labels = data.dailyLabels;
                    charts.trend.data.datasets = dailyDatasets;
                    charts.trend.update();

                    // Swipe on
                    if (chartContainer) {
                        chartContainer.style.transform = 'translateX(0)';
                        chartContainer.style.opacity = '1';
                    }
                }, 400);
            });
        }
    }

    // ─────────────────────────────────────────────────────────
    // CHART 2: AGENCY DISTRIBUTION SHARE (Doughnut Chart)
    // ─────────────────────────────────────────────────────────
    const agencyCtx = document.getElementById('agencyChart');
    if (agencyCtx) {
        const agencyLabelsWithValues = (data.agencyLabels || []).map((lbl, idx) => {
            const val = data.agencyData[idx] || 0;
            return `${lbl} (${formatMins(val)})`;
        });

        charts.agency = new Chart(agencyCtx, {
            type: 'doughnut',
            data: {
                labels: agencyLabelsWithValues,
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
                        position: 'bottom', // Put legend at bottom so it is completely visible
                        labels: {
                            boxWidth: 12,
                            padding: 10,
                            font: { family: "'Sora', sans-serif", size: 11 }
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
