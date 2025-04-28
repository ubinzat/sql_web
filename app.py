from flask import Flask, request, render_template_string, session, redirect, url_for
import sqlite3
from datetime import datetime
import os

app = Flask(__name__)
app.secret_key = 'sir-gibi-bir-sifre'
DB_NAME = 'example.db'
LOG_FILE = 'query_logs.txt'

# --- Görevler Tanımı ---
TASKS = [
    {
        'description': "Tüm öğrencileri listele",
        'expected': "SELECT * FROM ogrenciler"
    },
    {
        'description': "21 yaşından büyük öğrencileri listele",
        'expected': "SELECT * FROM ogrenciler WHERE yas > 21"
    },
    {
        'description': "Soyadı 'Demir' olan öğrencileri listele",
        'expected': "SELECT * FROM ogrenciler WHERE soyad = 'Demir'"
    },
    {
        'description': "Yaşı 10'dan küçük öğrencileri listele",
        'expected': "SELECT * FROM ogrenciler WHERE yas < 10"
    }
]

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''
    CREATE TABLE IF NOT EXISTS ogrenciler (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ad TEXT NOT NULL,
        soyad TEXT NOT NULL,
        yas INTEGER
    )
    ''')
    c.execute("DELETE FROM ogrenciler")
    c.executemany('INSERT INTO ogrenciler (ad, soyad, yas) VALUES (?, ?, ?)', [
        ('Ali', 'Yilmaz', 21),
        ('Ayse', 'Demir', 22),
        ('Mehmet', 'Kara', 20),
        ('Fatma', 'Celik', 23),
        ('Uğur', 'Binzat', 27),
        ('Ayçe', 'Ölmez', 22),
        ('Leo', 'Binzat', 2),
        ('Atlas', 'Ölmez', 8)
    ])
    conn.commit()
    conn.close()

# --- HTML Şablonu ---
HTML = """
<!doctype html>
<title>SQL Sorgu Deneme</title>
<h2>Görev: {{ task['description'] }}</h2>
<p>Puanınız: {{ score }}</p>

<div style="margin-bottom:20px;">
  <button onclick="insertQuery('SELECT * FROM ogrenciler;')">Tüm Öğrencileri Listele</button>
  <a href="{{ url_for('showdata') }}"><button>Tüm Veritabanını Göster</button></a>
  <a href="{{ url_for('report') }}"><button>Görev Raporunu Görüntüle</button></a>
</div>

<form method=post>
  <textarea id="query" name="query" rows=6 cols=80>{{ selected_query }}</textarea><br><br>
  <input type=submit value="Sorguyu Çalıştır">
</form>

{% if feedback %}
<p style="color:green;">{{ feedback }}</p>
{% endif %}
{% if result %}
<h3>Sonuçlar:</h3>
<table border=1>
<tr>
  {% for col in columns %}
    <th>{{ col }}</th>
  {% endfor %}
</tr>
{% for row in result %}
<tr>
  {% for cell in row %}
    <td>{{ cell }}</td>
  {% endfor %}
</tr>
{% endfor %}
</table>
{% endif %}
{% if error %}
<p style="color:red;">{{ error }}</p>
{% endif %}

<script>
function insertQuery(sql) {
    document.getElementById('query').value = sql;
}
</script>
"""

# --- Anasayfa ---
@app.route('/', methods=['GET', 'POST'])
def index():
    if 'score' not in session:
        session['score'] = 0
    if 'task_index' not in session:
        session['task_index'] = 0
    if 'completed_tasks' not in session:
        session['completed_tasks'] = []

    current_task = TASKS[session['task_index']]
    result = None
    columns = []
    error = None
    feedback = None
    selected_query = ''

    if request.method == 'POST':
        query = request.form['query']
        selected_query = query
        if not query.strip().lower().startswith('select'):
            error = 'Sadece SELECT sorgularına izin veriliyor.'
        else:
            try:
                conn = sqlite3.connect(DB_NAME)
                c = conn.cursor()
                c.execute(query)
                columns = [description[0] for description in c.description]
                result = c.fetchall()
                conn.close()
                # --- Sorgu kaydı ---
                with open(LOG_FILE, 'a', encoding='utf-8') as f:
                    f.write(f'[{datetime.now()}] {query}\n')

                # --- Doğruluk Kontrolü ---
                expected_query = current_task['expected'].lower().replace(' ', '').replace(';', '')
                student_query = query.lower().replace(' ', '').replace(';', '')
                if student_query.startswith(expected_query):
                    if current_task['description'] not in session['completed_tasks']:
                        session['score'] += 1
                        session['completed_tasks'].append(current_task['description'])
                    feedback = "Tebrikler! Doğru sorgu. 1 puan kazandınız."
                    session['task_index'] += 1
                    if session['task_index'] >= len(TASKS):
                        feedback += " Tüm görevleri tamamladınız!"
                        session['task_index'] = 0
                else:
                    feedback = "Henüz doğru sorgu değil. Tekrar deneyin."
            except Exception as e:
                error = f'Hata: {e}'

    return render_template_string(HTML, result=result, columns=columns, error=error,
                                  feedback=feedback, score=session['score'],
                                  task=TASKS[session['task_index']], selected_query=selected_query)

# --- Tüm Veritabanını Gösterme ---
@app.route('/showdata')
def showdata():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT * FROM ogrenciler")
    columns = [description[0] for description in c.description]
    result = c.fetchall()
    conn.close()

    return render_template_string("""
    <h2>Veritabanı İçeriği</h2>
    <a href="{{ url_for('index') }}">Ana Sayfa</a>
    <table border=1>
    <tr>
      {% for col in columns %}
        <th>{{ col }}</th>
      {% endfor %}
    </tr>
    {% for row in result %}
    <tr>
      {% for cell in row %}
        <td>{{ cell }}</td>
      {% endfor %}
    </tr>
    {% endfor %}
    </table>
    """, result=result, columns=columns)

# --- Görev Tamamlama Raporu ---
@app.route('/report')
def report():
    completed = session.get('completed_tasks', [])
    return render_template_string("""
    <h2>Görev Tamamlama Raporu</h2>
    <a href="{{ url_for('index') }}">Ana Sayfa</a>
    <ul>
    {% for task in completed %}
      <li>{{ task }}</li>
    {% endfor %}
    </ul>
    """, completed=completed)

if __name__ == '__main__':
    init_db()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
