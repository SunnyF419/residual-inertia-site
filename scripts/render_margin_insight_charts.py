"""Render the two margin-debt Insight figures from frozen research aggregates.

Run: python scripts/render_margin_insight_charts.py
This redraws the published evidence; it does not estimate a new model.
"""
import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = json.loads((ROOT / 'content/insight-data/margin-debt.json').read_text(encoding='utf8'))
OUT = ROOT / 'assets/insights'
INK, BLUE, SLATE, GRID, PAPER = '#0A2122', '#005CC2', '#526260', '#D9DBD4', '#F2F2EB'


def text(x, y, value, size=22, color=INK, anchor='start', weight=400):
    return f'<text x="{x}" y="{y}" font-size="{size}" fill="{color}" text-anchor="{anchor}" font-weight="{weight}">{html.escape(str(value))}</text>'


def line(x1, y1, x2, y2, color=GRID):
    return f'<path d="M{x1},{y1} L{x2},{y2}" fill="none" stroke="{color}"/>'


def wrap(parts, height, title, description):
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 600 {height}" width="600" height="{height}" role="img" aria-labelledby="title desc">
<title id="title">{html.escape(title)}</title><desc id="desc">{html.escape(description)}</desc>
<rect width="600" height="{height}" fill="{PAPER}"/>
<g font-family="Arial, Noto Sans SC, Microsoft YaHei, sans-serif">{''.join(parts)}</g></svg>'''


def cycles(lang):
    zh = lang == 'zh'
    title = '融资反复扩张与收缩' if zh else 'Borrowing rises and retreats'
    p = [text(24, 36, title, 28, weight=600), text(24, 69, '实际融资余额 · 每段起点 = 100' if zh else 'Real margin debt · each segment starts at 100', 20, SLATE)]
    for j, series in enumerate(DATA['series']):
        top, bottom = 130 + j * 290, 320 + j * 290
        points = series['points']
        start, end = series['start'], series['end']
        p.append(text(24, top-21, start.replace('-', '.') + ' — ' + end.replace('-', '.'), 22, weight=600))
        x = lambda n: 65 + n / (len(points)-1) * 505
        y = lambda value: bottom - value / 325 * (bottom-top)
        for tick in (0, 100, 200, 300):
            p.extend([line(65,y(tick),570,y(tick)),text(51,y(tick)+7,tick,19,SLATE,'end')])
        path = ' '.join(('M' if i==0 else 'L') + f'{x(i):.2f},{y(v):.2f}' for i, (_,v) in enumerate(points))
        p.append(f'<path d="{path}" fill="none" stroke="{BLUE}" stroke-width="2.7" stroke-linejoin="round"/>')
        tick_years = [1997, 2001, 2005, 2009] if j==0 else [2011, 2015, 2019, 2023]
        for year in tick_years:
            n = next(i for i,(d,_) in enumerate(points) if d==f'{year}-01')
            p.append(text(round(x(n),2),bottom+29,year,19,SLATE,'middle'))
    p.append(text(24,667,'2010 年报告口径调整，分段展示。' if zh else 'Separate panels reflect the 2010 reporting change.',19,SLATE))
    return wrap(p,690,title,'Monthly inflation-adjusted margin balances, 1997–2024. The two reporting segments are separately rebased to 100; levels across panels are not directly comparable.')


def drawdowns(lang):
    zh = lang == 'zh'
    title = '危机之外，回撤差距缩小' if zh else 'A smaller gap outside the crisis'
    p = [text(24,36,title,28,weight=600),text(24,69,'未来 12 个月最大回撤的平均值' if zh else 'Average maximum drawdown over the next 12 months',20,SLATE)]
    for i, row in enumerate(DATA['drawdowns']):
        top = 117 + i*222
        heading = ('全样本' if i==0 else '剔除金融危机窗口') if zh else ('Full sample' if i==0 else 'Excluding financial-crisis windows')
        p.append(text(24,top,heading,23,weight=600))
        for k,(key,label,color) in enumerate([('baseline','全部起点' if zh else 'All starts',INK),('mean','高位信号' if zh else 'High signal',BLUE)]):
            y=top+38+k*53
            value=row[key]
            p.append(text(24,y+20,label,21,SLATE))
            width=value/30*325
            p.append(f'<rect x="157" y="{y}" width="{width:.3f}" height="29" fill="{color}"/>')
            p.append(text(round(169+width,3),y+23,f'{value:.1f}%',23,color,weight=600))
        gap = f'差距 {row["gap"]:.1f} 个百分点' if zh else f'Gap: {row["gap"]:.1f} percentage points'
        p.append(text(157,top+163,gap,22,BLUE,weight=600))
    p.append(text(24,550,'高位：融资相对股价的同比增幅（ΔDS）' if zh else 'High signal: annual growth in margin debt / price',19,SLATE))
    p.append(text(24,578,'超过当时历史的 80 分位。全部起点包含高位组。' if zh else 'above its past 80th percentile. All starts include high starts.',18,SLATE))
    return wrap(p,604,title,'Full sample: all starts 16.0%, high signal 22.2%. Excluding forward windows overlapping October 2007 to March 2009: 14.1% and 15.7%. Bars use a common zero baseline and scale. Differences are descriptive, not statistically established.')


def main():
    OUT.mkdir(exist_ok=True)
    for lang in ('zh','en'):
        for name, render in [('cycles',cycles),('drawdowns',drawdowns)]:
            (OUT/f'margin-debt-{name}-{lang}.svg').write_text(render(lang),encoding='utf8')
    print('Rendered four bilingual SVG assets for two figures.')


if __name__ == '__main__':
    main()
