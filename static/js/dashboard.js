/**
 * dashboard.js – Dashboard charts and metrics for the Taxi Accounting System
 * 
 * Initialises Chart.js charts for profit trends, expense breakdowns,
 * contract progress, and other dashboard visualisations.
 */

(function () {
    'use strict';

    /**
     * Initialise all dashboard charts.
     * Looks for canvas elements with data-chart attributes.
     */
    function initDashboardCharts() {
        // Profit trend chart
        const profitCtx = document.getElementById('chart-profit-trend');
        if (profitCtx) {
            const labels = JSON.parse(profitCtx.dataset.labels || '[]');
            const income = JSON.parse(profitCtx.dataset.income || '[]');
            const expenses = JSON.parse(profitCtx.dataset.expenses || '[]');
            const profit = JSON.parse(profitCtx.dataset.profit || '[]');

            new Chart(profitCtx, {
                type: 'line',
                data: {
                    labels: labels,
                    datasets: [
                        {
                            label: 'Income',
                            data: income,
                            borderColor: '#38a169',
                            backgroundColor: 'rgba(56, 161, 105, 0.1)',
                            fill: true,
                            tension: 0.4,
                        },
                        {
                            label: 'Expenses',
                            data: expenses,
                            borderColor: '#e53e3e',
                            backgroundColor: 'rgba(229, 62, 62, 0.1)',
                            fill: true,
                            tension: 0.4,
                        },
                        {
                            label: 'Profit',
                            data: profit,
                            borderColor: '#2b6cb0',
                            backgroundColor: 'rgba(43, 108, 176, 0.1)',
                            fill: true,
                            tension: 0.4,
                        },
                    ],
                },
                options: {
                    responsive: true,
                    plugins: {
                        legend: { position: 'bottom' },
                        tooltip: {
                            callbacks: {
                                label: function (ctx) {
                                    return ctx.dataset.label + ': M ' + ctx.parsed.y.toFixed(2);
                                },
                            },
                        },
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            ticks: {
                                callback: function (value) {
                                    return 'M ' + value.toFixed(2);
                                },
                            },
                        },
                    },
                },
            });
        }

        // Expense breakdown pie/doughnut chart
        const expenseCtx = document.getElementById('chart-expense-breakdown');
        if (expenseCtx) {
            const labels = JSON.parse(expenseCtx.dataset.labels || '[]');
            const values = JSON.parse(expenseCtx.dataset.values || '[]');

            new Chart(expenseCtx, {
                type: 'doughnut',
                data: {
                    labels: labels,
                    datasets: [
                        {
                            data: values,
                            backgroundColor: [
                                '#2b6cb0',
                                '#38a169',
                                '#d69e2e',
                                '#e53e3e',
                                '#805ad5',
                                '#ed8936',
                                '#319795',
                                '#718096',
                            ],
                        },
                    ],
                },
                options: {
                    responsive: true,
                    plugins: {
                        legend: { position: 'bottom' },
                        tooltip: {
                            callbacks: {
                                label: function (ctx) {
                                    const total = ctx.dataset.data.reduce((a, b) => a + b, 0);
                                    const pct = ((ctx.parsed / total) * 100).toFixed(1);
                                    return ctx.label + ': M ' + ctx.parsed.toFixed(2) + ' (' + pct + '%)';
                                },
                            },
                        },
                    },
                },
            });
        }

        // Contract progress bar chart
        const contractCtx = document.getElementById('chart-contract-progress');
        if (contractCtx) {
            const labels = JSON.parse(contractCtx.dataset.labels || '[]');
            const progress = JSON.parse(contractCtx.dataset.progress || '[]');
            const targets = JSON.parse(contractCtx.dataset.targets || '[]');

            new Chart(contractCtx, {
                type: 'bar',
                data: {
                    labels: labels,
                    datasets: [
                        {
                            label: 'Progress (%)',
                            data: progress,
                            backgroundColor: progress.map(function (v) {
                                return v >= 100 ? '#38a169' : v >= 50 ? '#d69e2e' : '#e53e3e';
                            }),
                            borderRadius: 6,
                        },
                    ],
                },
                options: {
                    responsive: true,
                    indexAxis: 'y',
                    plugins: {
                        legend: { display: false },
                        tooltip: {
                            callbacks: {
                                label: function (ctx) {
                                    return ctx.parsed.x.toFixed(1) + '%';
                                },
                            },
                        },
                    },
                    scales: {
                        x: {
                            beginAtZero: true,
                            max: 100,
                            title: { display: true, text: 'Progress (%)' },
                        },
                    },
                },
            });
        }

        // Cash flow chart
        const cashFlowCtx = document.getElementById('chart-cash-flow');
        if (cashFlowCtx) {
            const labels = JSON.parse(cashFlowCtx.dataset.labels || '[]');
            const cashIn = JSON.parse(cashFlowCtx.dataset.cashIn || '[]');
            const cashOut = JSON.parse(cashFlowCtx.dataset.cashOut || '[]');
            const balance = JSON.parse(cashFlowCtx.dataset.balance || '[]');

            new Chart(cashFlowCtx, {
                type: 'bar',
                data: {
                    labels: labels,
                    datasets: [
                        {
                            label: 'Cash In',
                            data: cashIn,
                            backgroundColor: 'rgba(56, 161, 105, 0.7)',
                            borderRadius: 4,
                        },
                        {
                            label: 'Cash Out',
                            data: cashOut,
                            backgroundColor: 'rgba(229, 62, 62, 0.7)',
                            borderRadius: 4,
                        },
                        {
                            label: 'Balance',
                            data: balance,
                            type: 'line',
                            borderColor: '#2b6cb0',
                            backgroundColor: 'rgba(43, 108, 176, 0.1)',
                            fill: true,
                            tension: 0.4,
                            pointRadius: 4,
                        },
                    ],
                },
                options: {
                    responsive: true,
                    plugins: {
                        legend: { position: 'bottom' },
                        tooltip: {
                            callbacks: {
                                label: function (ctx) {
                                    return ctx.dataset.label + ': M ' + ctx.parsed.y.toFixed(2);
                                },
                            },
                        },
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            ticks: {
                                callback: function (value) {
                                    return 'M ' + value.toFixed(2);
                                },
                            },
                        },
                    },
                },
            });
        }
    }

    // Initialise on DOM ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initDashboardCharts);
    } else {
        initDashboardCharts();
    }
})();