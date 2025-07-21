from datetime import datetime, timedelta
import requests
import csv
import os

# ——— Configuration ———
API_BASE_URL = 'https://ll.thespacedevs.com/2.3.0/launches/'
API_KEY      = 'insert API Key'
HEADERS      = {'Authorization': f'Token {API_KEY}'}

# ——— Time window: 31 days ago → 60 days from now ———
now       = datetime.utcnow()
month_ago = now - timedelta(days=31)
future    = now + timedelta(days=60)

# Build query parameters
params = {
    'net__gte': month_ago.strftime('%Y-%m-%dT%H:%M:%SZ'),
    'net__lte': future   .strftime('%Y-%m-%dT%H:%M:%SZ'),
    'include_suborbital': 'false',
    'mode':     'normal',
    'limit':    2,
    'ordering': 'net'
}

# ——— Prepare output CSV path ———
out_dir  = r'C:\Users\standalone1\Desktop\RocketLaunch\Output'
os.makedirs(out_dir, exist_ok=True)
out_file = os.path.join(out_dir, 'launches_next_past_month.csv')

# ——— Helper to fetch a page of results ———
def get_results(url, params=None):
    resp = requests.get(url, headers=HEADERS, params=params)
    print(f"GET {resp.url} → {resp.status_code}")
    if resp.status_code != 200:
        print("Error response:", resp.text)
        return None
    return resp.json()

# ——— Main: open CSV once, write header, then paginate ———
with open(out_file, 'w', encoding='utf-8', newline='') as csvfile:
    writer = csv.writer(csvfile)
    # Write header row
    writer.writerow([
        'launch_id', 'date', 'time',
        'rocket', 'mission',
        'pad_location', 'location', 'status'
    ])

    url = API_BASE_URL
    first_page = True
    while url:
        data = get_results(url, params if first_page else None)
        first_page = False
        if not data:
            break

        for launch in data.get('results', []):
            # NET → date & time
            net = launch.get('net', '')
            date, _, time = net.partition('T')
            time = time.rstrip('Z')

            # name → rocket & mission
            name = launch.get('name', '')
            if '|' in name:
                rocket, mission = [s.strip() for s in name.split('|', 1)]
            else:
                rocket, mission = name, ''

            # pad_location (full) & location (country)
            pad_loc = launch.get('pad', {}) \
                            .get('location', {}) \
                            .get('name', '')
            country = launch.get('pad', {}) \
                            .get('country', {}) \
                            .get('name', '')

            # status
            status = launch.get('status', {}).get('name', '')

            # write the row
            writer.writerow([
                launch.get('id', ''),
                date, time,
                rocket, mission,
                pad_loc, country, status
            ])

        # advance to next page
        url = data.get('next')

print("Done! CSV saved to:", out_file)


'44e9bb0de803f1eca3ac4caa3fbde3bc2e31703a'
