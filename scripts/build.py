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
ROUTE = 'index.html'
PATHS = []


def url(path):
    return '../' * (len(Path(ROUTE).parts) - 1) + path


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
        ('home', 'index.html', '概览'), ('snapshots', 'snapshots/index.html', '每日快照'),
        ('research', 'research/index.html', '研究'), ('about', 'about.html', '关于余势')])
    canonical = 'https://' + CONFIG['domain'] + '/' + ROUTE.replace('index.html', '')
    return f'''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{E(title)} · Residual Inertia | 余势</title><meta name="description" content="{E(description or CONFIG['description'])}">
<link rel="canonical" href="{canonical}"><meta property="og:title" content="{E(title)} · Residual Inertia">
<meta property="og:description" content="{E(description or CONFIG['description'])}"><meta property="og:type" content="website">
<link rel="icon" href="{url('assets/brand/RI_favicon.svg')}" type="image/svg+xml"><link rel="stylesheet" href="{url('assets/site.css')}">
</head><body><a class="skip" href="#main">跳转正文</a><header class="masthead"><div class="wrap header-inner">
{anchor('index.html', '<img src="'+url('assets/brand/RI-horizontal-color.svg')+'" alt="Residual Inertia | 余势" width="260" height="64">', 'brand')}
<nav aria-label="主导航">{nav}</nav></div></header><main id="main" class="wrap">{content}</main>
<footer class="wrap"><div><strong>Residual Inertia | 余势</strong><p>独立投资研究与决策系统</p></div><div><p>What remains persists.</p><small>仅供研究，不构成投资建议。历史结果不代表未来表现。</small></div></footer></body></html>'''


def write(route, title, render, section='', description=None):
    global ROUTE
    ROUTE = route
    p = OUT / route
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(shell(title, render(), section, description), encoding='utf-8')
    PATHS.append(route)


def head(kicker, title, text=''):
    return f'<div class="pagehead"><p class="eyebrow">{E(kicker)}</p><h1>{E(title)}</h1><p class="lede">{E(text)}</p></div>'


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
        rows += f'<div class="pillar"><div><span>{E(names.get(p["name"],p["name"]))}</span><span>{E(p["state"])} <b>{number(score)}</b></span></div><div class="track"><span style="width:{width:.4f}%"></span></div></div>'
    return f'<section class="panel"><div class="section-title"><h2>风险的四个维度</h2><span class="mono">/ 100</span></div>{rows}<p class="caption">原模型分数与状态；各支柱含义不同，不作为统一买卖阈值。</p></section>'


def history_chart(snapshots):
    usable = [s for s in snapshots if isinstance(s['market'].get('regimeScore'), (int,float))]
    start = date.fromisoformat(usable[0]['observationDate']).toordinal()
    end = date.fromisoformat(usable[-1]['observationDate']).toordinal()
    points = ' '.join(f"{48+((date.fromisoformat(s['observationDate']).toordinal()-start)/max(end-start,1))*600:.2f},{178-s['market']['regimeScore']*1.45:.2f}" for s in usable)
    grid = ''.join(f'<line x1="48" y1="{178-v*1.45}" x2="648" y2="{178-v*1.45}"/><text x="8" y="{183-v*1.45}">{v}</text>' for v in [0,50,100])
    return f'''<section class="panel chart"><div class="section-title"><h2>市场状态的变化</h2><span class="mono">{len(usable)} 个观察日</span></div>
<svg viewBox="0 0 684 224" role="img" aria-labelledby="history-title history-desc"><title id="history-title">每日快照中的市场状态分数</title><desc id="history-desc">横轴为归档观察日，纵轴为综合分数，范围 0 到 100。最新分数 {number(usable[-1]['market']['regimeScore'])}。每日数值见快照档案。</desc><g class="grid">{grid}</g><polyline class="series" points="{points}"/><text x="48" y="212">{usable[0]['observationDate']}</text><text x="648" y="212" text-anchor="end">{usable[-1]['observationDate']}</text></svg>
<p class="caption">按归档观察日排列；周度或未更新的源信号可能连续数日相同。</p></section>'''


def snapshot_rows(snapshots, limit=None):
    rows = []
    for s in list(reversed(snapshots))[:limit]:
        m=s['market']
        rows.append(f'<tr><td>{anchor("snapshots/"+s["observationDate"]+".html", E(s["observationDate"]), "mono")}</td><td>{E(m["riskLevel"])}</td><td>{E(m["regimeState"])}</td><td class="numeric">{number(m["regimeScore"])}</td><td class="numeric">{number(m["breadth"],True)}</td><td>{shortdate(m["signalDate"])}</td></tr>')
    return '<div class="table-scroll" tabindex="0" role="region" aria-label="每日快照表格"><table><thead><tr><th>观察日</th><th>风险等级</th><th>市场状态</th><th class="numeric">综合分数</th><th class="numeric">市场宽度</th><th>风险信号截至</th></tr></thead><tbody>'+''.join(rows)+'</tbody></table></div>'


def research_cards(research):
    return '<div class="research-grid">'+''.join(f'<article class="research-card"><p class="eyebrow">{E(r["category"])} <span class="mono">{E(r["published"])}</span></p><h3>{anchor("research/"+r["slug"]+".html",E(r["title"]))}</h3><p>{E(r["summary"])}</p><div class="card-foot"><span>数据截至 {E(r["dataThrough"])}</span>{anchor("research/"+r["slug"]+".html","阅读全文 ↗")}</div></article>' for r in research)+'</div>'


def inline(text):
    return re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', E(text))


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
    body=anchor('snapshots/index.html','← 全部快照','back')+head('DAILY SNAPSHOT', s['observationDate']+' · 市场快照', '历史观察记录。归档日期与数据截止日期分别展示。')
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
    assert snapshots, 'Import snapshots before building.'
    # Delete only generated output in this checkout; never touch source archives.
    assert OUT.resolve().parent == ROOT.resolve() and OUT.name == 'dist' and not OUT.is_symlink()
    if OUT.exists(): shutil.rmtree(OUT)
    OUT.mkdir()
    shutil.copytree(ROOT/'assets', OUT/'assets')
    latest=snapshots[-1]
    def home():
        intro=f'<div class="home-head"><div><p class="eyebrow">RESIDUAL INERTIA / RESEARCH OBSERVATORY</p><h1>市场留下的信号。</h1><p class="lede">每日记录市场状态，让研究保留时间的刻度。</p></div><div class="edition"><span>最新归档观察日</span><strong class="mono">{latest["observationDate"]}</strong>{anchor("snapshots/"+latest["observationDate"]+".html","阅读完整快照 ↗")}</div></div>'
        intro+=f'<div class="dateline"><span>DAILY OBSERVATION</span><span>市场信号截至 {shortdate(latest["market"]["signalDate"])} · 历史归档，非实时行情</span></div>'+metrics(latest)
        intro+='<div class="two-col">'+history_chart(snapshots)+pillars(latest)+'</div>'
        intro+='<section class="section"><div class="section-title"><h2>每日快照</h2>'+anchor('snapshots/index.html',f'全部 {len(snapshots)} 份归档 ↗')+'</div>'+snapshot_rows(snapshots,5)+'</section>'
        intro+='<section class="section"><div class="section-title"><h2>研究与观察</h2>'+anchor('research/index.html','研究档案 ↗')+'</div>'+research_cards(research)+'</section>'
        return intro
    write('index.html','市场观察与独立研究',home,'home')
    write('snapshots/index.html','每日快照',lambda: head('DAILY ARCHIVE','把每一天，留在它发生的时点。',f'{len(snapshots)} 份真实归档 · {snapshots[0]["observationDate"]} — {latest["observationDate"]}。没有归档的日期不补造记录。')+snapshot_rows(snapshots),'snapshots')
    for i,s in enumerate(snapshots):
        write('snapshots/'+s['observationDate']+'.html',s['observationDate']+' 市场快照',lambda s=s,i=i: snapshot_page(s,snapshots[i-1] if i else None,snapshots[i+1] if i+1<len(snapshots) else None),'snapshots')
    write('research/index.html','研究档案',lambda: head('RESEARCH','研究，让观察有据可循。','保留数据时点、方法与局限。以下为已有研究报告的历史归档。')+research_cards(research),'research')
    for r in research:
        def article(r=r):
            return anchor('research/index.html','← 研究档案','back')+head(r['category']+' / RESEARCH ARCHIVE',r['title'],f'原报告生成日 {r["published"]} · 数据截至 {r["dataThrough"]}')+f'<div class="notice">{E(r["note"])}</div><article class="prose">'+markdown(r['markdown'])+'<h2>来源与局限</h2><p>来源：Residual Inertia 研究门户的历史报告。本文未重新计算策略收益或回测；情景分析与收益归因的口径见原文说明。历史信号不代表当前市场状态，策略篮子的等权分析不代表实际资金配置。</p><p>仅供研究，不构成投资建议。历史表现不代表未来结果。</p></article>'
        write('research/'+r['slug']+'.html',r['title'],article,'research',r['summary'])
    write('about.html','关于余势',lambda:head('ABOUT / METHODOLOGY','Residual Inertia | 余势','独立投资研究与决策系统')+'<article class="prose"><h2>What remains persists.</h2><p>从市场状态、风险与参与度出发，建立可以追溯的观察记录。研究与系统是核心，结论随证据变化。</p><h2>如何阅读每日快照</h2><p>观察日是快照建立的北京时间日期；数据截止日属于具体信号。周度风险、日频市场状态和政策研究有不同更新节奏。网站展示保存下来的研究结果，不提供实时行情，也不在线执行策略。</p><h2>数据与方法</h2><p>快照来自既有研究门户的每日归档。数值、风险等级和质量状态沿用原始输出，网站不重新计算模型；同一个信号可能在多个观察日保持不变。研究文章保留原报告的方法、数据时点与局限。</p><h2>披露</h2><p>内容仅用于独立研究和信息分享，不构成针对任何个人的投资建议。模型仓位不代表实际账户仓位。回测、估算及历史表现均不能保证未来结果。</p></article>','about')
    write('404.html','页面未找到',lambda:head('404','这页记录还不存在。','请从快照档案或研究目录继续阅读。')+f'<p><a href="https://{CONFIG["domain"]}/">返回首页</a></p>')
    # A custom-domain 404 can be served from arbitrary depths.
    p=OUT/'404.html'
    p.write_text(p.read_text(encoding='utf-8').replace('href="assets/', 'href="/assets/').replace('src="assets/','src="/assets/').replace('href="index.html"','href="/"').replace('href="snapshots/index.html"','href="/snapshots/"').replace('href="research/index.html"','href="/research/"').replace('href="about.html"','href="/about.html"'),encoding='utf-8')
    (OUT/'.nojekyll').write_text('',encoding='utf-8')
    (OUT/'CNAME').write_text(CONFIG['domain']+'\n',encoding='utf-8')
    origin='https://'+CONFIG['domain']
    (OUT/'robots.txt').write_text('User-agent: *\nAllow: /\nSitemap: '+origin+'/sitemap.xml\n',encoding='utf-8')
    (OUT/'sitemap.xml').write_text('<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'+''.join('<url><loc>'+origin+'/'+p.replace('index.html','')+'</loc></url>' for p in PATHS if p!='404.html')+'</urlset>',encoding='utf-8')
    print(f'Built {len(PATHS)} HTML pages from {len(snapshots)} snapshots and {len(research)} research reports.')


if __name__=='__main__':
    main()
