import urllib.request, re, html as htmllib, json, os, sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

MSK = timezone(timedelta(hours=3))
yesterday = (datetime.now(MSK) - timedelta(days=1)).strftime('%Y-%m-%d')
TG_TOKEN = os.environ.get('TG_BOT_TOKEN', '')
TG_CHAT   = os.environ.get('TG_CHAT_ID', '')

MONTHS_RU = ['','января','февраля','марта','апреля','мая','июня',
              'июля','августа','сентября','октября','ноября','декабря']

def fetch_html(url):
    req = urllib.request.Request(url, headers={
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36'
    })
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.read().decode('utf-8', errors='replace')

def parse_page(html):
    ids   = [int(m.group(1)) for m in re.finditer(r'data-post="[^/]+/(\d+)"', html)]
    dates = [m.group(1) for m in re.finditer(r'datetime="(\d{4}-\d{2}-\d{2})', html)]
    raws  = re.findall(
        r'class="tgme_widget_message_text js-message_text[^"]*"[^>]*>([\s\S]*?)</div>', html)
    texts = []
    for raw in raws:
        t = re.sub(r'<br\s*/?>', '\n', raw)
        t = re.sub(r'<[^>]+>', '', t)
        t = htmllib.unescape(t).strip()
        texts.append(re.sub(r'  +', ' ', t))
    while len(texts) < len(ids): texts.append('')
    while len(dates) < len(ids): dates.append('')
    return list(zip(ids, dates, texts))

def collect(channel):
    posts, before_id = [], None
    for page in range(10):
        url = f'https://t.me/s/{channel}' + (f'?before={before_id}' if before_id else '')
        try:
            rows = parse_page(fetch_html(url))
        except Exception as e:
            print(f'[{channel}] p{page+1} error: {e}', file=sys.stderr)
            break
        if not rows:
            break
        min_id = min(r[0] for r in rows)
        page_dates = {r[1] for r in rows}
        has_older = any(d < yesterday for d in page_dates if d)
        matched = [r[2] for r in rows if r[1] == yesterday and len(r[2]) > 30]
        posts.extend(matched)
        print(f'[{channel}] p{page+1}: {len(rows)} msgs, dates={sorted(page_dates)}, matched={len(matched)}', file=sys.stderr)
        if has_older:
            break
        before_id = min_id
    seen, out = set(), []
    for p in posts:
        if p not in seen:
            seen.add(p)
            out.append(p)
    return out

def esc(s):
    return s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

def make_card(post, idx, source):
    m = re.match(r'^(.{20,150}?[.!?])\s', post)
    headline = m.group(1) if m else ' '.join(post.split()[:12]) + '…'
    body = post[len(headline):].strip()
    n = idx + 1
    body_html = f'<p class="body">{esc(body)}</p>' if body else ''
    return f'''<article class="card">
  <span class="card-num">{n:02d}</span>
  <h2>{esc(headline)}</h2>
  {body_html}
  <div class="card-source">{esc(source)}</div>
</article>'''

def make_channel_header(label, count):
    return f'<div class="ch-header"><span class="ch-name">{esc(label)}</span><span class="ch-count">{count} новостей</span></div>'

CSS = '''
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

:root {
  --bg: #f7f6f2;
  --surface: #ffffff;
  --ink: #1c1c1e;
  --ink-2: #48484a;
  --ink-3: #8e8e93;
  --accent: #1c1c1e;
  --rule: #e0dfd9;
  --font-serif: 'Fraunces', Georgia, serif;
  --font-sans: 'Inter', system-ui, sans-serif;
}

body {
  font-family: var(--font-sans);
  background: var(--bg);
  color: var(--ink);
  line-height: 1.6;
  -webkit-font-smoothing: antialiased;
}

#bar {
  position: fixed; top: 0; left: 0; height: 2px;
  background: var(--ink); width: 0%; z-index: 999;
  transition: width .1s linear;
}

/* MASTHEAD */
.masthead {
  background: var(--ink);
  color: #fff;
  padding: 3rem 2rem 2.5rem;
  text-align: center;
  border-bottom: 1px solid #333;
}
.masthead h1 {
  font-family: var(--font-serif);
  font-size: clamp(2.8rem, 8vw, 6rem);
  font-weight: 700;
  letter-spacing: -.03em;
  line-height: 1;
}
.masthead .date-ru {
  margin-top: .6rem;
  font-size: .85rem;
  letter-spacing: .18em;
  text-transform: uppercase;
  color: rgba(255,255,255,.45);
}
.masthead .total {
  margin-top: .4rem;
  font-size: .78rem;
  color: rgba(255,255,255,.25);
  letter-spacing: .08em;
}

/* LAYOUT */
.container {
  max-width: 720px;
  margin: 0 auto;
  padding: 0 1.5rem 4rem;
}

/* CHANNEL HEADER */
.ch-header {
  display: flex;
  align-items: baseline;
  gap: 1rem;
  padding: 2.5rem 0 1rem;
  border-bottom: 2px solid var(--ink);
  margin-bottom: 0;
}
.ch-name {
  font-family: var(--font-serif);
  font-size: 1.6rem;
  font-weight: 700;
  letter-spacing: -.01em;
}
.ch-count {
  font-size: .78rem;
  color: var(--ink-3);
  letter-spacing: .1em;
  text-transform: uppercase;
}

/* CARD */
.card {
  padding: 1.5rem 0;
  border-bottom: 1px solid var(--rule);
  display: grid;
  grid-template-columns: 2rem 1fr;
  grid-template-rows: auto auto auto;
  column-gap: 1.25rem;
  row-gap: .4rem;
}
.card-num {
  font-family: var(--font-serif);
  font-size: .8rem;
  color: var(--ink-3);
  padding-top: .35rem;
  font-weight: 300;
  font-style: italic;
}
.card h2 {
  font-family: var(--font-serif);
  font-size: clamp(1.15rem, 2.5vw, 1.4rem);
  font-weight: 700;
  line-height: 1.3;
  color: var(--ink);
  grid-column: 2;
}
.card .body {
  font-size: .95rem;
  color: var(--ink-2);
  line-height: 1.65;
  grid-column: 2;
}
.card-source {
  grid-column: 2;
  font-size: .72rem;
  color: var(--ink-3);
  letter-spacing: .1em;
  text-transform: uppercase;
  margin-top: .25rem;
}

/* EMPTY STATE */
.empty {
  padding: 5rem 0;
  text-align: center;
  color: var(--ink-3);
  font-family: var(--font-serif);
  font-size: 1.3rem;
  font-style: italic;
}

footer {
  border-top: 1px solid var(--rule);
  padding: 1.5rem;
  text-align: center;
  font-size: .75rem;
  color: var(--ink-3);
  letter-spacing: .06em;
  background: var(--bg);
}
footer a { color: var(--ink-2); text-decoration: none; }
footer a:hover { text-decoration: underline; }

@media (max-width: 480px) {
  .card { grid-template-columns: 1.5rem 1fr; column-gap: .75rem; }
}
'''

def build_html(tourdom, atorus, date_str):
    d = datetime.strptime(date_str, '%Y-%m-%d')
    date_ru = f'{d.day} {MONTHS_RU[d.month]} {d.year}'
    total = len(tourdom) + len(atorus)

    body_parts = []
    idx = 0
    if tourdom:
        body_parts.append(make_channel_header('@tourdom', len(tourdom)))
        for p in tourdom:
            body_parts.append(make_card(p, idx, '@tourdom'))
            idx += 1
    if atorus:
        body_parts.append(make_channel_header('@atorus', len(atorus)))
        for p in atorus:
            body_parts.append(make_card(p, idx, '@atorus'))
            idx += 1

    inner = '\n'.join(body_parts) if body_parts else f'<div class="empty">Новостей за {date_ru} не поступало.</div>'

    return f'''<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Tourism Digest — {date_ru}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,300;0,9..144,700;1,9..144,400&family=Inter:wght@400;500&display=swap" rel="stylesheet">
<style>{CSS}</style>
</head>
<body>
<div id="bar"></div>
<script>window.addEventListener('scroll',()=>{{const d=document.documentElement;document.getElementById('bar').style.width=(d.scrollTop/(d.scrollHeight-d.clientHeight)*100)+'%'}})</script>
<header class="masthead">
  <h1>Tourism Digest</h1>
  <div class="date-ru">{date_ru}</div>
  <div class="total">{total} новостей &bull; @tourdom &bull; @atorus</div>
</header>
<div class="container">
{inner}
</div>
<footer>
  Tourism Digest &bull;
  <a href="https://t.me/tourdom">@tourdom</a> &bull;
  <a href="https://t.me/atorus">@atorus</a> &bull;
  Сгенерировано автоматически
</footer>
</body>
</html>'''

if __name__ == '__main__':
    print(f'Fetching posts for {yesterday}...', file=sys.stderr)
    tourdom = collect('tourdom')
    atorus  = collect('atorus')
    print(f'tourdom={len(tourdom)}, atorus={len(atorus)}', file=sys.stderr)

    out_path = Path('magazines') / f'{yesterday}.html'
    out_path.parent.mkdir(exist_ok=True)
    out_path.write_text(build_html(tourdom, atorus, yesterday), encoding='utf-8')
    print(f'Written: {out_path}', file=sys.stderr)

    if TG_TOKEN and TG_CHAT:
        msg = (f'Tourism Digest - {yesterday}\n\n'
               f'Novyi vypusk:\nhttps://satihomirov-dev.github.io/tourism-digest/magazines/{yesterday}.html\n\n'
               f'@tourdom: {len(tourdom)}\n@atorus: {len(atorus)}')
        data = json.dumps({'chat_id': TG_CHAT, 'text': msg}).encode('utf-8')
        req = urllib.request.Request(
            f'https://api.telegram.org/bot{TG_TOKEN}/sendMessage',
            data=data, headers={'Content-Type': 'application/json'})
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                print('Telegram: OK', file=sys.stderr)
        except Exception as e:
            print(f'Telegram error: {e}', file=sys.stderr)
