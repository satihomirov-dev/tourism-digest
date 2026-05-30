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

STYLES = ['lead', 'midnight', 'rose', 'terminal', 'academic', 'stats']

def make_spread(post, idx, source):
    style = STYLES[idx % 6]
    words = len(post.split())
    m = re.match(r'^(.{20,120}?[.!?])\s', post)
    first = m.group(1) if m else ' '.join(post.split()[:10]) + '…'
    rest  = post[len(first):].strip()

    if style == 'lead':
        return f'<section class="spread lead"><div class="src-tag">{source}</div><h2>{esc(first)}</h2><p>{esc(rest)}</p></section>'
    if style == 'midnight':
        return f'<section class="spread midnight"><div class="accent-bar"></div><div class="src-tag">{source}</div><h2>{esc(first)}</h2><p>{esc(rest)}</p></section>'
    if style == 'rose':
        return f'<section class="spread rose"><div class="deco-quote">«</div><div class="src-tag">{source}</div><h2>{esc(first)}</h2><p>{esc(rest)}</p></section>'
    if style == 'terminal':
        return f'<section class="spread terminal"><div class="scanlines"></div><div class="src-tag">{source}</div><div class="prompt">&gt; post.{idx+1:03d}</div><p>{esc(post)}</p></section>'
    if style == 'academic':
        return f'<section class="spread academic"><div class="fn-num">{idx+1}</div><div class="src-tag">{source}</div><div class="ruled"><h2>{esc(first)}</h2></div><p>{esc(rest)}</p></section>'
    return f'<section class="spread stats"><div class="src-tag">{source}</div><div class="big-num">{words}</div><div class="big-label">слов</div><p>{esc(post)}</p></section>'

def make_sep(label, count, extra=''):
    return f'<section class="spread separator"{extra}><div class="sep-bg">{label}</div><div class="sep-count">{count} новостей</div><div class="sep-label">{label}</div></section>'

CSS = '''*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'Inter',sans-serif;overflow-x:hidden;background:#111}
#bar{position:fixed;top:0;left:0;height:3px;background:linear-gradient(90deg,#ff6b6b,#ffd93d,#6bcb77,#4d96ff);width:0%;z-index:999}
.spread{min-height:100vh;display:flex;flex-direction:column;justify-content:center;padding:clamp(3rem,8vw,8rem);position:relative;overflow:hidden}
.src-tag{font-size:.75rem;font-weight:600;letter-spacing:.15em;text-transform:uppercase;opacity:.45;margin-bottom:1.5rem}
h2{font-family:'Fraunces',serif;font-size:clamp(2rem,5vw,3.8rem);line-height:1.15;margin-bottom:1.5rem;font-weight:700}
p{font-size:clamp(1.1rem,2vw,1.3rem);line-height:1.75;max-width:70ch}
.masthead{background:#000;align-items:center;text-align:center;gap:1rem}
.masthead h1{font-family:'Fraunces',serif;font-size:clamp(3.5rem,12vw,9rem);color:#fff;letter-spacing:-.03em;line-height:1}
.masthead .sub{color:rgba(255,255,255,.35);font-size:clamp(1rem,2.5vw,1.5rem);letter-spacing:.2em;text-transform:uppercase;margin-top:.75rem}
.masthead .meta{color:rgba(255,255,255,.2);font-size:.8rem;margin-top:1.5rem;letter-spacing:.1em}
.separator{background:#0a0a0a;justify-content:flex-end;padding-bottom:5rem}
.sep-bg{font-family:'Fraunces',serif;font-size:clamp(5rem,18vw,14rem);color:#fff;opacity:.05;position:absolute;bottom:1rem;left:clamp(3rem,8vw,8rem);line-height:1;pointer-events:none}
.sep-label{font-family:'Fraunces',serif;font-size:clamp(2rem,5vw,4rem);color:#fff;position:relative}
.sep-count{color:rgba(255,255,255,.3);font-size:.9rem;letter-spacing:.15em;text-transform:uppercase;margin-bottom:.5rem;position:relative}
.lead{background:#fff;color:#1a1a1a}.lead .src-tag,.lead h2{color:#1a1a1a}.lead p{color:#555}
.midnight{background:#0d1117;color:#e8f4f8}.midnight .src-tag{color:#8ab4c8}
.accent-bar{width:4px;height:4rem;background:#58a6ff;border-radius:2px;margin-bottom:2rem}
.midnight h2{color:#e8f4f8}.midnight p{color:#8ab4c8}
.rose{background:#fff0f3;color:#1a1a1a}.rose .src-tag{color:#c9184a}
.deco-quote{font-family:'Fraunces',serif;font-size:clamp(12rem,28vw,22rem);color:#c9184a;opacity:.07;position:absolute;top:-3rem;left:1rem;line-height:1;pointer-events:none;font-style:italic}
.rose h2{color:#c9184a;position:relative}.rose p{color:#555;position:relative}
.terminal{background:#0a0a0a;color:#00ff88;font-family:'Courier New',monospace}
.terminal .src-tag{color:#00ff88;opacity:.35}
.scanlines{position:absolute;inset:0;background:repeating-linear-gradient(0deg,transparent,transparent 3px,rgba(0,255,136,.018) 3px,rgba(0,255,136,.018) 4px);pointer-events:none}
.prompt{font-size:1rem;color:#00ff88;opacity:.4;margin-bottom:1.5rem}
.terminal p{font-size:clamp(1rem,1.8vw,1.15rem);line-height:1.85;position:relative}
.academic{background:#faf8f2;color:#2c2416}.academic .src-tag{color:#8b7355}
.fn-num{font-family:'Fraunces',serif;font-size:clamp(6rem,14vw,11rem);color:#2c2416;opacity:.05;position:absolute;top:2rem;right:3rem;line-height:1;font-weight:700}
.ruled{border-top:2px solid #2c2416;border-bottom:1px solid rgba(44,36,22,.25);padding:1.5rem 0;margin-bottom:1.5rem;position:relative}
.academic h2{font-size:clamp(1.6rem,3.5vw,2.8rem);color:#2c2416}
.academic p{font-family:'Fraunces',serif;font-style:italic;color:#5a4a35;font-size:clamp(1.05rem,1.8vw,1.2rem)}
.stats{background:#1a237e;color:#fff}.stats .src-tag{color:rgba(255,255,255,.35)}
.big-num{font-family:'Fraunces',serif;font-size:clamp(6rem,18vw,13rem);color:#fff;line-height:.9;font-weight:700;letter-spacing:-.04em}
.big-label{font-size:.9rem;color:rgba(255,255,255,.35);letter-spacing:.2em;text-transform:uppercase;margin-bottom:2rem}
.stats p{font-size:clamp(1rem,1.8vw,1.15rem);color:rgba(255,255,255,.75);max-width:62ch}
footer{background:#000;color:rgba(255,255,255,.25);text-align:center;padding:3rem 2rem;font-size:.8rem;letter-spacing:.1em}
footer a{color:rgba(255,255,255,.4);text-decoration:none}'''

def build_html(tourdom, atorus, date_str):
    d = datetime.strptime(date_str, '%Y-%m-%d')
    date_ru = f'{d.day} {MONTHS_RU[d.month]} {d.year}'
    total = len(tourdom) + len(atorus)
    spreads, idx = '', 0
    if tourdom:
        spreads += make_sep('@tourdom', len(tourdom))
        for p in tourdom:
            spreads += make_spread(p, idx, '@tourdom'); idx += 1
    if atorus:
        spreads += make_sep('@atorus', len(atorus), ' style="background:#0d1b2a"')
        for p in atorus:
            spreads += make_spread(p, idx, '@atorus'); idx += 1
    if not total:
        spreads = f'<section class="spread stats" style="background:#111;align-items:center;text-align:center"><div class="big-num" style="opacity:.15">...</div><div class="big-label">Тихий день</div><p style="color:rgba(255,255,255,.35)">Новостей за {date_ru} не поступало.</p></section>'
    return f'''<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Tourism Digest — {date_ru}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,300;0,9..144,700;1,9..144,400&family=Inter:wght@400;600&display=swap" rel="stylesheet">
<style>{CSS}</style>
</head>
<body>
<div id="bar"></div>
<script>window.addEventListener('scroll',()=>{{const d=document.documentElement;document.getElementById('bar').style.width=(d.scrollTop/(d.scrollHeight-d.clientHeight)*100)+'%'}})</script>
<section class="spread masthead"><h1>TOURISM<br>DIGEST</h1><div class="sub">{date_ru}</div><div class="meta">@tourdom &bull; @atorus &bull; {total} новостей</div></section>
{spreads}
<footer>Tourism Digest &bull; <a href="https://t.me/tourdom">@tourdom</a> &bull; <a href="https://t.me/atorus">@atorus</a> &bull; Сгенерировано автоматически</footer>
</body></html>'''

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
