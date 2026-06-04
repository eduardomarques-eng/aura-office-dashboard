import urllib.request, json
req = urllib.request.Request('http://localhost:8000/crew/run', data=json.dumps({"crew_type":"mining","context":"vaso japandi ceramica wabi-sabi flores secas decoracao minimalista"}).encode(), headers={'Content-Type':'application/json'}, method='POST')
resp = urllib.request.urlopen(req, timeout=300)
print(resp.read().decode())