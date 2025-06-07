document.addEventListener('DOMContentLoaded', () => {
    const priceCtx = document.getElementById('priceChart').getContext('2d');
    const fgCtx = document.getElementById('fgChart').getContext('2d');

    let priceChart, fgChart;

    fetch('/api/chart-data')
        .then(r => r.json())
        .then(data => {
            priceChart = new Chart(priceCtx, {
                type: 'line',
                data: {
                    labels: data.dates,
                    datasets: [{
                        label: 'Prix BTC (USD)',
                        data: data.prices,
                        borderColor: 'blue',
                        fill: false
                    }]
                }
            });

            fgChart = new Chart(fgCtx, {
                type: 'line',
                data: {
                    labels: data.dates,
                    datasets: [{
                        label: 'Fear & Greed',
                        data: data.fg,
                        borderColor: 'red',
                        fill: false
                    }]
                }
            });
        });

    const freq = document.getElementById('frequency');
    const dayWeekLabel = document.getElementById('day_week_label');
    const dayMonthLabel = document.getElementById('day_month_label');

    freq.addEventListener('change', () => {
        if (freq.value === 'weekly') {
            dayWeekLabel.style.display = '';
            dayMonthLabel.style.display = 'none';
        } else {
            dayWeekLabel.style.display = 'none';
            dayMonthLabel.style.display = '';
        }
    });

    document.getElementById('calc_btn').addEventListener('click', () => {
        const payload = {
            start_date: document.getElementById('start_date').value,
            amount: document.getElementById('amount').value,
            frequency: freq.value,
            day: freq.value === 'weekly' ? document.getElementById('day_week').value : document.getElementById('day_month').value
        };

        fetch('/api/dca', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        })
        .then(r => r.json())
        .then(res => {
            document.getElementById('dca_result').textContent = JSON.stringify(res, null, 2);
        });
    });
});
