(function ($) {
    // ── Theme palette (mirrors theme.css) ───────────────────────────────
    var palette = {
        success:     '#16a34a',
        successSoft: 'rgba(22,163,74,0.10)',
        danger:      '#dc2626',
        dangerSoft:  'rgba(220,38,38,0.10)',
        slate400:    '#94a3b8',
        slate200:    '#e2e8f0',
        slate500:    '#64748b',
        slate900:    '#0f172a'
    };

    // Chart.js global defaults
    if (typeof Chart !== 'undefined') {
        Chart.defaults.font.family = 'Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';
        Chart.defaults.font.size = 12;
        Chart.defaults.color = palette.slate500;
        Chart.defaults.borderColor = palette.slate200;
    }

    // ── Gateway state probe ─────────────────────────────────────────────
    // Show only when state is not OK — successful state is already conveyed
    // by the green dot on the gateway tile, no need to spam a toast.
    var gw_state = function () {
        $.ajax({
            type: "GET",
            url: window.location.pathname + 'manage/',
            data: { s: 'gw_state' },
            success: function (data) {
                var $tile = $('#binding_status');
                $tile.removeClass('up down');
                $tile.addClass(data.status ? 'up' : 'down');
                $('#binding_status_text').text(' · ' + (data.status ? 'connected' : 'unreachable'));
                if (!data.status && typeof toastr !== 'undefined') {
                    toastr.warning(data.message, { closeButton: true, progressBar: true, positionClass: 'toast-top-right' });
                }
            },
            error: function (jqXHR) {
                $('#binding_status').addClass('down');
                $('#binding_status_text').text(' · unreachable');
                try {
                    if (typeof toastr !== 'undefined') {
                        toastr.error(JSON.parse(jqXHR.responseText).message, { closeButton: true, progressBar: true, positionClass: 'toast-top-right' });
                    }
                } catch (e) { /* swallow */ }
            }
        });
    };
    gw_state();

    // ── Charts ──────────────────────────────────────────────────────────
    var timelineChart = null;
    var donutChart = null;
    var currentGrouping = 'daily';

    function initTimelineChart(labels, successData, failedData) {
        var ctx = document.getElementById('timelineChart');
        if (!ctx) return;
        if (timelineChart) timelineChart.destroy();

        timelineChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [
                    {
                        label: 'Success',
                        data: successData,
                        borderColor: palette.success,
                        backgroundColor: palette.successSoft,
                        borderWidth: 2,
                        tension: 0.35,
                        fill: true,
                        pointRadius: 0,
                        pointHoverRadius: 4,
                        pointHoverBackgroundColor: palette.success,
                        pointHoverBorderColor: '#fff',
                        pointHoverBorderWidth: 2
                    },
                    {
                        label: 'Failed',
                        data: failedData,
                        borderColor: palette.danger,
                        backgroundColor: palette.dangerSoft,
                        borderWidth: 2,
                        tension: 0.35,
                        fill: true,
                        pointRadius: 0,
                        pointHoverRadius: 4,
                        pointHoverBackgroundColor: palette.danger,
                        pointHoverBorderColor: '#fff',
                        pointHoverBorderWidth: 2
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: { mode: 'index', intersect: false },
                plugins: {
                    legend: {
                        display: true,
                        position: 'top',
                        align: 'end',
                        labels: { boxWidth: 8, boxHeight: 8, usePointStyle: true, padding: 12 }
                    },
                    tooltip: {
                        backgroundColor: palette.slate900,
                        titleColor: '#fff',
                        bodyColor: '#fff',
                        cornerRadius: 8,
                        padding: 10,
                        boxPadding: 4,
                        callbacks: {
                            label: function (context) {
                                return context.dataset.label + ': ' + context.parsed.y.toLocaleString();
                            }
                        }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        grid: { color: palette.slate200, drawBorder: false },
                        ticks: { callback: function (v) { return v.toLocaleString(); } },
                        border: { display: false }
                    },
                    x: {
                        grid: { display: false },
                        border: { display: false },
                        ticks: { maxRotation: 0 }
                    }
                }
            }
        });
    }

    function initDonutChart(successCount, failedCount, unknownCount) {
        var ctx = document.getElementById('donutChart');
        if (!ctx) return;
        if (donutChart) donutChart.destroy();

        donutChart = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: ['Success', 'Failed', 'Unknown'],
                datasets: [{
                    data: [successCount, failedCount, unknownCount],
                    backgroundColor: [palette.success, palette.danger, palette.slate400],
                    borderWidth: 0,
                    hoverOffset: 6
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: '70%',
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        backgroundColor: palette.slate900,
                        titleColor: '#fff',
                        bodyColor: '#fff',
                        cornerRadius: 8,
                        padding: 10,
                        callbacks: {
                            label: function (context) {
                                var label = context.label || '';
                                var value = context.parsed || 0;
                                var total = context.dataset.data.reduce(function (a, b) { return a + b; }, 0);
                                var pct = total > 0 ? ((value / total) * 100).toFixed(1) : 0;
                                return label + ': ' + value.toLocaleString() + ' (' + pct + '%)';
                            }
                        }
                    }
                }
            }
        });
    }

    function loadTimelineData(grouping) {
        $.ajax({
            type: "GET",
            url: window.location.pathname + 'manage/',
            data: { s: 'submit_log_timeline', grouping: grouping },
            beforeSend: function () { $('.grouping-buttons button').prop('disabled', true); },
            success: function (data) {
                if (data.status === 'success') {
                    initTimelineChart(data.labels, data.success, data.failed);
                    currentGrouping = grouping;
                }
            },
            error: function (_, __, errorThrown) {
                console.error('Failed to load timeline data:', errorThrown);
            },
            complete: function () { $('.grouping-buttons button').prop('disabled', false); }
        });
    }

    if (typeof chartData !== 'undefined') {
        initTimelineChart(chartData.timeline.labels, chartData.timeline.success, chartData.timeline.failed);
        initDonutChart(chartData.donut.success, chartData.donut.failed, chartData.donut.unknown);
    }

    $('.grouping-buttons button').on('click', function () {
        var grouping = $(this).data('grouping');
        $('.grouping-buttons button').removeClass('active');
        $(this).addClass('active');
        loadTimelineData(grouping);
    });

})(jQuery);
