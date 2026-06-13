import asyncio, os, sys, httpx
sys.stdout.reconfigure(encoding='utf-8')

async def raw_test():
    KEY = '3c8626a63471e84bc499e211070c0b63a8c5'
    BASE = 'https://connectors.windsor.ai/all'

    # Testa diferentes combinacoes de params para ver o que funciona
    tests = [
        # (descricao, params)
        ('IG date_preset', {
            'api_key': KEY, 'connector': 'instagram_public',
            'date_preset': 'last_7d',
            'fields': 'date,profile_followers_count,media_like_count'
        }),
        ('IG date_from/to', {
            'api_key': KEY, 'connector': 'instagram_public',
            'date_from': '2026-05-28', 'date_to': '2026-06-04',
            'fields': 'date,profile_followers_count,media_like_count'
        }),
        ('FB org date_preset', {
            'api_key': KEY, 'connector': 'facebook_organic',
            'date_preset': 'last_7d',
            'fields': 'date,page_fans,post_impressions'
        }),
    ]

    for desc, params in tests:
        async with httpx.AsyncClient(timeout=20) as c:
            r = await c.get(BASE, params=params)
            try:
                body = r.json()
            except Exception:
                body = {'raw': r.text[:200]}
            rows = body.get('data', []) if isinstance(body, dict) else []
            msg = body.get('message', '') if isinstance(body, dict) else ''
            print(f'[{r.status_code}] {desc}: rows={len(rows)} msg={msg[:80]}')
            if rows:
                print('  sample:', str(rows[0])[:120])

asyncio.run(raw_test())
