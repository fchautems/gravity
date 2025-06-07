import os
import sqlite3
from datetime import datetime

import pandas as pd
from flask import Flask, jsonify, render_template, request

DB_FILE = 'btc.db'
CSV_FILE = 'data.csv'

app = Flask(__name__)

DAY_MAP = {
    'lun.': 0,
    'mar.': 1,
    'mer.': 2,
    'jeu.': 3,
    'ven.': 4,
    'sam.': 5,
    'dim.': 6,
}


def init_db():
    if not os.path.exists(DB_FILE):
        df = pd.read_csv(CSV_FILE)
        df['Price'] = df['Price'].str.replace(',', '.').astype(float)
        df['Date'] = pd.to_datetime(df['Date'], format='%d.%m.%Y').dt.strftime('%Y-%m-%d')
        df['DayOfWeek'] = df['Jour Semaine'].map(DAY_MAP)
        conn = sqlite3.connect(DB_FILE)
        df.to_sql('btc', conn, index=False, if_exists='replace')
        conn.close()


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/data')
def api_data():
    date_str = request.args.get('date')
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute('SELECT Price, "Fear and Greed" FROM btc WHERE Date=?', (date_str,))
    row = cur.fetchone()
    conn.close()
    if row:
        return jsonify({'date': date_str, 'price': row[0], 'fear_greed': row[1]})
    return jsonify({'error': 'Date not found'}), 404


@app.route('/api/chart-data')
def chart_data():
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql('SELECT Date, Price, "Fear and Greed" FROM btc ORDER BY Date', conn)
    conn.close()
    return jsonify({
        'dates': df['Date'].tolist(),
        'prices': df['Price'].tolist(),
        'fg': df['Fear and Greed'].tolist()
    })


@app.route('/api/dca', methods=['POST'])
def api_dca():
    data = request.get_json()
    amount = float(data.get('amount', 0))
    start_date = data.get('start_date')
    frequency = data.get('frequency')
    day_param = data.get('day')

    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql('SELECT Date, Price FROM btc WHERE Date >= ? ORDER BY Date', conn, params=(start_date,))
    last_price = pd.read_sql('SELECT Price FROM btc ORDER BY Date DESC LIMIT 1', conn)['Price'][0]
    conn.close()

    df['Date'] = pd.to_datetime(df['Date'])
    if frequency == 'weekly':
        target = int(day_param)
        df = df[df['Date'].dt.weekday == target]
    elif frequency == 'monthly':
        target = int(day_param)
        df = df[df['Date'].dt.day == target]

    num_purchases = len(df)
    total_invested = num_purchases * amount
    btc_total = (amount / df['Price']).sum() if num_purchases > 0 else 0
    final_value = btc_total * last_price
    net_return = final_value - total_invested

    result = {
        'purchases': num_purchases,
        'total_invested': round(total_invested, 2),
        'btc_total': round(btc_total, 8),
        'final_value': round(final_value, 2),
        'net_return': round(net_return, 2)
    }
    return jsonify(result)


if __name__ == '__main__':
    init_db()
    app.run(debug=True)
