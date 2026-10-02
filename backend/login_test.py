import requests
creds = [
    ('punya@gmail.com', 'password123'),
    ('punya@gmail.com', 'password'),
    ('punya@gmail.com', 'punya123'),
]
for email, pwd in creds:
    try:
        r = requests.post('http://127.0.0.1:8000/api/login', json={'email': email, 'password': pwd}, timeout=10)
        print(email, pwd, r.status_code, r.text)
    except Exception as e:
        print('ERROR', email, pwd, e)
