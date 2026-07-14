import sqlite3, sys
conn = sqlite3.connect('stellar.db')
c = conn.cursor()
print('=== AUTO APPLY QUEUE (last 5 with failures) ===')
c.execute("SELECT id, job_title, job_url, status, failure_reason FROM auto_apply_queue WHERE failure_reason != '' ORDER BY updated_at DESC LIMIT 5")
rows = c.fetchall()
for row in rows:
    sys.stdout.buffer.write((repr(row) + '\n').encode('utf-8'))
print('\n=== AGENT LOGS (last 10) ===')
try:
    c.execute("SELECT agent, text, kind, created_at FROM agent_logs ORDER BY created_at DESC LIMIT 10")
    logs = c.fetchall()
    for log in logs:
        sys.stdout.buffer.write((repr(log) + '\n').encode('utf-8'))
except Exception as e:
    print(f'agent_logs error: {e}')
