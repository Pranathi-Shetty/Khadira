"""Check data counts in the demo database."""
import os, json
os.environ['DATABASE_URL'] = 'sqlite:///./mill_demo.db'
from mill.main import create_app
from fastapi.testclient import TestClient
app = create_app()
client = TestClient(app, raise_server_exceptions=False)
r = client.post('/api/auth/login', json={'username': 'admin', 'password': 'khadira2026!'})
cookies = r.cookies

def count(ep):
    r = client.get(ep, cookies=cookies)
    if r.status_code == 200:
        data = r.json()
        if isinstance(data, list):
            return len(data)
        elif isinstance(data, dict) and 'items' in data:
            return data.get('total', len(data['items']))
        return data
    return f'ERROR {r.status_code}'

print('Data counts in demo DB:')
print(f'  orders          : {count("/api/orders")}')
print(f'  purchase orders : {count("/api/purchasing")}')
print(f'  machines        : {count("/api/machines")}')
print(f'  rolls           : {count("/api/rolls")}')
print(f'  production runs : {count("/api/production")}')
print(f'  items           : {count("/api/items")}')
print(f'  suppliers       : {count("/api/partners/suppliers")}')
print(f'  buyers          : {count("/api/partners/buyers")}')
print(f'  notifications   : {count("/api/notifications")}')
print(f'  workers         : {count("/api/attendance/workers")}')
print()
dash = client.get('/api/dashboard', cookies=cookies).json()
print('Dashboard data:')
print(json.dumps(dash, indent=2))
print()
rpt = client.get('/api/reports/production', cookies=cookies).json()
print('Production report:')
print(json.dumps(rpt, indent=2))
print()
qrpt = client.get('/api/reports/quality', cookies=cookies).json()
print('Quality report:')
print(json.dumps(qrpt, indent=2))
