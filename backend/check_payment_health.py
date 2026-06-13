import requests
import json
import sys
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
sys.stdout.reconfigure(encoding='utf-8')

url = "https://localhost:8000/payment/health"
try:
    r = requests.get(url, timeout=10, verify=False)
    print(f"Status Code: {r.status_code}")
    print("Response JSON:")
    print(json.dumps(r.json(), indent=2))
except Exception as e:
    print(f"Error querying backend: {e}")
