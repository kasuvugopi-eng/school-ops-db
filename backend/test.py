import urllib.request
import json
import urllib.error
import random

def request(url, data=None, headers=None):
    headers = headers or {}
    if data:
        data = json.dumps(data).encode('utf-8')
        headers['Content-Type'] = 'application/json'
    req = urllib.request.Request(url, data=data, headers=headers)
    try:
        with urllib.request.urlopen(req) as response:
            return response.status, response.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()

reg_data = {
    'school_name': 'Test School',
    'school_code': 'TEST' + str(random.randint(1000,9999)),
    'admin_email': 'admin' + str(random.randint(1000,9999)) + '@test.com',
    'admin_password': 'password123',
    'admin_full_name': 'Test Admin'
}

status, text = request('http://127.0.0.1:8000/api/auth/register', reg_data)
if status not in [200, 201]:
    print("Register failed:", status, text)
else:
    token = json.loads(text).get('access_token')
    status2, text2 = request('http://127.0.0.1:8000/api/invites', {'role': 'teacher', 'expires_hours': 24}, {'Authorization': f'Bearer {token}'})
    if status2 in [200, 201]:
        print("PASS")
    else:
        print("Invite Create FAIL:", status2, text2)
