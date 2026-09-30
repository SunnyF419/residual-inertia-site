"""Dependency-free static publisher. Only content/ and assets/ enter the website."""
import argparse
import html
import json
import math
import re
import shutil
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'dist'
CONFIG = json.loads((ROOT / 'site.json').read_text(encoding='utf-8'))
E = lambda value: html.escape(str(value if value is not None else '—'), quote=True)
SMART_NAV_JS = '''<script>
(function(){
  const header=document.querySelector('.masthead');
  const klineClip=document.getElementById('kline-clip-rect');
  const flipCard=document.querySelector('.founder-flip-card');
  let lastY=window.scrollY,ticking=false;
  function update(){
    const y=window.scrollY;
    if(header){
      if(y>lastY&&y>80)header.classList.add('masthead--hidden');
      else if(y<lastY)header.classList.remove('masthead--hidden');
    }
    if(klineClip){
      const maxScroll=Math.max(200,document.body.scrollHeight-window.innerHeight);
      const progress=Math.min(1,Math.max(0,y/maxScroll));
      klineClip.setAttribute('width',(720*progress).toFixed(1));
    }
    lastY=y;ticking=false;
  }
  window.addEventListener('scroll',function(){if(!ticking){requestAnimationFrame(update);ticking=true;}},{passive:true});
  if(flipCard){
    function toggleFlip(){flipCard.classList.toggle('flipped');}
    flipCard.addEventListener('click',toggleFlip);
    flipCard.addEventListener('keydown',function(e){if(e.key==='Enter'||e.key===' '){e.preventDefault();toggleFlip();}});
  }
})();
</script>'''
ROUTE = 'index.html'
PATHS = []


def url(path):
    page, marker, fragment = path.partition('#')
    if page.endswith('index.html'):
        page = page[:-10]
    elif page.endswith('.html') and page != '404.html':
        page = page[:-5] + '/'
    return '/' + page.lstrip('/') + (marker + fragment if marker else '')


def number(value, pct=False):
    if not isinstance(value, (int, float)) or not math.isfinite(value):
        return '—'
    return f'{value * 100:.1f}%' if pct else f'{value:.1f}'


def shortdate(value):
    return E(str(value)[:10]) if value else '未提供'


def anchor(target, text, cls=''):
    return f'<a class="{cls}" href="{E(url(target))}">{text}</a>'


def shell(title, content, section='', description=None):
    nav = ''.join(anchor(path, name, 'active' if section == key else '') for key, path, name in [
        ('home', 'index.html', '首页'), ('overview', 'overview.html', '市场概览'),
        ('research', 'research/index.html', '研究'), ('about', 'about.html', '关于')])
    canonical = 'https://' + CONFIG['domain'] + url(ROUTE)
    return f'''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{E(title)} · Residual Inertia | 余势</title><meta name="description" content="{E(description or CONFIG['description'])}">
<link rel="canonical" href="{canonical}"><meta property="og:title" content="{E(title)} · Residual Inertia">
<meta property="og:description" content="{E(description or CONFIG['description'])}"><meta property="og:type" content="website">
<link rel="icon" href="{url('favicon.ico')}" sizes="16x16 32x32 48x48" type="image/x-icon"><link rel="icon" href="{url('assets/brand/favicon.svg')}" type="image/svg+xml"><link rel="apple-touch-icon" href="{url('assets/brand/apple-touch-icon.png')}"><link rel="stylesheet" href="{url('assets/site.css')}">
</head><body><a class="skip" href="#main">跳转正文</a><header class="masthead"><div class="wrap header-inner">
{anchor('index.html', '<img src="'+url('assets/brand/RI-horizontal-white.svg')+'" alt="Residual Inertia | 余势" width="260" height="64">', 'brand')}
<nav aria-label="主导航">{nav}</nav></div></header><main id="main" class="wrap">{content}</main>
<footer class="wrap site-footer"><div class="footer-main"><div><strong>Residual Inertia | 余势</strong><p>独立投资研究与决策系统</p><p class="brand-line">{E(CONFIG.get('brandLine',''))}</p></div><div class="footer-meta"><p>{E(CONFIG['motto'])}</p>{anchor('about.html#disclosure','披露')}</div></div><div class="footer-bottom"><small>仅供研究，不构成投资建议。历史结果不代表未来表现。</small></div></footer>{SMART_NAV_JS}</body></html>'''


def write(route, title, render, section='', description=None):
    global ROUTE
    destination = route if route.endswith('index.html') or route == '404.html' else route[:-5] + '/index.html'
    ROUTE = destination
    p = OUT / destination
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(shell(title, render(), section, description), encoding='utf-8')
    PATHS.append(destination)
    if destination != route:
        redirect(route, url(destination), title)


def redirect(route, target, title):
    p = OUT / route
    p.parent.mkdir(parents=True, exist_ok=True)
    canonical = 'https://' + CONFIG['domain'] + target.split('#')[0]
    p.write_text(f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>{E(title)} · 余势</title>
<meta http-equiv="refresh" content="0;url={E(target)}"><link rel="canonical" href="{E(canonical)}">
</head><body><h1>{E(title)}</h1><p>页面地址已更新。<a href="{E(target)}">继续阅读</a></p></body></html>''', encoding='utf-8')


def head(kicker, title, text=''):
    return f'<div class="pagehead"><p class="eyebrow">{E(kicker)}</p><h1>{E(title)}</h1><p class="lede">{E(text)}</p></div>'


def cover_kline():
    n = 18
    width = 720
    height = 120
    gap = width / n
    candle_w = gap * 0.55
    svg = []
    y = 60
    for i in range(n):
        change = math.sin(i * 0.8) * 14 + math.cos(i * 1.4) * 8
        open_y = y
        close_y = max(15, min(105, 60 + change))
        high_y = min(115, max(open_y, close_y) + 8 + (i % 3) * 3)
        low_y = max(5, min(open_y, close_y) - 8 - (i % 4) * 2)
        y = close_y
        x = i * gap + gap / 2
        bullish = close_y <= open_y
        color = '#5d8f7e' if bullish else '#c86159'
        body_top = min(open_y, close_y)
        body_h = max(2, abs(close_y - open_y))
        svg.append(f'<line x1="{x:.1f}" y1="{low_y:.1f}" x2="{x:.1f}" y2="{high_y:.1f}" stroke="{color}" stroke-width="1.5" opacity="0.75"/>')
        svg.append(f'<rect x="{x - candle_w/2:.1f}" y="{body_top:.1f}" width="{candle_w:.1f}" height="{body_h:.1f}" fill="{color}" rx="1" opacity="0.9"/>')
    return f'''<svg class="cover-kline" viewBox="0 0 {width} {height}" preserveAspectRatio="none" aria-hidden="true">
<defs><clipPath id="kline-clip"><rect id="kline-clip-rect" x="0" y="0" width="0" height="{height}"/></clipPath></defs>
<g clip-path="url(#kline-clip)">{''.join(svg)}</g>
</svg>'''


def cover():
    hero = E(CONFIG.get('hero','')).replace('，', '，<br>')
    return f'''<section class="brand-cover" id="hero" aria-label="余势品牌封面">
{cover_kline()}
<div class="cover-copy"><p class="eyebrow">RESIDUAL INERTIA | 余势</p>
<h1>{hero}</h1><div class="cover-description"><span class="cover-rule" aria-hidden="true"></span>
<p>独立投资研究与决策系统<span>Independent Investment Research &amp; Systems</span></p></div>
<div class="cover-actions">{anchor('research/index.html', '阅读研究', 'cover-primary')}{anchor('overview.html', '进入市场概览 ↗', 'cover-secondary')}</div></div>
</section>
'''


def homepage(latest, research):
    return cover()


def principles():
    items = [
        ('Evidence', '证据', '以数据与可检验的依据形成判断，也保留结论的边界。'),
        ('Simplicity', '简洁', '理解复杂性之后做取舍，让重要的问题与判断清楚可见。'),
        ('System', '系统', '把观察、研究与复盘连接起来，让方法可以积累、检验与修正。'),
        ('Independence', '独立', '保持独立思考，在新的证据出现时保留改变观点的能力。'),
    ]
    return '<section class="principles" id="principles" aria-labelledby="principles-title"><p class="eyebrow">OUR PRINCIPLES</p><h2 id="principles-title">研究的四个原则</h2><div class="principle-grid">'+''.join(f'<div><h3>{en}<span>{cn}</span></h3><p>{text}</p></div>' for en,cn,text in items)+'</div></section>'


def metrics(s):
    m = s['market']
    specs = [('风险等级', m['riskLevel'], '周度风险模型', m['signalDate']),
             ('市场状态', m['regimeState'], f"综合分数 {number(m['regimeScore'])} / 100", m['regimeDate']),
             ('模型目标仓位', number(m['targetExposure'], True), '模型输出 · 非实际持仓', m['signalDate']),
             ('市场宽度', number(m['breadth'], True), '原市场研究指标', m['breadthDate'])]
    return '<div class="metrics">' + ''.join(f'<section class="metric"><p>{E(label)}</p><strong>{E(value)}</strong><span>{E(detail)}</span><small>数据截至 {shortdate(asof)}</small></section>' for label,value,detail,asof in specs) + '</div>'


def pillars(s):
    names = {'Financial Stress':'金融压力', 'Fragility':'市场脆弱度', 'Market Risk':'市场风险', 'Participation':'市场参与度'}
    rows = ''
    for p in s['market'].get('pillars', []):
        score = p.get('score')
        width = min(100, max(0, score)) if isinstance(score, (int,float)) else 0
        tone = {'建设性': 'positive', '谨慎': 'caution', '中性': 'caution', '防御': 'caution', '压力': 'risk'}.get(p['state'], 'neutral')
        rows += f'<div class="pillar"><div><span>{E(names.get(p["name"],p["name"]))}</span><span>{E(p["state"])} <b>{number(score)}</b></span></div><div class="track"><span class="{tone}" style="width:{width:.4f}%"></span></div></div>'
    return f'<section class="panel"><div class="section-title"><h2>风险的四个维度</h2><span class="mono">/ 100</span></div>{rows}<p class="caption">原模型分数与状态；各支柱含义不同，不作为统一买卖阈值。</p></section>'


def history_chart(snapshots, embedded=False):
    history = json.loads((ROOT/'content/market/regime-history.json').read_text(encoding='utf-8'))
    usable = history['points']
    start = date.fromisoformat(history['windowStart']).toordinal()
    end = date.fromisoformat(history['windowEnd']).toordinal()
    points = ' '.join(f"{48+(date.fromisoformat(p['date']).toordinal()-start)/max(end-start,1)*600:.2f},{178-p['score']*1.45:.2f}" for p in usable)
    grid = ''.join(f'<line x1="48" y1="{178-v*1.45}" x2="648" y2="{178-v*1.45}"/><text x="8" y="{183-v*1.45}">{v}</text>' for v in [0,50,100])
    ticks = ''.join(f'<text x="{48+(date(y,1,1).toordinal()-start)/max(end-start,1)*600:.2f}" y="212" text-anchor="middle">{y}</text>' for y in range(date.fromordinal(start).year+1,date.fromordinal(end).year+1))
    svg = f'<svg viewBox="0 0 684 224" role="img" aria-labelledby="history-title history-desc"><title id="history-title">过去五年的市场状态分数</title><desc id="history-desc">{history["windowStart"]} 至 {history["windowEnd"]}，共 {len(usable)} 个模型数据点。综合分数范围为 0 到 100。</desc><g class="grid">{grid}</g><polyline class="series" points="{points}"/>{ticks}</svg>'
    caption = f'<p class="caption">{history["windowStart"]} — {history["windowEnd"]} · {len(usable)} 个模型数据点。窗口随每日归档的数据截止日向前滚动。来源：市场研究 Dashboard 历史序列。</p>'
    if embedded:
        return f'<div class="chart-embedded">{svg}{caption}</div>'
    return f'''<section class="panel chart"><div class="section-title"><h2>市场状态的变化</h2><span class="mono">滚动 5 年</span></div>{svg}{caption}</section>'''


def snapshot_rows(snapshots, limit=None):
    rows = []
    for s in list(reversed(snapshots))[:limit]:
        m=s['market']
        rows.append(f'<tr><td>{anchor("snapshots/"+s["observationDate"]+".html", E(s["observationDate"]), "mono")}</td><td>{E(m["riskLevel"])}</td><td>{E(m["regimeState"])}</td><td class="numeric">{number(m["regimeScore"])}</td><td class="numeric">{number(m["breadth"],True)}</td><td>{shortdate(m["signalDate"])}</td></tr>')
    return '<div class="table-scroll" tabindex="0" role="region" aria-label="每日快照表格"><table><thead><tr><th>观察日</th><th>风险等级</th><th>市场状态</th><th class="numeric">综合分数</th><th class="numeric">市场宽度</th><th>风险信号截至</th></tr></thead><tbody>'+''.join(rows)+'</tbody></table></div>'


def overview_pillars(s):
    names = {'Financial Stress':'金融压力', 'Fragility':'市场脆弱度', 'Market Risk':'市场风险', 'Participation':'市场参与度'}
    items = []
    for p in s['market'].get('pillars', []):
        score = p.get('score')
        width = min(100, max(0, score)) if isinstance(score, (int,float)) else 0
        tone = {'建设性': 'positive', '谨慎': 'caution', '中性': 'caution', '防御': 'caution', '压力': 'risk'}.get(p['state'], 'neutral')
        items.append(f'<div class="overview-pillar"><div class="pillar-label"><span>{E(names.get(p["name"],p["name"]))}</span><span>{E(p["state"])}</span></div><div class="pillar-track"><span class="{tone}" style="width:{width:.4f}%"></span></div><div class="pillar-value">{number(score)}</div></div>')
    return '<div class="overview-pillar-grid">'+''.join(items)+'</div>'


def overview_snapshot_list(snapshots):
    items = []
    for s in list(reversed(snapshots))[:8]:
        m=s['market']
        items.append(f'<li class="snapshot-item"><a href="{url("snapshots/"+s["observationDate"]+".html")}"><span class="snapshot-date mono">{E(s["observationDate"])}</span><span class="snapshot-state">{E(m["regimeState"])}</span><span class="snapshot-score mono">{number(m["regimeScore"])}</span><span class="snapshot-link">查看 →</span></a></li>')
    return '<ul class="snapshot-list">'+''.join(items)+'</ul>'


def overview_reading(s):
    m = s['market']
    brief = s.get('brief', {})
    posture = brief.get('posture', f"综合状态 {m['regimeState']}。")
    return f'<section class="reading-card"><div class="reading-main"><p class="eyebrow">LATEST READING / 最新观察</p><h2>{E(m["regimeState"])}</h2><p class="reading-posture">{E(posture)}</p><p class="reading-caption">{anchor("snapshots/"+s["observationDate"]+".html","阅读完整快照 ↗")} · 数据截至 {shortdate(m["signalDate"])} · {E(s["observationDate"])} 归档</p></div><div class="reading-score"><span class="mono">{number(m["regimeScore"])}</span><small>/ 100</small><span class="score-label">综合分数</span></div></section>'


def research_cards(research):
    return '<div class="research-grid">'+''.join(f'<article class="research-card"><p class="eyebrow">{E(r["category"])} <span class="mono">{E(r["published"])}</span></p><h3>{anchor("research/"+r["slug"]+".html",E(r["title"]))}</h3><p>{E(r["summary"])}</p><div class="card-foot"><span>{E("数据截至 "+r["dataThrough"] if r.get("dataThrough") else r.get("dateLabel", "发表于")+" "+r["published"])}</span>{anchor("research/"+r["slug"]+".html","阅读全文 ↗")}</div></article>' for r in research)+'</div>'


COLLECTIONS = {
    'market': ('市场周报与月报', 'MARKET LETTERS', '沿着周度与月度的时间刻度，梳理市场变化、风险与观察。'),
    'personal': ('个人专题研究', 'INDEPENDENT RESEARCH', '围绕具体问题展开研究，包括 WQS 等策略与风险专题。'),
    'fomc': ('FOMC 政策研究', 'POLICY RESEARCH', '关注美联储政策、沟通及其与市场的关系。'),
}


def collection(r):
    return r.get('collection', 'market' if r['category'] in ('周报', '月报') else 'personal')


def research_folders(research):
    cards = []
    for i, (key, (title, label, description)) in enumerate(COLLECTIONS.items(), 1):
        count = sum(collection(r) == key for r in research)
        status = f'{count} 份报告' if count else '报告待整理'
        cards.append(anchor(f'research/{key}/index.html', f'<span class="folder-tab mono">0{i} / {label}</span><h2>{title}</h2><p>{description}</p><div class="folder-foot"><span>{status}</span><span>打开目录 ↗</span></div>', 'folder-card'))
    return '<div class="folder-grid">' + ''.join(cards) + '</div>'


def about():
    founder_intro = f'''<section class="founder-section" id="founder" aria-labelledby="founder-title">
<div class="founder-card">
<div class="founder-flip-card" role="button" tabindex="0" aria-label="创始人卡片，点击查看照片">
<div class="founder-flip-inner">
<div class="founder-flip-front">
<img src="{url('assets/brand/RI-symbol-reverse.svg')}" alt="Residual Inertia" width="120" height="85">
</div>
<div class="founder-flip-back">
<img src="{url('assets/brand/founder-sunny.jpg')}" alt="{E(CONFIG['founder'])} 肖像" width="320" height="400">
</div>
</div>
</div>
<div class="founder-bio">
<p class="eyebrow" id="founder-title">FOUNDER / 创始人</p>
<h2>{E(CONFIG['founder'])}</h2>
<p class="brand-line">{E(CONFIG.get('brandLine',''))}</p>
<p>创建 Residual Inertia｜余势，致力于把市场观察、实证研究与决策系统整合为可重复、可验证的研究基础设施。</p>
</div>
</div>
</section>'''
    return head('ABOUT / RESIDUAL INERTIA', '关于余势', '从复杂中提炼判断，为思考留下空间。') + f'''<article class="prose about-intro">
<p>Residual Inertia｜余势是由 {E(CONFIG['founder'])} 创建的独立投资研究与决策系统平台。平台聚焦量化投资、资产定价、宏观市场、金融数据与 AI 驱动的研究基础设施，并将市场观察、实证研究、模型与工具整合进一个可重复、可验证的研究流程。</p>
<p>Residual Inertia 相信，好的研究并不一定来自更复杂的模型，而来自更清晰的问题、更可靠的证据，以及能够被持续检验和改进的方法。平台坚持 Evidence before narrative. Process before prediction. 从市场状态监测、专题研究，到 Dashboard、数据系统与研究工作流，Residual Inertia 希望逐步建立一套能够长期积累、持续迭代，并真正服务于投资决策的研究基础设施。</p>
</article>''' + principles() + founder_intro + '''<article class="prose">
<h2 id="disclosure">披露</h2><p>内容仅用于独立研究和信息分享，不构成针对任何个人的投资建议。模型仓位不代表实际账户仓位。回测、估算及历史表现均不能保证未来结果。</p></article>'''


def inline(text):
    return re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', E(text))


def research_article(r):
    body = anchor('research/'+collection(r)+'/index.html', '← '+COLLECTIONS[collection(r)][0], 'back')
    dates = f'{r.get("dateLabel", "原报告生成日")} {r["published"]}'
    if r.get('updated'):
        dates += f' · 修订于 {r["updated"]}'
    if r.get('dataThrough'):
        dates += f' · 数据截至 {r["dataThrough"]}'
    body += head(r['category']+' / RESEARCH', r['title'], dates)
    if r.get('subtitle'):
        body += '<p class="paper-subtitle">'+E(r['subtitle'])+'</p>'
    body += '<article class="prose"><section class="article-intro"><h2>简介</h2><p>'+E(r['summary'])+'</p>'
    if r.get('author'):
        body += '<p class="caption">作者：'+E(r['author'])+'</p>'
    if r.get('pdf'):
        pdf = r['pdf']
        local = (ROOT / pdf).resolve()
        assert local.is_relative_to((ROOT/'assets/papers').resolve()) and local.is_file(), 'PDF must be a published asset'
        assert local.read_bytes().startswith(b'%PDF-'), 'Invalid PDF file'
        size = local.stat().st_size / 1024 / 1024
        body += f'<div class="paper-actions"><a class="cover-primary" href="{E(url(pdf))}" download>下载 PDF ↓</a><span class="caption">PDF · {size:.1f} MB</span></div>'
    if r.get('ssrnUrl'):
        assert r['ssrnUrl'].startswith('https://papers.ssrn.com/'), 'Expected SSRN paper URL'
        body += f'<p><a href="{E(r["ssrnUrl"])}" target="_blank" rel="noopener noreferrer">查看 SSRN 原文 ↗</a></p>'
    body += '</section>'
    if r.get('note'):
        body += '<div class="notice">'+E(r['note'])+'</div>'
    body += markdown(r.get('markdown', ''))
    source = r.get('sourceNote', '来源：Residual Inertia 研究门户的历史报告。本文未重新计算策略收益或回测；情景分析与收益归因的口径见原文说明。历史信号不代表当前市场状态，策略篮子的等权分析不代表实际资金配置。')
    return body+'<h2>来源与局限</h2><p>'+E(source)+'</p><p>仅供研究，不构成投资建议。历史表现不代表未来结果。</p></article>'


def markdown(text):
    # Intentionally limited: raw HTML is escaped; imported reports use headings, lists and tables.
    lines=text.splitlines(); out=[]; i=0
    while i<len(lines):
        line=lines[i].strip()
        if not line: i+=1; continue
        if line.startswith('|'):
            rows=[]
            while i<len(lines) and lines[i].strip().startswith('|'):
                cells=[c.strip() for c in lines[i].strip().strip('|').split('|')]
                if not all(re.fullmatch(r':?-+:?',c) for c in cells): rows.append(cells)
                i+=1
            out.append('<div class="table-scroll" tabindex="0" role="region" aria-label="研究数据表"><table><thead><tr>'+''.join('<th>'+inline(c)+'</th>' for c in rows[0])+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+inline(c)+'</td>' for c in row)+'</tr>' for row in rows[1:])+'</tbody></table></div>'); continue
        if line.startswith('- '):
            items=[]
            while i<len(lines) and lines[i].strip().startswith('- '):
                items.append('<li>'+inline(lines[i].strip()[2:])+'</li>'); i+=1
            out.append('<ul>'+''.join(items)+'</ul>'); continue
        if line.startswith('## '): out.append('<h2>'+inline(line[3:])+'</h2>')
        elif line.startswith('> '): out.append('<blockquote>'+inline(line[2:])+'</blockquote>')
        else: out.append('<p>'+inline(line)+'</p>')
        i+=1
    return ''.join(out)


def snapshot_page(s, previous, following):
    m=s['market']
    body=anchor('overview.html#daily-snapshots','← 市场概览 · 每日快照','back')+head('DAILY SNAPSHOT', s['observationDate']+' · 市场快照', '历史观察记录。归档日期与数据截止日期分别展示。')
    body+=f'<div class="notice"><strong>归档于 {E(s["capturedAt"])}</strong><span>时间为 UTC；观察日按北京时间记录。以下状态均指归档时点。</span></div>'+metrics(s)
    alerts=''.join(f'<p><strong>{E(a["title"])}</strong> · {E(a["detail"])}</p>' for a in s['alerts'])
    body+=f'<div class="two-col">{pillars(s)}<section class="panel"><p class="eyebrow">归档摘要</p><h2>{E(m["regimeState"])} · 综合分数 {number(m["regimeScore"])}</h2><p>{E(s["brief"]["posture"])}</p>{alerts}<p class="caption">风险提示来自原始研究门户。模型目标仓位不是投资者实际仓位。</p></section></div>'
    rows=''.join(f'<tr><td>{E(src["name"])}</td><td>{shortdate(src["asOf"])}</td><td>{E({"current":"当时已覆盖","stale":"当时滞后"}.get(src["status"],src["status"]))}</td><td>{E({"pass":"通过","warning":"存在提示","fail":"未通过"}.get(src["qualityStatus"],src["qualityStatus"]))}</td></tr>' for src in s['sources'])
    body+='<section class="section"><h2>数据来源与截止日期</h2><p class="caption">最新性沿用归档时的交易日历检查，不能解读为今天仍然最新。</p><div class="table-scroll" tabindex="0" role="region" aria-label="数据来源"><table><thead><tr><th>来源</th><th>数据截至</th><th>归档时最新性</th><th>质量检查</th></tr></thead><tbody>'+rows+'</tbody></table></div></section>'
    body+=f'<details class="provenance"><summary>快照来源与核验标识</summary><p>源快照：<code>{E(s["snapshotId"])}</code></p><p>原始快照内容哈希（非本网页文件哈希）：<code>{E(s["contentHash"])}</code></p></details>'
    body+='<div class="pager">'+(anchor('snapshots/'+previous['observationDate']+'.html','← '+previous['observationDate']) if previous else '<span></span>')+(anchor('snapshots/'+following['observationDate']+'.html',following['observationDate']+' →') if following else '<span>最新归档</span>')+'</div>'
    return body


def main():
    snapshots=[json.loads(p.read_text(encoding='utf-8')) for p in sorted((ROOT/'content/snapshots').glob('*.json'))]
    research=[json.loads(p.read_text(encoding='utf-8')) for p in sorted((ROOT/'content/research').glob('*.json'),reverse=True)]
    research.sort(key=lambda r: r['published'], reverse=True)
    assert snapshots, 'Import snapshots before building.'
    # Delete only generated output in this checkout; never touch source archives.
    assert OUT.resolve().parent == ROOT.resolve() and OUT.name == 'dist' and not OUT.is_symlink()
    if OUT.exists(): shutil.rmtree(OUT)
    OUT.mkdir()
    shutil.copytree(ROOT/'assets', OUT/'assets')
    shutil.copy2(ROOT/'assets/brand/favicon.ico', OUT/'favicon.ico')
    latest=snapshots[-1]
    def overview():
        intro=f'<section class="overview-hero"><p class="eyebrow">RESEARCH OBSERVATORY / 市场观测</p><h1>市场留下的信号</h1><p class="lede">每日记录市场状态，把数据归档为可回看的观察。这里不是实时行情，而是有刻度的研究笔记。</p></section>'
        intro+=overview_reading(latest)
        intro+=f'<section class="overview-pillars"><p class="eyebrow">WHAT WE WATCH / 四个维度</p><h2>风险与结构的持续跟踪</h2><p class="section-intro">从金融压力、市场脆弱度、风险与参与度四个角度理解状态。分数越高，越需要关注。</p>{overview_pillars(latest)}</section>'
        intro+=f'<section class="overview-trend"><p class="eyebrow">TREND / 变化</p><h2>市场状态的长期变化</h2><p class="section-intro">过去五年的模型综合分数变化，窗口随数据截止日滚动。</p>{history_chart(snapshots, embedded=True)}</section>'
        intro+=f'<section class="overview-archive" id="daily-snapshots"><p class="eyebrow">ARCHIVE / 每日快照</p><h2>历史观察记录</h2><p class="section-intro">选择日期回看当时的市场状态。共 {len(snapshots)} 份归档。</p>{overview_snapshot_list(snapshots)}</section>'
        intro+=f'<section class="overview-research"><p class="eyebrow">RESEARCH / 研究</p><h2>近期市场研究</h2>{research_cards([r for r in research if collection(r)=="market"][:2])}</section>'
        return intro
    write('index.html','独立研究，从简出发',lambda: homepage(latest,research),'home')
    write('overview.html','市场概览',overview,'overview')
    redirect('snapshots/index.html', '/overview/#daily-snapshots', '每日快照 · 市场概览')
    for i,s in enumerate(snapshots):
        write('snapshots/'+s['observationDate']+'.html',s['observationDate']+' 市场快照',lambda s=s,i=i: snapshot_page(s,snapshots[i-1] if i else None,snapshots[i+1] if i+1<len(snapshots) else None),'overview')
    write('research/index.html','研究档案',lambda: head('RESEARCH','研究，让观察有据可循。','从市场观察到独立专题，按研究方向阅读。')+research_folders(research),'research')
    for key,(title,label,description) in COLLECTIONS.items():
        def folder(key=key,title=title,label=label,description=description):
            reports=[r for r in research if collection(r)==key]
            return anchor('research/index.html','← 研究目录','back')+head(label,title,description)+(research_cards(reports) if reports else '<div class="empty-research"><h2>研究档案待整理</h2><p>这一目录尚未发布报告，整理完成后将在这里收录。</p></div>')
        write(f'research/{key}/index.html',title,folder,'research')
    for r in research:
        write('research/'+r['slug']+'.html',r['title'],lambda r=r: research_article(r),'research',r['summary'])
    write('about.html','关于余势',about,'about')
    write('404.html','页面未找到',lambda:head('404','这页记录还不存在。','请从快照档案或研究目录继续阅读。')+f'<p><a href="https://{CONFIG["domain"]}/">返回首页</a></p>')
    (OUT/'.nojekyll').write_text('',encoding='utf-8')
    (OUT/'CNAME').write_text(CONFIG['domain']+'\n',encoding='utf-8')
    origin='https://'+CONFIG['domain']
    (OUT/'robots.txt').write_text('User-agent: *\nAllow: /\nSitemap: '+origin+'/sitemap.xml\n',encoding='utf-8')
    (OUT/'sitemap.xml').write_text('<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'+''.join('<url><loc>'+origin+'/'+p.replace('index.html','')+'</loc></url>' for p in PATHS if p!='404.html')+'</urlset>',encoding='utf-8')
    print(f'Built {len(PATHS)} HTML pages from {len(snapshots)} snapshots and {len(research)} research reports.')


if __name__=='__main__':
    main()
