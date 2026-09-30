"""Dependency-free static publisher. Only content/ and assets/ enter the website."""
import argparse
import html
import hashlib
import json
import math
import re
import shutil
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'dist'
CONFIG = json.loads((ROOT / 'site.json').read_text(encoding='utf-8'))
CSS_VERSION = hashlib.sha256((ROOT / 'assets/site.css').read_bytes()).hexdigest()[:12]
ACCOUNT_VERSION = hashlib.sha256((ROOT / 'assets/account.js').read_bytes()).hexdigest()[:12]
E = lambda value: html.escape(str(value if value is not None else '—'), quote=True)

# ── Bilingual support ─────────────────────────────────────────────────────
LANG = 'zh'  # 'zh' or 'en'; set by main() before each build pass

I18N = {
    # Nav
    'nav_home': ('首页', 'Home'),
    'nav_overview': ('市场概览', 'Market'),
    'nav_global': ('全球态势', 'Global Pulse'),
    'account_login': ('登录 / 注册', 'Log in / Sign up'),
    'account_manage': ('报告管理', 'Manage reports'),
    'account_label': ('账户', 'Account'),
    'import_report': ('导入报告', 'Import report'),
    'formal_reports_pending': ('正式报告将于作者发布后显示，周报每周六更新。', 'Author-published reports will appear here. Weekly letters are published on Saturdays.'),
    'nav_research': ('研究', 'Research'),
    'nav_about': ('关于', 'About'),
    'skip': ('跳转正文', 'Skip to content'),
    'nav_aria': ('主导航', 'Main navigation'),
    'global_title': ('全球态势', 'Global Pulse'),
    'global_intro': ('追踪全球事件与航运变化，数据持续更新。', 'Follow global events and maritime developments with continuously updated data.'),
    'global_open': ('全屏打开 ↗', 'Open full screen ↗'),
    'global_login': ('管理登录', 'Admin login'),
    'global_note': ('若嵌入页面未显示，请全屏打开。管理登录在新窗口中进行。', 'If the embedded view is unavailable, open the full-screen version. Management login opens in a new tab.'),
    # Footer
    'footer_system': ('独立投资研究与决策系统', 'Independent Investment Research & Systems'),
    'footer_disclosure': ('披露', 'Disclosure'),
    'footer_disclaimer': ('仅供研究，不构成投资建议。历史结果不代表未来表现。', 'For research purposes only. Not investment advice. Past results do not guarantee future performance.'),
    # Redirect page
    'redirect_text': ('页面地址已更新。', 'Page address has been updated.'),
    'redirect_continue': ('继续阅读', 'Continue'),
    # Cover / homepage
    'cover_hero': ('从市场状态，到下一笔决策。', 'From market state to the next decision.'),
    'cover_system': ('独立投资研究与决策系统', 'Independent Investment Research & Systems'),
    'cover_system_sub': ('Independent Investment Research & Systems', '独立投资研究与决策系统'),
    'cover_read': ('阅读研究', 'Read Research'),
    'cover_overview': ('进入市场概览 ↗', 'Market Overview ↗'),
    'home_title': ('独立研究，从简出发', 'Independent Research, From Simplicity'),
    'home_desc': ('独立投资研究与决策系统。每日市场快照、风险观察与研究档案。', 'Independent investment research and decision systems. Daily market snapshots, risk observations, and research archives.'),
    # Principles
    'principles_eyebrow': ('OUR PRINCIPLES', 'OUR PRINCIPLES'),
    'principles_title': ('研究的四个原则', 'Four Principles of Research'),
    'principle_evidence': ('证据', 'Evidence'),
    'principle_simplicity': ('简洁', 'Simplicity'),
    'principle_system': ('系统', 'System'),
    'principle_independence': ('独立', 'Independence'),
    'principle_evidence_desc': ('以数据与可检验的依据形成判断，也保留结论的边界。', 'Form judgments from data and testable evidence, while preserving the boundaries of conclusions.'),
    'principle_simplicity_desc': ('理解复杂性之后做取舍，让重要的问题与判断清楚可见。', 'Make trade-offs after understanding complexity, so that important questions and judgments are clearly visible.'),
    'principle_system_desc': ('把观察、研究与复盘连接起来，让方法可以积累、检验与修正。', 'Connect observation, research, and review, so that methods can accumulate, be tested, and refined.'),
    'principle_independence_desc': ('保持独立思考，在新的证据出现时保留改变观点的能力。', 'Maintain independent thinking, preserving the ability to change views when new evidence emerges.'),
    # Metrics
    'm_risk': ('风险等级', 'Risk Level'),
    'm_risk_d': ('周度风险模型', 'Weekly risk model'),
    'm_state': ('市场状态', 'Market State'),
    'm_target': ('模型目标仓位', 'Model Target Exposure'),
    'm_target_d': ('模型输出 · 非实际持仓', 'Model output · not actual positions'),
    'm_breadth': ('市场宽度', 'Market Breadth'),
    'm_breadth_d': ('原市场研究指标', 'Original market research indicator'),
    'data_as_of': ('数据截至', 'Data as of'),
    'not_provided': ('未提供', 'N/A'),
    # Pillars
    'pillars_title': ('风险的四个维度', 'Four Dimensions of Risk'),
    'pillars_caption': ('原模型分数与状态；各支柱含义不同，不作为统一买卖阈值。', 'Original model scores and states; pillar meanings differ and are not unified buy/sell thresholds.'),
    # History chart
    'chart_title': ('市场状态的变化', 'Change in Market State'),
    'chart_rolling': ('滚动 5 年', 'Rolling 5-Year'),
    'chart_svg_title': ('过去五年的市场状态分数', 'Market State Scores Over Five Years'),
    'chart_caption_suffix': ('个模型数据点。窗口随每日归档的数据截止日向前滚动。来源：市场研究 Dashboard 历史序列。', 'model data points. Window rolls forward with daily archive data cutoff. Source: Market Research Dashboard historical series.'),
    # Snapshot page
    'snapshot_suffix': ('市场快照', 'Market Snapshot'),
    'snapshot_lede': ('历史观察记录。归档日期与数据截止日期分别展示。', 'Historical observation record. Archive date and data cutoff date are shown separately.'),
    'back_overview': ('← 市场概览 · 每日快照', '← Market Overview · Daily Snapshots'),
    'archived_at': ('归档于', 'Archived'),
    'archive_note': ('时间为 UTC；观察日按北京时间记录。以下状态均指归档时点。', 'Time in UTC; observation date in Beijing time. All states refer to the archive moment.'),
    'summary_eyebrow': ('归档摘要', 'Archive Summary'),
    'summary_caption': ('风险提示来自原始研究门户。模型目标仓位不是投资者实际仓位。', 'Risk alerts from the original research portal. Model target exposure is not actual investor positions.'),
    'sources_title': ('数据来源与截止日期', 'Data Sources & Cutoff Dates'),
    'sources_caption': ('最新性沿用归档时的交易日历检查，不能解读为今天仍然最新。', 'Freshness follows the trading calendar check at archive time and should not be interpreted as current.'),
    'th_source': ('来源', 'Source'),
    'th_asof': ('数据截至', 'Data as of'),
    'th_freshness': ('归档时最新性', 'Freshness at archive'),
    'th_quality': ('质量检查', 'Quality check'),
    'provenance_summary': ('快照来源与核验标识', 'Snapshot source & verification'),
    'src_label': ('源快照：', 'Source snapshot: '),
    'hash_label': ('原始快照内容哈希（非本网页文件哈希）：', 'Original snapshot content hash (not this page hash): '),
    'pager_latest': ('最新归档', 'Latest'),
    # Overview page
    'overview_title': ('市场概览', 'Market Overview'),
    'ov_eyebrow': ('RESEARCH OBSERVATORY / 市场观测', 'RESEARCH OBSERVATORY'),
    'ov_hero': ('市场留下的信号', 'Signals the Market Leaves Behind'),
    'ov_lede': ('每日记录市场状态，把数据归档为可回看的观察。这里不是实时行情，而是有刻度的研究笔记。', 'Daily market state, archived as reviewable observations. Not real-time quotes, but calibrated research notes.'),
    'reading_eyebrow': ('LATEST READING / 最新观察', 'LATEST READING'),
    'score_label': ('综合分数', 'Composite Score'),
    'read_full': ('阅读完整快照 ↗', 'Read full snapshot ↗'),
    'archived_label': ('归档', 'Archived'),
    'ov_pillars_eyebrow': ('WHAT WE WATCH / 四个维度', 'WHAT WE WATCH'),
    'ov_pillars_title': ('风险与结构的持续跟踪', 'Continuous Tracking of Risk & Structure'),
    'ov_pillars_intro': ('从金融压力、市场脆弱度、风险与参与度四个角度理解状态。分数越高，越需要关注。', 'Understanding market state through financial stress, fragility, risk, and participation. Higher scores warrant more attention.'),
    'ov_trend_eyebrow': ('TREND / 变化', 'TREND'),
    'ov_trend_title': ('市场状态的长期变化', 'Long-Term Change in Market State'),
    'ov_trend_intro': ('滚动 5 年的模型综合分数变化，窗口随数据截止日向前滚动。', 'Rolling 5-year composite score changes; window rolls forward with data cutoff dates.'),
    'ov_archive_eyebrow': ('ARCHIVE / 每日快照', 'ARCHIVE'),
    'ov_archive_title': ('历史观察记录', 'Historical Observation Records'),
    'ov_archive_intro': ('选择日期回看当时的市场状态。共 {0} 份归档。', 'Select a date to review the market state at that time. {0} archives in total.'),
    'ov_research_eyebrow': ('RESEARCH / 研究', 'RESEARCH'),
    'ov_research_title': ('近期市场研究', 'Recent Market Research'),
    'snapshot_view': ('查看 →', 'View →'),
    # Research
    'research_title': ('研究档案', 'Research Archive'),
    'research_head': ('研究，让观察有据可循。', 'Research grounds observation in evidence.'),
    'research_sub': ('从市场观察到独立专题，按研究方向阅读。', 'From market observations to independent studies, organized by research direction.'),
    'read_full_article': ('阅读全文 ↗', 'Read full text ↗'),
    'view_ssrn': ('查看 SSRN 原文 ↗', 'View on SSRN ↗'),
    'download_pdf': ('下载 PDF ↓', 'Download PDF ↓'),
    'intro_heading': ('简介', 'Introduction'),
    'author_label': ('作者：', 'Author: '),
    'sources_heading': ('来源与局限', 'Sources & Limitations'),
    'not_advice': ('仅供研究，不构成投资建议。历史表现不代表未来结果。', 'For research purposes only. Not investment advice. Past performance does not guarantee future results.'),
    'empty_title': ('研究档案待整理', 'Research Archive Pending'),
    'empty_text': ('这一目录尚未发布报告，整理完成后将在这里收录。', 'No reports published in this section yet. They will appear here once organized.'),
    'back_research': ('← 研究目录', '← Research'),
    'data_through': ('数据截至', 'Data through'),
    'published_at': ('发表于', 'Published'),
    'report_date': ('原报告生成日', 'Original report date'),
    'revised_at': ('修订于', 'Revised'),
    # Collections
    'col_market': ('市场周报与月报', 'Market Letters'),
    'col_market_label': ('MARKET LETTERS', 'MARKET LETTERS'),
    'col_market_desc': ('沿着周度与月度的时间刻度，梳理市场变化、风险与观察。', 'Tracking market changes, risk, and observations along weekly and monthly intervals.'),
    'col_personal': ('个人专题研究', 'Independent Research'),
    'col_personal_label': ('INDEPENDENT RESEARCH', 'INDEPENDENT RESEARCH'),
    'col_personal_desc': ('围绕具体问题展开研究，包括 WQS 等策略与风险专题。', 'Research around specific questions, including WQS and other strategy and risk topics.'),
    'col_fomc': ('FOMC 政策研究', 'Policy Research'),
    'col_fomc_label': ('POLICY RESEARCH', 'POLICY RESEARCH'),
    'col_fomc_desc': ('关注美联储政策、沟通及其与市场的关系。', 'Examining Fed policy, communication, and their relationship with markets.'),
    'reports_count': ('份报告', 'reports'),
    'reports_pending': ('报告待整理', 'Reports pending'),
    'open_folder': ('打开目录 ↗', 'Open ↗'),
    # About
    'about_title': ('关于余势', 'About Residual Inertia'),
    'about_lede': ('从复杂中提炼判断，为思考留下空间。', 'Distilling judgment from complexity, leaving room for thought.'),
    'founder_eyebrow': ('FOUNDER / 创始人', 'FOUNDER'),
    'founder_bio': ('创建 Residual Inertia｜余势，致力于把市场观察、实证研究与决策系统整合为可重复、可验证的研究基础设施。', 'Founded Residual Inertia, dedicated to integrating market observation, empirical research, and decision systems into repeatable, verifiable research infrastructure.'),
    'founder_card_label': ('创始人卡片，点击查看照片', 'Founder card, click to view photo'),
    'founder_portrait': ('肖像', 'portrait'),
    'disclosure_title': ('披露', 'Disclosure'),
    'disclosure_text': ('内容仅用于独立研究和信息分享，不构成针对任何个人的投资建议。模型仓位不代表实际账户仓位。回测、估算及历史表现均不能保证未来结果。', 'Content is for independent research and information sharing only, and does not constitute personalized investment advice. Model positions do not represent actual account positions. Backtests, estimates, and historical performance cannot guarantee future results.'),
    # 404
    '404_title': ('页面未找到', 'Page Not Found'),
    '404_lede': ('请从快照档案或研究目录继续阅读。', 'Please continue from the snapshot archive or research directory.'),
    'back_home': ('返回首页', 'Back to home'),
    'snapshots_redirect': ('每日快照 · 市场概览', 'Daily Snapshots · Market Overview'),
}

# Market state / pillar / source translations (data-driven content)
STATES = {'建设性': 'Constructive', '谨慎': 'Cautious', '中性': 'Neutral', '防御': 'Defensive', '压力': 'Stressed'}
PILLAR_ZH = {'Financial Stress': '金融压力', 'Fragility': '市场脆弱度', 'Market Risk': '市场风险', 'Participation': '市场参与度'}
SOURCES = {'市场研究': 'Market Research', '策略表现': 'Strategy Performance', '持仓档案': 'Holdings Archive', 'FOMC 政策研究': 'FOMC Policy Research', '全球态势': 'Global Situation', 'ACM 利率观察台': 'ACM Rate Observatory'}
STATUS = {'current': ('当时已覆盖', 'Covered'), 'stale': ('当时滞后', 'Lagged')}
QUALITY = {'pass': ('通过', 'Pass'), 'warning': ('存在提示', 'Warning'), 'fail': ('未通过', 'Fail')}
CATEGORIES = {'周报': ('周报', 'Weekly'), '月报': ('月报', 'Monthly'), 'SSRN 论文': ('SSRN 论文', 'SSRN Paper')}


def L(key):
    """Look up a bilingual UI string by key for the current language."""
    entry = I18N.get(key)
    if entry is None:
        return key
    return entry[1] if LANG == 'en' else entry[0]


def state_label(value):
    """Translate a market state for display."""
    if LANG == 'en':
        return STATES.get(value, value)
    return value


def source_label(value):
    """Translate a source name for display."""
    if LANG == 'en':
        return SOURCES.get(value, value)
    return value


def category_label(value):
    """Translate a research category for display."""
    entry = CATEGORIES.get(value)
    if entry is None:
        return value
    return entry[1] if LANG == 'en' else entry[0]


def status_label(value):
    entry = STATUS.get(value)
    return entry[1] if LANG == 'en' else value if entry is None else entry[0]


def quality_label(value):
    entry = QUALITY.get(value)
    return entry[1] if LANG == 'en' else value if entry is None else entry[0]


def rfield(r, base):
    """Get a research field with language fallback (title → title_en)."""
    if LANG == 'en':
        return r.get(base + '_en', r[base])
    return r[base]


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
ALL_PAGES = []  # (lang, path) for sitemap across both languages


def url(path):
    """Generate a URL; English pages get /en/ prefix, assets stay at root."""
    page, marker, fragment = path.partition('#')
    if page.endswith('index.html'):
        page = page[:-10]
    elif page.endswith('.html') and page != '404.html':
        page = page[:-5] + '/'
    result = '/' + page.lstrip('/') + (marker + fragment if marker else '')
    is_asset = path.startswith('assets/') or path.startswith('favicon')
    if LANG == 'en' and not is_asset:
        result = '/en' + result
    return result


def number(value, pct=False):
    if not isinstance(value, (int, float)) or not math.isfinite(value):
        return '—'
    return f'{value * 100:.1f}%' if pct else f'{value:.1f}'


def shortdate(value):
    return E(str(value)[:10]) if value else L('not_provided')


def anchor(target, text, cls=''):
    return f'<a class="{cls}" href="{E(url(target))}">{text}</a>'


def other_lang_url():
    """URL for the same page in the other language, for the nav toggle."""
    if ROUTE == '404.html':
        return '/en/404.html' if LANG == 'zh' else '/404.html'
    route = ROUTE.replace('index.html', '').replace('.html', '')
    route = route.rstrip('/') + '/' if route else ''
    if LANG == 'zh':
        return '/en/' + route
    return '/' + route


def out_dir():
    """Output directory for current language."""
    return OUT / 'en' if LANG == 'en' else OUT


def shell(title, content, section='', description=None):
    lang_attr = 'en' if LANG == 'en' else 'zh-CN'
    nav = ''.join(anchor(path, name, 'active' if section == key else '') for key, path, name in [
        ('home', 'index.html', L('nav_home')), ('overview', 'overview.html', L('nav_overview')),
        ('global', 'global/index.html', L('nav_global')),
        ('research', 'research/index.html', L('nav_research')), ('about', 'about.html', L('nav_about'))])
    toggle_label = 'EN' if LANG == 'zh' else '中文'
    canonical = 'https://' + CONFIG['domain'] + url(ROUTE)
    desc = description or (L('home_desc') if LANG == 'en' else CONFIG['description'])
    return f'''<!doctype html>
<html lang="{lang_attr}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{E(title)} · Residual Inertia | 余势</title><meta name="description" content="{E(desc)}">
<link rel="canonical" href="{canonical}"><meta property="og:title" content="{E(title)} · Residual Inertia">
<meta property="og:description" content="{E(desc)}"><meta property="og:type" content="website">
<link rel="icon" href="{url('favicon.ico')}" sizes="16x16 32x32 48x48" type="image/x-icon"><link rel="icon" href="{url('assets/brand/favicon.svg')}" type="image/svg+xml"><link rel="apple-touch-icon" href="{url('assets/brand/apple-touch-icon.png')}"><link rel="stylesheet" href="{url('assets/site.css')}?v={CSS_VERSION}">
<script defer src="{url('assets/account.js')}?v={ACCOUNT_VERSION}"></script>
</head><body{' class="global-page"' if section == 'global' else ''}><a class="skip" href="#main">{L('skip')}</a><header class="masthead"><div class="wrap header-inner">
{anchor('index.html', '<img src="'+url('assets/brand/RI-horizontal-white.svg')+'" alt="Residual Inertia | 余势" width="260" height="64">', 'brand')}
<nav aria-label="{L('nav_aria')}">{nav}<a class="account-link" data-account-link data-login="{L('account_login')}" data-account="{L('account_label')}" data-manage="{L('account_label')}" href="https://global.residualinertia.com/auth/login?next=/account">{L('account_login')}</a><a class="lang-toggle" href="{E(other_lang_url())}">{toggle_label}</a></nav></div></header><main id="main" class="wrap{' global-main' if section == 'global' else ''}">{content}</main>
<footer class="wrap site-footer"><div class="footer-main"><div><strong>Residual Inertia | 余势</strong><p>{L('footer_system')}</p><p class="brand-line">{E(CONFIG.get('brandLine',''))}</p></div><div class="footer-meta"><p>{E(CONFIG['motto'])}</p>{anchor('about.html#disclosure', L('footer_disclosure'))}</div></div><div class="footer-bottom"><small>{L('footer_disclaimer')}</small></div></footer>{SMART_NAV_JS}</body></html>'''


def write(route, title, render, section='', description=None):
    global ROUTE
    destination = route if route.endswith('index.html') or route == '404.html' else route[:-5] + '/index.html'
    ROUTE = destination
    p = out_dir() / destination
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(shell(title, render(), section, description), encoding='utf-8')
    PATHS.append(destination)
    ALL_PAGES.append((LANG, destination))
    if destination != route:
        redirect(route, url(destination), title)


def redirect(route, target, title):
    lang_attr = 'en' if LANG == 'en' else 'zh-CN'
    p = out_dir() / route
    p.parent.mkdir(parents=True, exist_ok=True)
    canonical = 'https://' + CONFIG['domain'] + target.split('#')[0]
    p.write_text(f'''<!doctype html><html lang="{lang_attr}"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>{E(title)} · 余势</title>
<meta http-equiv="refresh" content="0;url={E(target)}"><link rel="canonical" href="{E(canonical)}">
</head><body><h1>{E(title)}</h1><p>{L('redirect_text')}<a href="{E(target)}">{L('redirect_continue')}</a></p></body></html>''', encoding='utf-8')


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
    hero = E(CONFIG.get('hero_en' if LANG == 'en' else 'hero', '')).replace('，', '，<br>')
    eyebrow = 'RESIDUAL INERTIA' if LANG == 'en' else 'RESIDUAL INERTIA | 余势'
    return f'''<section class="brand-cover" id="hero" aria-label="Residual Inertia">
{cover_kline()}
<div class="cover-copy"><p class="eyebrow">{eyebrow}</p>
<h1>{hero}</h1><div class="cover-description"><span class="cover-rule" aria-hidden="true"></span>
<p>{L('cover_system')}<span>{L('cover_system_sub')}</span></p></div>
<div class="cover-actions">{anchor('research/index.html', L('cover_read'), 'cover-primary')}{anchor('overview.html', L('cover_overview'), 'cover-secondary')}</div></div>
</section>
'''


def homepage(latest, research):
    return cover()


def principles():
    items = [
        ('Evidence', L('principle_evidence'), L('principle_evidence_desc')),
        ('Simplicity', L('principle_simplicity'), L('principle_simplicity_desc')),
        ('System', L('principle_system'), L('principle_system_desc')),
        ('Independence', L('principle_independence'), L('principle_independence_desc')),
    ]
    def card(en, cn, text):
        span = f'<span>{cn}</span>' if cn != en else ''
        return f'<div><h3>{en}{span}</h3><p>{text}</p></div>'
    return '<section class="principles" id="principles" aria-labelledby="principles-title"><p class="eyebrow">' + L('principles_eyebrow') + '</p><h2 id="principles-title">' + L('principles_title') + '</h2><div class="principle-grid">' + ''.join(card(*item) for item in items) + '</div></section>'


def metrics(s):
    m = s['market']
    specs = [(L('m_risk'), m['riskLevel'], L('m_risk_d'), m['signalDate']),
             (L('m_state'), state_label(m['regimeState']), f"{L('score_label')} {number(m['regimeScore'])} / 100", m['regimeDate']),
             (L('m_target'), number(m['targetExposure'], True), L('m_target_d'), m['signalDate']),
             (L('m_breadth'), number(m['breadth'], True), L('m_breadth_d'), m['breadthDate'])]
    return '<div class="metrics">' + ''.join(f'<section class="metric"><p>{E(label)}</p><strong>{E(value)}</strong><span>{E(detail)}</span><small>{L("data_as_of")} {shortdate(asof)}</small></section>' for label, value, detail, asof in specs) + '</div>'


def pillars(s):
    rows = ''
    for p in s['market'].get('pillars', []):
        score = p.get('score')
        width = min(100, max(0, score)) if isinstance(score, (int, float)) else 0
        tone = {'建设性': 'positive', '谨慎': 'caution', '中性': 'caution', '防御': 'caution', '压力': 'risk'}.get(p['state'], 'neutral')
        label = p['name'] if LANG == 'en' else PILLAR_ZH.get(p['name'], p['name'])
        rows += f'<div class="pillar"><div><span>{E(label)}</span><span>{E(state_label(p["state"]))} <b>{number(score)}</b></span></div><div class="track"><span class="{tone}" style="width:{width:.4f}%"></span></div></div>'
    return f'<section class="panel"><div class="section-title"><h2>{L("pillars_title")}</h2><span class="mono">/ 100</span></div>{rows}<p class="caption">{L("pillars_caption")}</p></section>'


def history_chart(snapshots, embedded=False):
    history = json.loads((ROOT/'content/market/regime-history.json').read_text(encoding='utf-8'))
    usable = history['points']
    start = date.fromisoformat(history['windowStart']).toordinal()
    end = date.fromisoformat(history['windowEnd']).toordinal()
    points = ' '.join(f"{48+(date.fromisoformat(p['date']).toordinal()-start)/max(end-start,1)*600:.2f},{178-p['score']*1.45:.2f}" for p in usable)
    grid = ''.join(f'<line x1="48" y1="{178-v*1.45}" x2="648" y2="{178-v*1.45}"/><text x="8" y="{183-v*1.45}">{v}</text>' for v in [0, 50, 100])
    ticks = ''.join(f'<text x="{48+(date(y,1,1).toordinal()-start)/max(end-start,1)*600:.2f}" y="212" text-anchor="middle">{y}</text>' for y in range(date.fromordinal(start).year+1, date.fromordinal(end).year+1))
    svg = f'<svg viewBox="0 0 684 224" role="img" aria-labelledby="history-title history-desc"><title id="history-title">{L("chart_svg_title")}</title><desc id="history-desc">{history["windowStart"]} — {history["windowEnd"]}, {len(usable)} {L("chart_caption_suffix")}</desc><g class="grid">{grid}</g><polyline class="series" points="{points}"/>{ticks}</svg>'
    caption = f'<p class="caption">{history["windowStart"]} — {history["windowEnd"]} · {len(usable)} {L("chart_caption_suffix")}</p>'
    if embedded:
        return f'<div class="chart-embedded">{svg}{caption}</div>'
    return f'''<section class="panel chart"><div class="section-title"><h2>{L("chart_title")}</h2><span class="mono">{L("chart_rolling")}</span></div>{svg}{caption}</section>'''


def snapshot_rows(snapshots, limit=None):
    rows = []
    for s in list(reversed(snapshots))[:limit]:
        m = s['market']
        rows.append(f'<tr><td>{anchor("snapshots/"+s["observationDate"]+".html", E(s["observationDate"]), "mono")}</td><td>{E(m["riskLevel"])}</td><td>{E(state_label(m["regimeState"]))}</td><td class="numeric">{number(m["regimeScore"])}</td><td class="numeric">{number(m["breadth"],True)}</td><td>{shortdate(m["signalDate"])}</td></tr>')
    return '<div class="table-scroll" tabindex="0" role="region" aria-label="Daily snapshots"><table><thead><tr><th>observation</th><th>risk</th><th>state</th><th class="numeric">score</th><th class="numeric">breadth</th><th>signal</th></tr></thead><tbody>' + ''.join(rows) + '</tbody></table></div>'


def overview_pillars(s):
    items = []
    for p in s['market'].get('pillars', []):
        score = p.get('score')
        width = min(100, max(0, score)) if isinstance(score, (int, float)) else 0
        tone = {'建设性': 'positive', '谨慎': 'caution', '中性': 'caution', '防御': 'caution', '压力': 'risk'}.get(p['state'], 'neutral')
        label = p['name'] if LANG == 'en' else PILLAR_ZH.get(p['name'], p['name'])
        items.append(f'<div class="overview-pillar"><div class="pillar-label"><span>{E(label)}</span><span>{E(state_label(p["state"]))}</span></div><div class="pillar-track"><span class="{tone}" style="width:{width:.4f}%"></span></div><div class="pillar-value">{number(score)}</div></div>')
    return '<div class="overview-pillar-grid">' + ''.join(items) + '</div>'


def overview_snapshot_list(snapshots):
    items = []
    for s in list(reversed(snapshots))[:8]:
        m = s['market']
        items.append(f'<li class="snapshot-item"><a href="{url("snapshots/"+s["observationDate"]+".html")}"><span class="snapshot-date mono">{E(s["observationDate"])}</span><span class="snapshot-state">{E(state_label(m["regimeState"]))}</span><span class="snapshot-score mono">{number(m["regimeScore"])}</span><span class="snapshot-link">{L("snapshot_view")}</span></a></li>')
    return '<ul class="snapshot-list">' + ''.join(items) + '</ul>'


def overview_reading(s):
    m = s['market']
    brief = s.get('brief', {})
    if LANG == 'en':
        posture = f"Composite state {state_label(m['regimeState'])}, score {number(m['regimeScore'])} / 100, breadth {number(m['breadth'], True)}."
    else:
        posture = brief.get('posture', f"综合状态 {m['regimeState']}。")
    return f'<section class="reading-card"><div class="reading-main"><p class="eyebrow">{L("reading_eyebrow")}</p><h2>{E(state_label(m["regimeState"]))}</h2><p class="reading-posture">{E(posture)}</p><p class="reading-caption">{anchor("snapshots/"+s["observationDate"]+".html", L("read_full"))} · {L("data_as_of")} {shortdate(m["signalDate"])} · {E(s["observationDate"])} {L("archived_label")}</p></div><div class="reading-score"><span class="mono">{number(m["regimeScore"])}</span><small>/ 100</small><span class="score-label">{L("score_label")}</span></div></section>'


def research_cards(research):
    cards = []
    for r in research:
        title = rfield(r, 'title')
        summary = rfield(r, 'summary')
        if r.get('dataThrough'):
            date_note = L('data_through') + ' ' + r['dataThrough']
        else:
            date_note = (r.get('dateLabel', L('published_at'))) + ' ' + r['published']
        cards.append(f'<article class="research-card"><p class="eyebrow">{E(category_label(r["category"]))} <span class="mono">{E(r["published"])}</span></p><h3>{anchor("research/"+r["slug"]+".html", E(title))}</h3><p>{E(summary)}</p><div class="card-foot"><span>{E(date_note)}</span>{anchor("research/"+r["slug"]+".html", L("read_full_article"))}</div></article>')
    return '<div class="research-grid">' + ''.join(cards) + '</div>'


COLLECTIONS = {
    'market': ('col_market', 'col_market_label', 'col_market_desc'),
    'personal': ('col_personal', 'col_personal_label', 'col_personal_desc'),
    'fomc': ('col_fomc', 'col_fomc_label', 'col_fomc_desc'),
}


def collection(r):
    return r.get('collection', 'market' if r['category'] in ('周报', '月报') else 'personal')


def research_folders(research):
    cards = []
    for i, (key, (tkey, lkey, dkey)) in enumerate(COLLECTIONS.items(), 1):
        count = sum(collection(r) == key for r in research)
        status = f'{count} {L("reports_count")}' if count else L('reports_pending')
        cards.append(anchor(f'research/{key}/index.html', f'<span class="folder-tab mono">0{i} / {L(lkey)}</span><h2>{L(tkey)}</h2><p>{L(dkey)}</p><div class="folder-foot"><span>{status}</span><span>{L("open_folder")}</span></div>', 'folder-card'))
    return '<div class="folder-grid">' + ''.join(cards) + '</div>'


def about():
    founder_intro = f'''<section class="founder-section" id="founder" aria-labelledby="founder-title">
<div class="founder-card">
<div class="founder-flip-card" role="button" tabindex="0" aria-label="{L('founder_card_label')}">
<div class="founder-flip-inner">
<div class="founder-flip-front">
<img src="{url('assets/brand/RI-symbol-reverse.svg')}" alt="Residual Inertia" width="120" height="85">
</div>
<div class="founder-flip-back">
<img src="{url('assets/brand/founder-sunny.jpg')}" alt="{E(CONFIG['founder'])} {L('founder_portrait')}" width="320" height="400">
</div>
</div>
</div>
<div class="founder-bio">
<p class="eyebrow" id="founder-title">{L('founder_eyebrow')}</p>
<h2>{E(CONFIG['founder'])}</h2>
<p class="brand-line">{E(CONFIG.get('brandLine', ''))}</p>
<p>{L('founder_bio')}</p>
</div>
</div>
</section>'''
    if LANG == 'en':
        intro_text = f'''<article class="prose about-intro">
<p>Residual Inertia is an independent investment research and decision systems platform founded by {E(CONFIG['founder'])}. The platform focuses on quantitative investing, asset pricing, macro markets, financial data, and AI-driven research infrastructure, integrating market observations, empirical research, models, and tools into a repeatable, verifiable research workflow.</p>
<p>Residual Inertia believes that good research does not necessarily come from more complex models, but from clearer questions, more reliable evidence, and methods that can be continuously tested and improved. The platform adheres to Evidence before narrative. Process before prediction. From market state monitoring and thematic research to dashboards, data systems, and research workflows, Residual Inertia aims to gradually build research infrastructure that accumulates over time, iterates continuously, and genuinely serves investment decisions.</p>
</article>'''
    else:
        intro_text = f'''<article class="prose about-intro">
<p>Residual Inertia｜余势是由 {E(CONFIG['founder'])} 创建的独立投资研究与决策系统平台。平台聚焦量化投资、资产定价、宏观市场、金融数据与 AI 驱动的研究基础设施，并将市场观察、实证研究、模型与工具整合进一个可重复、可验证的研究流程。</p>
<p>Residual Inertia 相信，好的研究并不一定来自更复杂的模型，而来自更清晰的问题、更可靠的证据，以及能够被持续检验和改进的方法。平台坚持 Evidence before narrative. Process before prediction. 从市场状态监测、专题研究，到 Dashboard、数据系统与研究工作流，Residual Inertia 希望逐步建立一套能够长期积累、持续迭代，并真正服务于投资决策的研究基础设施。</p>
</article>'''
    return head('ABOUT / RESIDUAL INERTIA', L('about_title'), L('about_lede')) + intro_text + principles() + founder_intro + f'''<article class="prose">
<h2 id="disclosure">{L('disclosure_title')}</h2><p>{L('disclosure_text')}</p></article>'''


def inline(text):
    return re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', E(text))


def research_article(r):
    tkey, _, _ = COLLECTIONS[collection(r)]
    body = anchor('research/' + collection(r) + '/index.html', '← ' + L(tkey), 'back')
    date_label = r.get('dateLabel', L('report_date'))
    dates = f'{date_label} {r["published"]}'
    if r.get('updated'):
        dates += f' · {L("revised_at")} {r["updated"]}'
    if r.get('dataThrough'):
        dates += f' · {L("data_through")} {r["dataThrough"]}'
    body += head(category_label(r['category']) + ' / RESEARCH', rfield(r, 'title'), dates)
    if r.get('subtitle'):
        body += '<p class="paper-subtitle">' + E(r['subtitle']) + '</p>'
    body += '<article class="prose"><section class="article-intro"><h2>' + L('intro_heading') + '</h2><p>' + E(rfield(r, 'summary')) + '</p>'
    if r.get('author'):
        body += '<p class="caption">' + L('author_label') + E(r['author']) + '</p>'
    if r.get('pdf'):
        pdf = r['pdf']
        local = (ROOT / pdf).resolve()
        assert local.is_relative_to((ROOT/'assets/papers').resolve()) and local.is_file(), 'PDF must be a published asset'
        assert local.read_bytes().startswith(b'%PDF-'), 'Invalid PDF file'
        size = local.stat().st_size / 1024 / 1024
        body += f'<div class="paper-actions"><a class="cover-primary" href="{E(url(pdf))}" download>{L("download_pdf")}</a><span class="caption">PDF · {size:.1f} MB</span></div>'
    if r.get('ssrnUrl'):
        assert r['ssrnUrl'].startswith('https://papers.ssrn.com/'), 'Expected SSRN paper URL'
        body += f'<p><a href="{E(r["ssrnUrl"])}" target="_blank" rel="noopener noreferrer">{L("view_ssrn")}</a></p>'
    body += '</section>'
    if r.get('note'):
        body += '<div class="notice">' + E(r['note']) + '</div>'
    body += markdown(rfield(r, 'markdown') or '')
    source = rfield(r, 'sourceNote') or ( '来源：Residual Inertia 研究门户的历史报告。' if LANG == 'zh' else 'Source: historical reports from the Residual Inertia research portal.')
    return body + '<h2>' + L('sources_heading') + '</h2><p>' + E(source) + '</p><p>' + L('not_advice') + '</p></article>'


def markdown(text):
    # Intentionally limited: raw HTML is escaped; imported reports use headings, lists and tables.
    lines = text.splitlines(); out = []; i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line: i += 1; continue
        if line.startswith('|'):
            rows = []
            while i < len(lines) and lines[i].strip().startswith('|'):
                cells = [c.strip() for c in lines[i].strip().strip('|').split('|')]
                if not all(re.fullmatch(r':?-+:?', c) for c in cells): rows.append(cells)
                i += 1
            out.append('<div class="table-scroll" tabindex="0" role="region" aria-label="research data table"><table><thead><tr>' + ''.join('<th>' + inline(c) + '</th>' for c in rows[0]) + '</tr></thead><tbody>' + ''.join('<tr>' + ''.join('<td>' + inline(c) + '</td>' for c in row) + '</tr>' for row in rows[1:]) + '</tbody></table></div>'); continue
        if line.startswith('- '):
            items = []
            while i < len(lines) and lines[i].strip().startswith('- '):
                items.append('<li>' + inline(lines[i].strip()[2:]) + '</li>'); i += 1
            out.append('<ul>' + ''.join(items) + '</ul>'); continue
        if line.startswith('## '): out.append('<h2>' + inline(line[3:]) + '</h2>')
        elif line.startswith('> '): out.append('<blockquote>' + inline(line[2:]) + '</blockquote>')
        else: out.append('<p>' + inline(line) + '</p>')
        i += 1
    return ''.join(out)


def snapshot_page(s, previous, following):
    m = s['market']
    body = anchor('overview.html#daily-snapshots', L('back_overview'), 'back') + head('DAILY SNAPSHOT', s['observationDate'] + ' · ' + L('snapshot_suffix'), L('snapshot_lede'))
    body += f'<div class="notice"><strong>{L("archived_at")} {E(s["capturedAt"])}</strong><span>{L("archive_note")}</span></div>' + metrics(s)
    alerts = ''.join(f'<p><strong>{E(a["title"])}</strong> · {E(a["detail"])}</p>' for a in s['alerts'])
    body += f'<div class="two-col">{pillars(s)}<section class="panel"><p class="eyebrow">{L("summary_eyebrow")}</p><h2>{E(state_label(m["regimeState"]))} · {L("score_label")} {number(m["regimeScore"])}</h2><p>{E(s["brief"]["posture"])}</p>{alerts}<p class="caption">{L("summary_caption")}</p></section></div>'
    rows = ''.join(f'<tr><td>{E(source_label(src["name"]))}</td><td>{shortdate(src["asOf"])}</td><td>{E(status_label(src["status"]))}</td><td>{E(quality_label(src["qualityStatus"]))}</td></tr>' for src in s['sources'])
    body += '<section class="section"><h2>' + L('sources_title') + '</h2><p class="caption">' + L('sources_caption') + '</p><div class="table-scroll" tabindex="0" role="region" aria-label="data sources"><table><thead><tr><th>' + L('th_source') + '</th><th>' + L('th_asof') + '</th><th>' + L('th_freshness') + '</th><th>' + L('th_quality') + '</th></tr></thead><tbody>' + rows + '</tbody></table></div></section>'
    body += f'<details class="provenance"><summary>{L("provenance_summary")}</summary><p>{L("src_label")}<code>{E(s["snapshotId"])}</code></p><p>{L("hash_label")}<code>{E(s["contentHash"])}</code></p></details>'
    body += '<div class="pager">' + (anchor('snapshots/' + previous['observationDate'] + '.html', '← ' + previous['observationDate']) if previous else '<span></span>') + (anchor('snapshots/' + following['observationDate'] + '.html', following['observationDate'] + ' →') if following else '<span>' + L('pager_latest') + '</span>') + '</div>'
    return body


def global_pulse():
    return f'''<section class="global-heading"><div><p class="eyebrow">GLOBAL PULSE</p><h1>{L('global_title')}</h1><p>{L('global_intro')}</p></div><div class="global-actions"><a class="global-login" href="https://global.residualinertia.com/?manage=1" target="_blank" rel="noopener">{L('global_login')}</a><a href="https://global.residualinertia.com/?focus=1&amp;lang={'en' if LANG == 'en' else 'zh'}" target="_blank" rel="noopener">{L('global_open')}</a></div></section>
<iframe class="global-frame" src="https://global.residualinertia.com/?embed=1&amp;lang={'en' if LANG == 'en' else 'zh'}" title="{L('global_title')}" width="1280" height="800" style="display:block;flex:1;min-height:0;width:100%;height:0;border:1px solid var(--grid,#d9dbd4)" allow="fullscreen; camera https://global.residualinertia.com" allowfullscreen referrerpolicy="strict-origin-when-cross-origin"></iframe>
<p class="global-note">{L('global_note')}</p>'''


def build_language(snapshots, research, latest):
    """Build all pages for the current LANG."""
    PATHS.clear()

    def overview():
        intro = f'<section class="overview-hero"><p class="eyebrow">{L("ov_eyebrow")}</p><h1>{L("ov_hero")}</h1><p class="lede">{L("ov_lede")}</p></section>'
        intro += overview_reading(latest)
        intro += f'<section class="overview-pillars"><p class="eyebrow">{L("ov_pillars_eyebrow")}</p><h2>{L("ov_pillars_title")}</h2><p class="section-intro">{L("ov_pillars_intro")}</p>{overview_pillars(latest)}</section>'
        intro += f'<section class="overview-trend"><p class="eyebrow">{L("ov_trend_eyebrow")}</p><h2>{L("ov_trend_title")}</h2><p class="section-intro">{L("ov_trend_intro")}</p>{history_chart(snapshots, embedded=True)}</section>'
        intro += f'<section class="overview-archive" id="daily-snapshots"><p class="eyebrow">{L("ov_archive_eyebrow")}</p><h2>{L("ov_archive_title")}</h2><p class="section-intro">{L("ov_archive_intro").format(len(snapshots))}</p>{overview_snapshot_list(snapshots)}</section>'
        intro += f'<section class="overview-research"><p class="eyebrow">{L("ov_research_eyebrow")}</p><h2>{L("ov_research_title")}</h2>{research_cards([r for r in research if collection(r)=="market"][:2])}</section>'
        return intro

    write('index.html', L('home_title'), lambda: homepage(latest, research), 'home')
    write('overview.html', L('overview_title'), overview, 'overview')
    write('global/index.html', L('global_title'), global_pulse, 'global', L('global_intro'))
    redirect('snapshots/index.html', url('overview.html#daily-snapshots'), L('snapshots_redirect'))
    for i, s in enumerate(snapshots):
        write('snapshots/' + s['observationDate'] + '.html', s['observationDate'] + ' ' + L('snapshot_suffix'), lambda s=s, i=i: snapshot_page(s, snapshots[i-1] if i else None, snapshots[i+1] if i+1 < len(snapshots) else None), 'overview')
    write('research/index.html', L('research_title'), lambda: head('RESEARCH', L('research_head'), L('research_sub')) + research_folders(research), 'research')
    for key, (tkey, lkey, dkey) in COLLECTIONS.items():
        def folder(key=key, lkey=lkey, dkey=dkey):
            reports = [r for r in research if collection(r) == key]
            return anchor('research/index.html', L('back_research'), 'back') + head(L(lkey), L(tkey), L(dkey)) + (f'<p><a class="report-import" data-import-report href="https://global.residualinertia.com/auth/login?next=/research/manage" hidden>{L("import_report")}</a></p>' if key == 'market' else '') + (research_cards(reports) if reports else '<div class="empty-research"><h2>' + L('empty_title') + '</h2><p>' + (L('formal_reports_pending') if key == 'market' else L('empty_text')) + '</p></div>')
        write(f'research/{key}/index.html', L(tkey), folder, 'research')
    for r in research:
        write('research/' + r['slug'] + '.html', rfield(r, 'title'), lambda r=r: research_article(r), 'research', rfield(r, 'summary'))
    write('about.html', L('about_title'), about, 'about')
    write('404.html', L('404_title'), lambda: head('404', L('404_title'), L('404_lede')) + f'<p><a href="https://{CONFIG["domain"]}/">{L("back_home")}</a></p>')


def main():
    global LANG
    snapshots = [json.loads(p.read_text(encoding='utf-8')) for p in sorted((ROOT/'content/snapshots').glob('*.json'))]
    research = [json.loads(p.read_text(encoding='utf-8')) for p in sorted((ROOT/'content/research').glob('*.json'), reverse=True)]
    research.sort(key=lambda r: r['published'], reverse=True)
    assert snapshots, 'Import snapshots before building.'
    # Delete only generated output in this checkout; never touch source archives.
    assert OUT.resolve().parent == ROOT.resolve() and OUT.name == 'dist' and not OUT.is_symlink()
    if OUT.exists(): shutil.rmtree(OUT)
    OUT.mkdir()
    shutil.copytree(ROOT/'assets', OUT/'assets')
    shutil.copy2(ROOT/'assets/brand/favicon.ico', OUT/'favicon.ico')
    latest = snapshots[-1]

    for lang in ('zh', 'en'):
        LANG = lang
        build_language(snapshots, research, latest)

    (OUT/'.nojekyll').write_text('', encoding='utf-8')
    (OUT/'CNAME').write_text(CONFIG['domain'] + '\n', encoding='utf-8')
    origin = 'https://' + CONFIG['domain']
    (OUT/'robots.txt').write_text('User-agent: *\nAllow: /\nSitemap: ' + origin + '/sitemap.xml\n', encoding='utf-8')
    (OUT/'sitemap.xml').write_text('<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' + ''.join('<url><loc>' + origin + '/' + (('en/' if lang == 'en' else '') + p).replace('index.html', '') + '</loc></url>' for lang, p in ALL_PAGES if p != '404.html') + '</urlset>', encoding='utf-8')
    print(f'Built {len(ALL_PAGES)} HTML pages ({len(ALL_PAGES)//2} per language) from {len(snapshots)} snapshots and {len(research)} research reports.')


if __name__ == '__main__':
    main()
