import requests, json, os

base = "http://127.0.0.1:8001"
print('Testing', base)

# 1. GET /locations
r = requests.get(f"{base}/locations", timeout=5)
print('/locations ->', r.status_code)
try:
    print(r.json())
except Exception as e:
    print('locations json error', e)

# 2. Upload CSV
sample = os.path.join(os.path.dirname(__file__), 'sample_itinerary.csv')
if not os.path.exists(sample):
    print('sample CSV not found:', sample)
else:
    with open(sample, 'rb') as f:
        files = {'file': ('sample_itinerary.csv', f, 'text/csv')}
        r2 = requests.post(f"{base}/upload_itinerary", files=files, timeout=10)
        print('/upload_itinerary ->', r2.status_code)
        print(r2.text)
        data = r2.json() if r2.ok else None

# 3. If upload returned meetings, call /chat
if data and data.get('meetings'):
    meetings = data['meetings']
    # set a leg override (BKC -> Bandra) to cab to simulate the UI edit_leg action
    override_payload = {'from': 'BKC', 'to': 'Bandra', 'mode': 'cab', 'reason': 'test override'}
    r_override = requests.post(f"{base}/set_leg_override", json=override_payload, timeout=5)
    print('/set_leg_override ->', r_override.status_code, r_override.text)

    payload = {'message': 'plan my day', 'meetings': meetings}
    r3 = requests.post(f"{base}/chat", json=payload, timeout=20)
    print('/chat ->', r3.status_code)
    try:
        print(json.dumps(r3.json(), indent=2))
    except Exception as e:
        print('chat json error', e)
else:
    print('No meetings to test /chat')
