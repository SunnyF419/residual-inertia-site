"""Dependency-free static publisher. Only content/ and assets/ enter the website."""
import argparse
import html
import hashlib
import json
import math
import re
import shutil
from datetime import date, datetime
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'dist'
CONFIG = json.loads((ROOT / 'site.json').read_text(encoding='utf-8'))
SNAPSHOT_INDEXING = json.loads((ROOT / 'content/snapshot-indexing.json').read_text(encoding='utf-8'))
assert SNAPSHOT_INDEXING.get('version') == 1 and isinstance(SNAPSHOT_INDEXING.get('overrides'), dict), 'Invalid snapshot indexing policy'
CSS_VERSION = hashlib.sha256((ROOT / 'assets/site.css').read_bytes()).hexdigest()[:12]
ACCOUNT_VERSION = hashlib.sha256((ROOT / 'assets/account.js').read_bytes()).hexdigest()[:12]
MOTION_VERSION = hashlib.sha256((ROOT / 'assets/site-motion.js').read_bytes()).hexdigest()[:12]
CHART_VERSION = hashlib.sha256((ROOT / 'assets/market-chart.js').read_bytes()).hexdigest()[:12]
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
    'home_title': ('Residual Inertia 余势｜独立投资研究、量化市场观察与决策系统', 'Residual Inertia | Independent Investment Research & Decision Systems'),
    'home_desc': ('Residual Inertia（余势）是由 Taiyang Feng（Sunny）创立的独立投资研究与决策系统平台，聚焦量化投资、资产定价、宏观市场、市场风险与研究基础设施。', 'Residual Inertia is an independent investment research and decision systems platform founded by Taiyang Feng (Sunny), focused on quantitative investing, asset pricing, macro markets, market risk, and research infrastructure.'),
    'featured_research': ('精选研究', 'Featured Research'),
    'browse_research': ('全部研究 ↗', 'All Research ↗'),
    'recent_updates': ('最近更新', 'Recent Updates'),
    'research_all': ('全部', 'All'),
    'research_categories': ('研究分类', 'Research Categories'),
    'latest_snapshot': ('市场观察归档', 'Market Observation Archive'),
    'composite_cutoff': ('状态数据截至', 'State data as of'),
    'score_ranges': ('分数区间', 'Score Ranges'),
    'archive_older': ('更早的观察记录', 'Earlier Observations'),
    'home_founder': ('创始人', 'Founder'),
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
    'chart_caption_suffix': ('个模型数据点。窗口随最新有效数据的截止日向前滚动。来源：市场研究 Dashboard 历史序列。', 'model data points. Window rolls forward with the latest valid data cutoff. Source: Market Research Dashboard historical series.'),
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
    'updated_label': ('同步于', 'Synced'),
    'current_title': ('最新市场观察', 'Latest Market Reading'),
    'current_lede': ('已通过质量检查的最新模型数据。各项指标按自身截止日期展示，每日历史记录单独保留。', 'Latest model data that passed quality checks. Each metric shows its own cutoff date; daily historical records are kept separately.'),
    'current_read': ('查看最新数据 ↗', 'View latest data ↗'),
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
    'research_pagination': ('研究分页', 'Research pagination'),
    'research_page_label': ('第 {0} 页', 'Page {0}'),
    'research_page_range': ('第 {0}–{1} 篇，共 {2} 篇', '{0}–{1} of {2} reports'),
    'research_previous': ('← 上一页', '← Previous'),
    'research_next': ('下一页 →', 'Next →'),
    'read_full_article': ('阅读全文 ↗', 'Read full text ↗'),
    'view_ssrn': ('查看 SSRN 原文 ↗', 'View on SSRN ↗'),
    'view_pdf': ('浏览 PDF', 'Read PDF'),
    'intro_heading': ('简介', 'Introduction'),
    'author_label': ('作者：', 'Author: '),
    'report_id_label': ('正式编号：', 'Report ID: '),
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
    'col_weekly': ('市场周报', 'Weekly Letters'),
    'col_monthly': ('市场月报', 'Monthly Letters'),
    'col_weekly_desc': ('每周回看市场结构、风险与下一期观察条件。', 'A weekly review of market structure, risk, and conditions to watch next.'),
    'col_monthly_desc': ('按月整理市场变化与中期研究判断。', 'Monthly reviews of market developments and medium-term research.'),
    'col_market_label': ('MARKET LETTERS', 'MARKET LETTERS'),
    'col_market_desc': ('沿着周度与月度的时间刻度，梳理市场变化、风险与观察。', 'Tracking market changes, risk, and observations along weekly and monthly intervals.'),
    'col_personal': ('专题研究', 'Thematic Research'),
    'col_personal_label': ('THEMATIC RESEARCH', 'THEMATIC RESEARCH'),
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
    'founder_role': ('Residual Inertia 创始人、研究者与研究作者。', 'Founder of Residual Inertia, researcher and research author.'),
    'founder_focus': ('研究方向涵盖量化投资、资产定价、宏观市场、市场风险、金融数据与 AI 辅助研究基础设施。', 'Research interests include quantitative investing, asset pricing, macro markets, market risk, financial data and AI-assisted research infrastructure.'),
    'founder_works': ('研究与外部论文记录', 'Research and external paper records'),
    'paper_external': ('外部发表／工作论文记录', 'External publication / working paper record'),
    'paper_local_version': ('本站版本', 'Local version'),
    'author_manuscript': ('作者稿', 'Author manuscript'),
    'working_paper_draft': ('工作论文草稿', 'Working paper draft'),
    'view_doi': ('查看 DOI 论文记录', 'View DOI publication'),
    'hub_directions': ('研究方向与作者', 'Research directions and authors'),
    'research_desc': ('Residual Inertia（余势）的研究档案，收录 Taiyang Feng 与合著者的市场周报、专题论文和 FOMC 政策研究，保留作者、数据截止日、版本与原始资料链接。', 'Research from Residual Inertia by Taiyang Feng and collaborators: market letters, thematic papers and FOMC policy research, with authorship, data cutoffs, versions and original sources.'),
    'scholarly_label': ('学术研究', 'Scholarly Research'),
    'scholarly_desc': ('专题研究中的学术论文，保留合著署名、作者稿版本与 SSRN 外部记录。', 'Academic papers within thematic research, with coauthorship, manuscript versions and external SSRN records.'),
    'related_research': ('相关研究与观察', 'Related research and observations'),
    'research_process': ('研究流程与市场系统', 'Research process and market systems'),
    'research_process_desc': ('市场概览保留模型状态及各项数据日期；每日快照记录当时的公开读数、来源质量与核验标识。周报和政策研究结合这些观察形成文字判断，学术论文保留各自的方法、作者及版本说明。模型读数不等同于实际持仓，也不替代研究中的假设与局限。', 'Market Overview preserves model states and source dates; daily snapshots record public readings, source quality and verification identifiers. Letters and policy research develop written views from these observations, while academic papers retain their own methods, authors and version notes. Model readings are not actual holdings and do not replace research assumptions or limitations.'),
    'selected_work': ('研究与系统入口', 'Research and systems'),
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
CATEGORIES = {'周报': ('周报', 'Weekly'), '月报': ('月报', 'Monthly'), 'SSRN 论文': ('SSRN 论文', 'SSRN Paper'), 'FOMC研究': ('FOMC 政策研究', 'FOMC Policy Research')}


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
  const flipCard=document.querySelector('.founder-flip-card');
  let lastY=window.scrollY,ticking=false;
  function update(){
    const y=window.scrollY;
    if(header){
      if(y>lastY&&y>80)header.classList.add('masthead--hidden');
      else if(y<lastY)header.classList.remove('masthead--hidden');
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
PAGE_SEO = {}  # (lang, path) -> indexability and availability of translated content


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


def production_url(route, lang):
    """Absolute clean page URL, independent of the current rendering language."""
    path = route.removesuffix('index.html')
    return 'https://' + CONFIG['domain'] + '/' + ('en/' if lang == 'en' else '') + path


def research_authors(record):
    """Normalize confirmed aliases only; preserve coauthors and their order."""
    origin = 'https://' + CONFIG['domain'] + '/'
    authors = []
    for name in re.split(r'[;；]', record.get('author') or 'Residual Inertia'):
        name = name.strip()
        if not name:
            continue
        if name.casefold() in {'sunny', 'sunny feng', 'taiyang feng', 'taiyang feng (sunny)', 'taiyang feng（sunny）'}:
            author = {'@id': origin + '#taiyang-feng', '@type': 'Person', 'name': 'Taiyang Feng'}
        elif name.casefold() in {'residual inertia', 'residual inertia research', 'residual inertia | 余势', 'admin'}:
            author = {'@id': origin + '#organization', '@type': 'Organization', 'name': 'Residual Inertia'}
        else:
            key = hashlib.sha256(name.casefold().encode('utf-8')).hexdigest()[:16]
            author = {'@id': origin + '#author-' + key, '@type': 'Person', 'name': name}
        if author['@id'] not in {a['@id'] for a in authors}:
            authors.append(author)
    return authors or [{'@id': origin + '#organization', '@type': 'Organization', 'name': 'Residual Inertia'}]


def author_display(record):
    return ('; ' if LANG == 'en' else '；').join(a['name'] for a in research_authors(record))


def author_links(record):
    names = []
    for author in research_authors(record):
        if author['@id'].endswith('#taiyang-feng'):
            names.append(f'<a rel="author" href="{url("about.html#founder")}">{E(author["name"])}</a>')
        elif author['@type'] == 'Organization':
            names.append(anchor('index.html', E(author['name'])))
        else:
            names.append(E(author['name']))
    return ('; ' if LANG == 'en' else '；').join(names)


def external_publications(record):
    """Only use recorded landing pages/identifiers; never infer a DOI from an SSRN ID."""
    links = []
    if record.get('ssrnUrl'):
        target = record['ssrnUrl']
        parsed = urlsplit(target)
        identifier = parse_qs(parsed.query).get('abstract_id', [''])[0]
        assert parsed.scheme == 'https' and parsed.netloc == 'papers.ssrn.com'
        assert parsed.path == '/sol3/papers.cfm' and identifier.isdigit(), 'Expected SSRN landing page'
        links.append({'kind': 'SSRN', 'url': target, 'value': identifier})
    if record.get('doi') or record.get('doiUrl'):
        value = record.get('doi') or record['doiUrl']
        if value.startswith('https://doi.org/'):
            value = value.removeprefix('https://doi.org/')
        assert re.fullmatch(r'10\.\d{4,9}/[^\s<>"#?]+', value), 'Invalid recorded DOI'
        links.append({'kind': 'DOI', 'url': 'https://doi.org/' + value, 'value': value})
    return links


def snapshot_index_decision(snapshot, earlier=()):
    """Index verified new data vintages or meaningful state/commentary changes, not numeric noise."""
    overrides = SNAPSHOT_INDEXING.get('overrides', {})
    override = overrides.get(snapshot['observationDate'])
    if override:
        assert override.get('index') in (True, False) and isinstance(override.get('index'), bool)
        assert str(override.get('reason', '')).strip(), 'Snapshot overrides require an editorial reason'
        if not override['index']:
            return False, 'editorial: ' + override['reason']

    def complete(s):
        m = s.get('market', {})
        if not isinstance(m, dict) or not isinstance(s.get('brief'), dict):
            return False
        valid = lambda x, lower, upper: isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x) and lower <= x <= upper
        try:
            date.fromisoformat(s['observationDate'])
            datetime.fromisoformat(s['capturedAt'].replace('Z', '+00:00'))
            for key in ('signalDate', 'effectiveDate', 'regimeDate', 'breadthDate'):
                date.fromisoformat(m[key][:10])
        except (KeyError, ValueError, TypeError):
            return False
        pillars = m.get('pillars', [])
        if not isinstance(pillars, list) or not all(isinstance(p, dict) for p in pillars):
            return False
        sources = s.get('sources', [])
        if not isinstance(sources, list) or not all(isinstance(p, dict) for p in sources):
            return False
        verified_sources = []
        for source in sources:
            try:
                date.fromisoformat(source.get('asOf', '')[:10])
            except (ValueError, TypeError):
                continue
            if source.get('id') == 'marketResearch' and source.get('qualityStatus') in ('pass', 'warning'):
                verified_sources.append(source)
        return bool(s.get('snapshotId') and re.fullmatch(r'[a-f0-9]{64}', str(s.get('contentHash') or '')) and
                    m.get('riskLevel') and m.get('regimeState') and
                    valid(m.get('regimeScore'), 0, 100) and valid(m.get('targetExposure'), 0, 1) and valid(m.get('breadth'), 0, 1) and
                    len(pillars) == 4 and {p.get('name') for p in pillars} == {'Financial Stress', 'Fragility', 'Market Risk', 'Participation'} and
                    all(p.get('state') and valid(p.get('score'), 0, 100) for p in pillars) and
                    verified_sources and
                    str(s.get('brief', {}).get('posture', '')).strip())

    if not complete(snapshot):
        return False, 'incomplete-data-or-verification'
    if override:
        return True, 'editorial: ' + override['reason']
    vintage = lambda s: tuple(s['market'][k][:10] for k in ('signalDate', 'effectiveDate', 'regimeDate', 'breadthDate'))
    peers = [s for s in earlier if s['observationDate'] < snapshot['observationDate'] and complete(s) and vintage(s) == vintage(snapshot)]
    if not peers:
        return True, 'new-verified-data-vintage'
    def signature(s):
        m = s['market']
        states = (m['riskLevel'], m['regimeState'], tuple(sorted((p['name'], p['state']) for p in m['pillars'])))
        texts = [s.get('brief', {}).get(k, '') for k in ('headline', 'posture')]
        texts += sorted('|'.join(str(a.get(k, '')) for k in ('severity', 'title', 'detail')) for a in s.get('alerts', []))
        # Replacing number tokens distinguishes prose/state changes from re-filled templates.
        commentary = tuple(re.sub(r'\d+(?:\.\d+)?', '{number}', str(text)).strip() for text in texts)
        return states, commentary
    if all(signature(snapshot) != signature(s) for s in peers):
        return True, 'new-state-or-commentary'
    return False, 'repeated-vintage-and-template-commentary'


def should_index_snapshot(snapshot, earlier=()):
    return snapshot_index_decision(snapshot, earlier)[0]


def breadcrumb_node(title, record=None):
    crumb = lambda label, route: (label, production_url(route, LANG))
    items = [crumb(L('nav_home'), 'index.html')]
    if ROUTE.startswith('research/'):
        items.append(crumb(L('nav_research'), 'research/index.html'))
        if record:
            kind = report_variant(record)
            items.append(crumb(L('col_' + kind), 'research/' + kind + '/index.html'))
            items.append(crumb(rfield(record, 'title'), ROUTE))
        else:
            parts = ROUTE.split('/')
            kind = parts[1] if len(parts) > 2 and parts[1] != 'page' else None
            if kind:
                items.append(crumb(L('col_' + kind), 'research/' + kind + '/index.html'))
            if 'page' in parts:
                number = parts[parts.index('page') + 1]
                items.append(crumb(('第 ' + number + ' 页') if LANG == 'zh' else 'Page ' + number, ROUTE))
    elif ROUTE.startswith('snapshots/') or ROUTE == 'overview/index.html':
        items.append(crumb(L('nav_overview'), 'overview/index.html'))
        items.append((L('ov_archive_title'), production_url('overview/index.html', LANG) + '#daily-snapshots'))
        if ROUTE.startswith('snapshots/'):
            items.append(crumb(ROUTE.split('/')[1], ROUTE))
    elif ROUTE.startswith('market/'):
        items += [crumb(L('nav_overview'), 'overview/index.html'), crumb(title, ROUTE)]
    else:
        return None
    return {'@type': 'BreadcrumbList', '@id': production_url(ROUTE, LANG) + '#breadcrumb',
            'itemListElement': [{'@type': 'ListItem', 'position': i, 'name': name, 'item': target}
                                for i, (name, target) in enumerate(items, 1)]}


def research_nodes(record):
    canonical = production_url(ROUTE, LANG)
    origin = 'https://' + CONFIG['domain'] + '/'
    scholarly = bool(record.get('ssrnUrl') or record.get('doi') or record.get('doiUrl'))
    authors = research_authors(record)
    article = {'@type': 'ScholarlyArticle' if scholarly else 'Article', '@id': canonical + '#article',
               'headline': rfield(record, 'title'), 'description': rfield(record, 'summary'),
               'datePublished': record['published'], 'author': [{'@id': a['@id']} for a in authors],
               'mainEntityOfPage': {'@id': canonical}, 'url': canonical,
               'inLanguage': 'en' if LANG == 'en' else 'zh-CN'}
    if record.get('updated'):
        article['dateModified'] = record['updated']
    if record.get('version'):
        article['version'] = record['version']
    if record.get('dataThrough'):
        article['temporalCoverage'] = record['dataThrough']
    if scholarly:
        article.update(name=rfield(record, 'title'), abstract=rfield(record, 'summary'))
        external = external_publications(record)
        article['sameAs'] = [p['url'] for p in external]
        article['identifier'] = [{'@type': 'PropertyValue', 'propertyID': p['kind'], 'value': p['value'], 'url': p['url']} for p in external]
        if record.get('keywords'):
            article['keywords'] = record['keywords']
        # RI publishes the website presentation, not a claim to have published the external paper.
        page = {'@type': 'WebPage', '@id': canonical, 'url': canonical,
                'mainEntity': {'@id': article['@id']}, 'publisher': {'@id': origin + '#organization'}}
        nodes = [page, article]
    else:
        article['publisher'] = {'@id': origin + '#organization'}
        if record.get('researchId'):
            article['identifier'] = record['researchId']
        nodes = [article]
    nodes += [a for a in authors if a['@id'] not in (origin + '#taiyang-feng', origin + '#organization')]
    return nodes


def snapshot_nodes(snapshot):
    canonical = production_url(ROUTE, LANG)
    origin = 'https://' + CONFIG['domain'] + '/'
    market = snapshot['market']
    fields = [('Risk level', market['riskLevel']), ('Composite risk score', market['regimeScore']),
              ('Model target exposure', market['targetExposure']), ('Market breadth', market['breadth'])]
    fields += [(p['name'], p['score']) for p in market['pillars']]
    return [{'@type': 'Dataset', '@id': canonical + '#dataset',
             'name': snapshot['observationDate'] + (' · 市场快照' if LANG == 'zh' else ' · Market snapshot'),
             'description': snapshot['brief']['posture'], 'url': canonical,
             'mainEntityOfPage': {'@id': canonical}, 'creator': {'@id': origin + '#organization'},
             'publisher': {'@id': origin + '#organization'}, 'dateCreated': snapshot['capturedAt'],
             'temporalCoverage': snapshot['observationDate'], 'inLanguage': 'en' if LANG == 'en' else 'zh-CN',
             'isPartOf': {'@id': origin + 'overview/#daily-snapshots-dataset'},
             'identifier': [snapshot['snapshotId'], {'@type': 'PropertyValue', 'propertyID': 'SHA-256', 'value': snapshot['contentHash']}],
             'variableMeasured': [{'@type': 'PropertyValue', 'name': name, 'value': value} for name, value in fields]}]


def organization_node():
    origin = 'https://' + CONFIG['domain'] + '/'
    return {'@type': 'Organization', '@id': origin + '#organization',
            'name': 'Residual Inertia', 'alternateName': '余势', 'url': origin,
            'description': L('home_desc'), 'logo': origin + 'assets/brand/RI-horizontal-color.svg',
            'founder': {'@id': origin + '#taiyang-feng'}}


def structured_data(home=False, extra_nodes=()):
    origin = 'https://' + CONFIG['domain'] + '/'
    organization_id = origin + '#organization'
    person_id = origin + '#taiyang-feng'
    graph = [
        organization_node(),
        {'@type': 'Person', '@id': person_id, 'name': 'Taiyang Feng',
         'alternateName': 'Sunny', 'url': origin + 'about/#founder',
         'founderOf': {'@id': organization_id}, 'jobTitle': 'Founder and Researcher',
         'description': L('founder_role') + ' ' + L('founder_focus'),
         'knowsAbout': ['Quantitative investing', 'Asset pricing', 'Macro markets', 'Market risk',
                        'Financial data', 'Research infrastructure', 'AI-assisted research infrastructure']},
    ]
    if home:
        graph.append({'@type': 'WebSite', '@id': origin + '#website',
                      'url': origin, 'name': 'Residual Inertia', 'alternateName': '余势',
                      'publisher': {'@id': organization_id}, 'inLanguage': ['zh-CN', 'en'],
                      'hasPart': [{'@id': production_url(route, LANG)} for route in
                                  ('research/index.html', 'overview/index.html', 'global/index.html', 'about/index.html')]})
    graph += list(extra_nodes)
    assert len({node['@id'] for node in graph}) == len(graph), 'Duplicate graph entity'
    # founderOf is the inverse of Schema.org founder, not a new vocabulary property.
    payload = {'@context': {'@vocab': 'https://schema.org/',
                           'founderOf': {'@reverse': 'https://schema.org/founder'}}, '@graph': graph}
    data = json.dumps(payload, ensure_ascii=False, allow_nan=False).replace('<', '\\u003c')
    return '<script type="application/ld+json">' + data + '</script>'


def add_language_alternates():
    """Only pair generated, indexable pages whose content has a translated variant."""
    for lang, route in ALL_PAGES:
        counterpart = ('en' if lang == 'zh' else 'zh', route)
        if not all(PAGE_SEO.get(key, {}).get('indexable') and
                   PAGE_SEO.get(key, {}).get('translated') for key in [(lang, route), counterpart]):
            continue
        zh = production_url(route, 'zh')
        en = production_url(route, 'en')
        links = ''.join(f'<link rel="alternate" hreflang="{code}" href="{E(target)}">'
                        for code, target in [('zh-CN', zh), ('en', en), ('x-default', zh)])
        page = OUT / ('en' if lang == 'en' else '') / route
        assert page.is_file() and (OUT / ('en' if counterpart[0] == 'en' else '') / route).is_file()
        page.write_text(page.read_text(encoding='utf-8').replace('</head>', links + '\n</head>', 1), encoding='utf-8')


def write_sitemap():
    pages = [key for key in dict.fromkeys(ALL_PAGES) if PAGE_SEO[key]['indexable']]
    entries = ''.join('<url><loc>' + E(production_url(route, lang)) + '</loc></url>' for lang, route in pages)
    (OUT/'sitemap.xml').write_text('<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' + entries + '</urlset>', encoding='utf-8')


def number(value, pct=False):
    if not isinstance(value, (int, float)) or not math.isfinite(value):
        return '—'
    return f'{value * 100:.1f}%' if pct else f'{value:.1f}'


def score_tone(value):
    """Same raw-score boundaries as the dashboard's Market Regime _color()."""
    if not isinstance(value, (int, float)) or not math.isfinite(value):
        return 'unknown'
    for threshold, tone in [(35, 'constructive'), (50, 'neutral'), (65, 'caution'), (80, 'defensive')]:
        if value < threshold:
            return tone
    return 'stress'


def score_legend():
    states = [('constructive', '建设性', '<35'), ('neutral', '中性', '35–<50'),
              ('caution', '谨慎', '50–<65'), ('defensive', '防御', '65–<80'), ('stress', '压力', '≥80')]
    return '<ul class="score-legend" aria-label="' + L('score_ranges') + '">' + ''.join(
        f'<li class="tone-{tone}"><i aria-hidden="true"></i>{E(state_label(state))} <span class="mono">{E(bounds)}</span></li>'
        for tone, state, bounds in states) + '</ul>'


def shortdate(value):
    return E(str(value)[:10]) if value else L('not_provided')


def anchor(target, text, cls=''):
    return f'<a class="{cls}" href="{E(url(target))}">{text}</a>'


def action_content(label):
    backward = label.startswith('← ')
    label = label.removeprefix('← ').removesuffix(' ↗').removesuffix(' →')
    icon = '<svg class="action-icon' + (' action-icon-back' if backward else '') + '" width="20" height="20" viewBox="0 0 20 20" aria-hidden="true" focusable="false"><path d="M7 3l6 7-6 7" fill="none" stroke="currentColor" stroke-width="1.3" stroke-linecap="round" stroke-linejoin="round"/></svg>'
    return f'<span>{E(label)}</span>{icon}'


def action_link(target, label, cls='', *, external=False):
    classes = ('action-link ' + cls).strip()
    if external:
        return f'<a class="{classes}" href="{E(target)}" target="_blank" rel="noopener noreferrer">{action_content(label)}</a>'
    return anchor(target, action_content(label), classes)


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


def footer():
    text = lambda cn, en: cn if LANG == 'zh' else en
    research = ''.join(anchor(f'research/{kind}/index.html', L('col_'+kind)) for kind in ('weekly', 'monthly', 'personal', 'fomc'))
    market = anchor('overview.html', L('nav_overview')) + anchor('overview.html#daily-snapshots', text('每日快照档案', 'Daily Snapshot Archive')) + anchor('global/index.html', L('nav_global'))
    account = f'''<a data-account-link data-login="{L('account_login')}" data-account="{L('account_label')}" href="https://global.residualinertia.com/auth/login?next=/account">{L('account_login')}</a>
<a href="https://global.residualinertia.com/auth/register">{text('注册读者账户', 'Create Reader Account')}</a>
<a data-import-report hidden href="https://global.residualinertia.com/auth/login?next=/research/manage">{text('报告管理', 'Manage Reports')}</a>'''
    about = anchor('about.html', L('nav_about')) + anchor('about.html#founder', L('home_founder')) + anchor('about.html#principles', text('品牌理念', 'Our Principles')) + anchor('about.html#disclosure', L('footer_disclosure'))
    columns = [(L('nav_research'), research), (text('市场与系统', 'Markets & Systems'), market), ('MyRI', account), ('Residual Inertia', about)]
    navigation = ''.join(f'<section class="footer-column"><h2>{E(title)}</h2><div>{links}</div></section>' for title, links in columns)
    return f'''<footer class="site-footer"><div class="wrap footer-inner">
<nav class="footer-navigation" aria-label="{text('页脚导航', 'Footer navigation')}">{navigation}</nav>
<div class="footer-signature">{anchor('index.html', '<img src="'+url('assets/brand/RI-symbol-reverse.svg')+'" alt="Residual Inertia | 余势" width="116" height="82">', 'footer-logo')}<p class="footer-brandline">{E(CONFIG['brandLine'])}</p><p class="footer-motto">{E(CONFIG['motto'])}</p></div>
<div class="footer-bottom"><div><p class="footer-descriptor">{L('footer_system')}</p><p class="footer-disclaimer">{L('footer_disclaimer')}</p><small>© Residual Inertia | 余势</small></div><a class="footer-top" href="#top"><span>{text('返回顶部', 'Back to top')}</span><span aria-hidden="true">↑</span></a></div>
</div></footer>'''


def shell(title, content, section='', description=None, indexable=True, schema_nodes=(), record=None):
    lang_attr = 'en' if LANG == 'en' else 'zh-CN'
    nav = ''.join(anchor(path, name, 'active' if section == key else '') for key, path, name in [
        ('home', 'index.html', L('nav_home')), ('overview', 'overview.html', L('nav_overview')),
        ('global', 'global/index.html', L('nav_global')),
        ('research', 'research/index.html', L('nav_research')), ('about', 'about.html', L('nav_about'))])
    toggle_label = 'EN' if LANG == 'zh' else '中文'
    canonical = production_url(ROUTE, LANG)
    desc = description or CONFIG.get('description_en' if LANG == 'en' else 'description', CONFIG['description'])
    seo_title = title if section == 'home' else (title + (' | 余势' if '余势' not in title else '') if 'Residual Inertia' in title else title + ' · Residual Inertia | 余势')
    og_title = seo_title if section == 'home' else (title if 'Residual Inertia' in title else title + ' · Residual Inertia')
    article_meta = ''
    if record:
        article_meta = f'<meta name="author" content="{E(author_display(record))}"><meta property="article:published_time" content="{E(record["published"])}">'
        if record.get('updated'):
            article_meta += f'<meta property="article:modified_time" content="{E(record["updated"])}">'
    return f'''<!doctype html>
<html lang="{lang_attr}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{E(seo_title)}</title><meta name="description" content="{E(desc)}">
<meta name="robots" content="{'index, follow' if indexable else 'noindex, follow'}">
<link rel="canonical" href="{E(canonical)}"><meta property="og:title" content="{E(og_title)}">
<meta property="og:description" content="{E(desc)}"><meta property="og:type" content="{'article' if record else 'website'}"><meta property="og:url" content="{E(canonical)}">
<meta name="twitter:card" content="summary"><meta name="twitter:title" content="{E(og_title)}"><meta name="twitter:description" content="{E(desc)}"><meta name="twitter:url" content="{E(canonical)}">{article_meta}
{structured_data(home=section == 'home', extra_nodes=schema_nodes) if indexable or schema_nodes else ''}
<link rel="icon" href="{url('favicon.ico')}" sizes="16x16 32x32 48x48" type="image/x-icon"><link rel="icon" href="{url('assets/brand/favicon.svg')}" type="image/svg+xml"><link rel="apple-touch-icon" href="{url('assets/brand/apple-touch-icon.png')}"><link rel="stylesheet" href="{url('assets/site.css')}?v={CSS_VERSION}">
<script defer src="{url('assets/account.js')}?v={ACCOUNT_VERSION}"></script>
<script defer src="{url('assets/site-motion.js')}?v={MOTION_VERSION}"></script>
{f'<script defer src="{url("assets/market-chart.js")}?v={CHART_VERSION}"></script>' if 'data-market-chart' in content else ''}
</head><body id="top"{' class="global-page"' if section == 'global' else ' class="home-page"' if section == 'home' else ''}><a class="skip" href="#main">{L('skip')}</a><header class="masthead"><div class="wrap header-inner">
{anchor('index.html', '<img src="'+url('assets/brand/RI-horizontal-white.svg')+'" alt="Residual Inertia | 余势" width="260" height="64">', 'brand')}
<nav aria-label="{L('nav_aria')}">{nav}<a class="account-link" data-account-link data-login="{L('account_login')}" data-account="{L('account_label')}" data-manage="{L('account_label')}" href="https://global.residualinertia.com/auth/login?next=/account">{L('account_login')}</a><a class="lang-toggle" href="{E(other_lang_url())}">{toggle_label}</a></nav></div></header><main id="main" class="wrap{' global-main' if section == 'global' else ''}">{content}</main>
{footer()}{SMART_NAV_JS}</body></html>'''


def write(route, title, render, section='', description=None, indexable=True, translated=True, record=None, snapshot=None, archive_snapshots=None, archive_research=None):
    global ROUTE
    destination = route if route.endswith('index.html') or route == '404.html' else route[:-5] + '/index.html'
    ROUTE = destination
    p = out_dir() / destination
    p.parent.mkdir(parents=True, exist_ok=True)
    nodes = []
    breadcrumb = breadcrumb_node(title, record)
    if breadcrumb:
        nodes.append(breadcrumb)
    if record:
        nodes.extend(research_nodes(record))
    if snapshot:
        nodes.extend(snapshot_nodes(snapshot))
    if archive_snapshots:
        origin = 'https://' + CONFIG['domain'] + '/'
        nodes.append({'@type': 'Dataset', '@id': origin + 'overview/#daily-snapshots-dataset',
                      'name': 'Residual Inertia Daily Market Snapshots',
                      'description': L('ov_archive_intro').format(len(archive_snapshots)),
                      'url': production_url(destination, LANG) + '#daily-snapshots',
                      'creator': {'@id': origin + '#organization'},
                      'publisher': {'@id': origin + '#organization'},
                      'temporalCoverage': archive_snapshots[0]['observationDate'] + '/' + archive_snapshots[-1]['observationDate'],
                      'inLanguage': 'en' if LANG == 'en' else 'zh-CN'})
    if section == 'about':
        nodes.append({'@type': 'AboutPage', '@id': production_url(destination, LANG),
                      'url': production_url(destination, LANG),
                      'about': [{'@id': 'https://' + CONFIG['domain'] + '/#organization'},
                                {'@id': 'https://' + CONFIG['domain'] + '/#taiyang-feng'}],
                      'mainEntity': {'@id': 'https://' + CONFIG['domain'] + '/#taiyang-feng'}})
    origin = 'https://' + CONFIG['domain'] + '/'
    if archive_research is not None:
        canonical = production_url(destination, LANG)
        nodes.extend([{'@type': 'CollectionPage', '@id': canonical, 'url': canonical, 'name': title,
                       'publisher': {'@id': origin + '#organization'}, 'isPartOf': {'@id': origin + '#website'},
                       'mainEntity': {'@id': canonical + '#reports'}},
                      {'@type': 'ItemList', '@id': canonical + '#reports',
                       'itemListElement': [{'@type': 'ListItem', 'position': i,
                                            'item': {'@id': production_url('research/' + r['slug'] + '/index.html', LANG) + '#article',
                                                     'url': production_url('research/' + r['slug'] + '/index.html', LANG),
                                                     'name': rfield(r, 'title')}} for i, r in enumerate(archive_research, 1)]}])
    if section == 'global':
        nodes.extend([{'@type': 'WebPage', '@id': production_url(destination, LANG),
                       'url': production_url(destination, LANG), 'name': title,
                       'isPartOf': {'@id': origin + '#website'},
                       'publisher': {'@id': origin + '#organization'},
                       'mainEntity': {'@id': 'https://global.residualinertia.com/#application'}},
                      {'@type': 'WebApplication', '@id': 'https://global.residualinertia.com/#application',
                       'name': 'Global Pulse', 'alternateName': '全球态势',
                       'url': 'https://global.residualinertia.com/',
                       'creator': {'@id': origin + '#organization'}, 'description': L('global_intro')}])
    if destination == 'overview/index.html':
        nodes.append({'@type': 'WebPage', '@id': production_url(destination, LANG),
                      'name': title, 'url': production_url(destination, LANG),
                      'isPartOf': {'@id': origin + '#website'},
                      'publisher': {'@id': origin + '#organization'},
                      'mainEntity': {'@id': origin + 'overview/#daily-snapshots-dataset'},
                      'relatedLink': production_url('global/index.html', LANG)})
    p.write_text(shell(title, render(), section, description, indexable=indexable, schema_nodes=nodes, record=record), encoding='utf-8')
    PATHS.append(destination)
    ALL_PAGES.append((LANG, destination))
    PAGE_SEO[(LANG, destination)] = {'indexable': indexable, 'translated': translated}
    if destination != route:
        redirect(route, url(destination), title)


def redirect(route, target, title):
    lang_attr = 'en' if LANG == 'en' else 'zh-CN'
    p = out_dir() / route
    p.parent.mkdir(parents=True, exist_ok=True)
    canonical = 'https://' + CONFIG['domain'] + target.split('#')[0]
    p.write_text(f'''<!doctype html><html lang="{lang_attr}"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>{E(title)} · 余势</title>
<meta name="robots" content="noindex, follow">
<meta http-equiv="refresh" content="0;url={E(target)}"><link rel="canonical" href="{E(canonical)}">
</head><body><h1>{E(title)}</h1><p>{L('redirect_text')}<a href="{E(target)}">{L('redirect_continue')}</a></p></body></html>''', encoding='utf-8')


def head(kicker, title, text=''):
    return f'<div class="pagehead"><p class="eyebrow">{E(kicker)}</p><h1>{E(title)}</h1><p class="lede">{E(text)}</p></div>'


def cover_kline():
    # A decorative brand motif, never market data or a model output.
    candles = []
    previous = 60
    for i in range(18):
        close = max(15, min(105, 60 + math.sin(i * .8) * 14 + math.cos(i * 1.4) * 8))
        top = min(previous, close)
        color = '#5d8f7e' if close <= previous else '#c86159'
        x = i * 40 + 20
        candles.append(f'<line x1="{x}" y1="{max(5, top-8-(i%4)*2):.1f}" x2="{x}" y2="{min(115, max(previous,close)+8+(i%3)*3):.1f}" stroke="{color}" stroke-width="1.5"/>')
        candles.append(f'<rect x="{x-11}" y="{top:.1f}" width="22" height="{max(2, abs(close-previous)):.1f}" fill="{color}" rx="1"/>')
        previous = close
    return '<svg class="cover-kline" viewBox="0 0 720 120" preserveAspectRatio="none" aria-hidden="true" focusable="false"><defs><clipPath id="kline-clip"><rect id="kline-clip-rect" width="720" height="120"/></clipPath></defs><g clip-path="url(#kline-clip)">' + ''.join(candles) + '</g></svg>'


def cover():
    hero = E(CONFIG.get('hero_en' if LANG == 'en' else 'hero', '')).replace('，', '，<br>')
    eyebrow = 'RESIDUAL INERTIA' if LANG == 'en' else 'RESIDUAL INERTIA | 余势'
    return f'''<section class="brand-cover" id="hero" aria-label="Residual Inertia">
<div class="cover-copy"><p class="eyebrow">{eyebrow}</p>
<h1>{hero}</h1><div class="cover-description"><span class="cover-rule" aria-hidden="true"></span>
<p>{L('cover_system')}<span>{L('cover_system_sub')}</span></p></div>
<p class="cover-founder">{L('home_founder')} · {anchor('about.html#founder', E(CONFIG['founder']))}</p>
<div class="cover-actions">{anchor('research/index.html', action_content(L('cover_read')), 'cover-primary')}{action_link('overview.html', L('cover_overview'), 'cover-secondary')}</div></div>
<div class="cover-emblem"><span class="emblem-wordmark">Residual Inertia | 余势</span>
<img src="{url('assets/brand/RI-symbol-reverse.svg')}" alt="" width="232" height="164">
<div class="emblem-caption"><p>{E(CONFIG['brandLine'])}</p><span>{E(CONFIG['motto'])}</span></div></div>{cover_kline()}
</section>
'''


def homepage(latest, research):
    featured = [r for r in research if r.get('ssrnUrl')][:2] or research[:2]
    content = cover() + f'<p class="brand-definition">{E(L("home_desc"))}</p>'
    if featured:
        content += f'<section class="home-featured" aria-labelledby="featured-title"><div class="editorial-heading"><div><p class="eyebrow">SELECTED PAPERS</p><h2 id="featured-title">{L("featured_research")}</h2></div>{action_link("research/index.html", L("browse_research"))}</div>{research_cards(featured)}</section>'
    updates = [(latest['observationDate'], L('current_title') if latest.get('kind') == 'current' else L('latest_snapshot'), L('nav_overview'), reading_route(latest))]
    updates += [(r['published'], rfield(r, 'title'), category_label(r['category']), 'research/' + r['slug'] + '.html') for r in research]
    updates.sort(key=lambda item: item[0], reverse=True)
    rows = ''.join(f'<li><time class="mono" datetime="{E(day)}">{E(day)}</time>{anchor(route, E(title))}<span>{E(kind)}</span></li>' for day, title, kind, route in updates[:3])
    content += f'<section class="home-updates" aria-labelledby="updates-title"><div><p class="eyebrow">NOTEBOOK</p><h2 id="updates-title">{L("recent_updates")}</h2></div><ul class="update-list">{rows}</ul></section>'
    return content


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
    return '<div class="metrics">' + ''.join(f'<section class="metric"><p>{E(label)}</p><strong>{E(value)}</strong><span class="{"score-value tone-" + score_tone(m["regimeScore"]) if i == 1 else ""}">{E(detail)}</span><small>{L("data_as_of")} {shortdate(asof)}</small></section>' for i, (label, value, detail, asof) in enumerate(specs)) + '</div>'


def pillars(s):
    rows = ''
    for p in s['market'].get('pillars', []):
        score = p.get('score')
        width = min(100, max(0, score)) if isinstance(score, (int, float)) and math.isfinite(score) else 0
        tone = 'tone-' + score_tone(score)
        label = p['name'] if LANG == 'en' else PILLAR_ZH.get(p['name'], p['name'])
        rows += f'<div class="pillar"><div><span>{E(label)}</span><span>{E(state_label(p["state"]))} <b>{number(score)}</b></span></div><div class="track"><span class="{tone}" style="width:{width:.4f}%"></span></div></div>'
    return f'<section class="panel"><div class="section-title"><h2>{L("pillars_title")}</h2><span class="mono">/ 100</span></div>{rows}<p class="caption">{L("pillars_caption")}</p></section>'


def history_chart(snapshots, embedded=False):
    history = json.loads((ROOT/'content/market/regime-history.json').read_text(encoding='utf-8'))
    usable = history['points']
    start = date.fromisoformat(history['windowStart']).toordinal()
    end = date.fromisoformat(history['windowEnd']).toordinal()
    latest = usable[-1]
    states = [('constructive', '建设性', 0, 35), ('neutral', '中性', 35, 50),
              ('caution', '谨慎', 50, 65), ('defensive', '防御', 65, 80), ('stress', '压力', 80, 100)]
    x = lambda day: 40 + (date.fromisoformat(day).toordinal()-start)/max(end-start,1)*1140
    y = lambda score: 266-score*2.42
    points = ' '.join(f'{x(p["date"]):.2f},{y(p["score"]):.2f}' for p in usable)
    bands = ''.join(f'<rect class="market-band tone-{tone}" x="40" y="{y(hi)}" width="1140" height="{(hi-lo)*2.42}"/>' for tone, _, lo, hi in states)
    grid = ''.join(f'<line x1="40" y1="{y(v)}" x2="1180" y2="{y(v)}"/><text x="30" y="{y(v)+4}" text-anchor="end">{v}</text>' for v in [0, 35, 50, 65, 80, 100])
    ticks = ''.join(f'<text x="{x(date(yr,1,1).isoformat())}" y="292" text-anchor="middle">{yr}</text>' for yr in range(date.fromordinal(start).year+1, date.fromordinal(end).year+1))
    svg = f'<svg class="market-svg" viewBox="0 0 1200 300" preserveAspectRatio="none" role="img" aria-labelledby="history-title history-desc"><title id="history-title">{L("chart_svg_title")}</title><desc id="history-desc">{history["windowStart"]} — {history["windowEnd"]}, {len(usable)} {L("chart_caption_suffix")}</desc><g data-chart-bands>{bands}</g><g class="market-grid" data-chart-grid>{grid}</g><polyline class="market-series" data-chart-series points="{points}"/><g data-chart-ticks>{ticks}</g><circle class="market-endpoint tone-{score_tone(latest["score"])}" data-chart-endpoint cx="{x(latest["date"])}" cy="{y(latest["score"])}" r="4"/><g data-chart-cursor hidden><line class="market-cursor"/><circle r="4"/></g></svg>'
    zh = LANG == 'zh'
    text = lambda cn, en: cn if zh else en
    buttons = ''.join(f'<button type="button" data-chart-range="{months}" aria-pressed="{"true" if months == 60 else "false"}">{label}</button>' for months, label in [(1,text('近 1 月','1M')), (6,text('近半年','6M')), (12,text('近 1 年','1Y')), (60,text('近 5 年','5Y'))])
    legend = ''.join(f'<li class="tone-{tone}"><i aria-hidden="true"></i>{E(state_label(state))}<span>{"≥80" if lo == 80 else "<35" if lo == 0 else str(lo)+"–<"+str(hi)}</span></li>' for tone, state, lo, hi in states)
    payload = json.dumps({'windowStart':history['windowStart'], 'windowEnd':history['windowEnd'],
                          'points':[dict(p, label=state_label(p['state'])) for p in usable],
                          'rangeLabel':text('所选范围','Selected range'), 'countLabel':text('个数据点','data points'),
                          'scoreLabel':text('综合分数','Composite score')}, ensure_ascii=False, separators=(',',':')).replace('<','\\u003c')
    return f'''<div class="market-panel" data-market-chart>
<div class="market-toolbar"><div class="market-latest"><span>{text('历史序列最新值','Latest in history')}</span><strong class="score-value tone-{score_tone(latest['score'])}">{number(latest['score'])}<small> / 100</small></strong><span class="market-status score-value tone-{score_tone(latest['score'])}">{E(state_label(latest['state']))}</span><time class="mono" datetime="{latest['date']}">{latest['date']}</time></div><div class="market-ranges" data-chart-controls hidden role="group" aria-label="{text('图表时间范围','Chart time range')}">{buttons}</div></div>
<div class="market-plot">{svg}<div class="market-tooltip" data-chart-tooltip hidden></div></div>
<div class="market-browse" data-chart-controls hidden><label for="market-day">{text('逐日查看','Explore by date')}</label><input id="market-day" data-chart-slider type="range" min="0" max="{len(usable)-1}" value="{len(usable)-1}" aria-label="{text('用方向键查看历史日期和分数','Use arrow keys to explore historical dates and scores')}"><output data-chart-readout for="market-day" aria-live="polite"></output></div>
<ul class="market-legend" aria-label="{L('score_ranges')}">{legend}</ul>
<p class="market-window mono" data-chart-window>{history['windowStart']} — {history['windowEnd']} · {len(usable)} {text('个数据点','data points')}</p><p class="market-source">{text('来源：市场研究 Dashboard 历史序列。滚动 5 年；分数越高，越需要关注。色带按原始分数区间划分。','Source: Market Research Dashboard historical series. Rolling 5-year window; higher scores warrant more attention. Bands use raw score thresholds.')}</p>
<script type="application/json" data-chart-data>{payload}</script></div>'''


def snapshot_rows(snapshots, limit=None):
    rows = []
    for s in list(reversed(snapshots))[:limit]:
        m = s['market']
        rows.append(f'<tr><td>{anchor("snapshots/"+s["observationDate"]+".html", E(s["observationDate"]), "mono")}</td><td>{E(m["riskLevel"])}</td><td>{E(state_label(m["regimeState"]))}</td><td class="numeric score-value tone-{score_tone(m["regimeScore"])}">{number(m["regimeScore"])}</td><td class="numeric">{number(m["breadth"],True)}</td><td>{shortdate(m["signalDate"])}</td></tr>')
    return '<div class="table-scroll" tabindex="0" role="region" aria-label="Daily snapshots"><table><thead><tr><th>observation</th><th>risk</th><th>state</th><th class="numeric">score</th><th class="numeric">breadth</th><th>signal</th></tr></thead><tbody>' + ''.join(rows) + '</tbody></table></div>'


def overview_pillars(s):
    items = []
    for p in s['market'].get('pillars', []):
        score = p.get('score')
        width = min(100, max(0, score)) if isinstance(score, (int, float)) and math.isfinite(score) else 0
        tone = 'tone-' + score_tone(score)
        label = p['name'] if LANG == 'en' else PILLAR_ZH.get(p['name'], p['name'])
        items.append(f'<div class="overview-pillar"><div class="pillar-label"><span>{E(label)}</span><span>{E(state_label(p["state"]))}</span></div><div class="pillar-track"><span class="{tone}" style="width:{width:.4f}%"></span></div><div class="pillar-value score-value {tone}">{number(score)}</div></div>')
    return '<div class="overview-pillar-grid">' + ''.join(items) + '</div>'


def overview_snapshot_list(snapshots):
    items = []
    for s in reversed(snapshots):
        m = s['market']
        items.append(f'<li class="snapshot-item"><a href="{url("snapshots/"+s["observationDate"]+".html")}"><time datetime="{E(s["observationDate"])}" class="snapshot-date mono">{E(s["observationDate"])}</time><span class="snapshot-state">{E(state_label(m["regimeState"]))}</span><span class="snapshot-score mono score-value tone-{score_tone(m["regimeScore"])}">{number(m["regimeScore"])}</span><span class="snapshot-link">{L("snapshot_view")}</span></a></li>')
    result = '<ul class="snapshot-list">' + ''.join(items[:6]) + '</ul>'
    if len(items) > 6:
        result += '<details class="archive-more"><summary>' + L('archive_older') + f' · {len(items)-6}</summary><ul class="snapshot-list">' + ''.join(items[6:]) + '</ul></details>'
    return result


def reading_route(s):
    return 'market/latest.html' if s.get('kind') == 'current' else 'snapshots/' + s['observationDate'] + '.html'


def latest_reading(snapshots):
    archived = snapshots[-1]
    path = ROOT/'content/market/latest.json'
    if not path.exists():
        return archived
    current = json.loads(path.read_text(encoding='utf-8'))
    if all(current['market'][key][:10] >= archived['market'][key][:10] for key in ('regimeDate', 'signalDate', 'breadthDate')):
        return current
    return archived


def overview_reading(s):
    m = s['market']
    brief = s.get('brief', {})
    if LANG == 'en':
        posture = f"Composite state {state_label(m['regimeState'])}, score {number(m['regimeScore'])} / 100, breadth {number(m['breadth'], True)}."
    else:
        posture = brief.get('posture', f"综合状态 {m['regimeState']}。")
    tone = 'tone-' + score_tone(m['regimeScore'])
    stamp = L('updated_label') + ' ' + E(s['capturedAt'].replace('T', ' ').replace('Z', ' UTC')) if s.get('kind') == 'current' else E(s['observationDate']) + ' ' + L('archived_label')
    return f'<section class="reading-card {tone}"><div class="reading-main"><p class="eyebrow">{L("reading_eyebrow")}</p><h2 class="reading-state">{E(state_label(m["regimeState"]))}</h2><p class="reading-posture">{E(posture)}</p><p class="reading-caption">{L("composite_cutoff")} {shortdate(m["regimeDate"])}<br>{stamp}</p></div><div class="reading-score"><span class="mono score-value">{number(m["regimeScore"])}</span><small>/ 100</small><span class="score-label">{L("score_label")}</span></div><div class="reading-foot">{action_link(reading_route(s), L("current_read") if s.get("kind") == "current" else L("read_full"))}</div></section>'


def research_cards(research):
    cards = []
    for r in research:
        title = rfield(r, 'title')
        summary = rfield(r, 'summary')
        group = collection(r)
        assert group in COLLECTIONS, 'Unknown research collection'
        variant = report_variant(r)
        series = {'weekly':'WEEKLY REVIEW','monthly':'MONTHLY LETTER','personal':'THEMATIC RESEARCH','fomc':'POLICY / FOMC'}[variant]
        issue, separator, cover_title = title.partition(': ' if LANG == 'en' else '：')
        if not separator:
            issue, cover_title = '', title
        identity = r.get('researchId', '')
        if not identity and r.get('ssrnUrl'):
            match = re.search(r'abstract_id=(\d+)', r['ssrnUrl'])
            identity = 'SSRN / ' + match[1] if match else 'SSRN'
        if r.get('dataThrough'):
            date_note = L('data_through') + ' ' + r['dataThrough']
        else:
            date_note = (r.get('dateLabel_en', L('published_at')) if LANG == 'en' else r.get('dateLabel', L('published_at'))) + ' ' + r['published']
        subtitle = f'<p class="research-subtitle">{E(rfield(r, "subtitle"))}</p>' if r.get('subtitle') else ''
        cover = f'''<div class="report-cover report-cover-{variant}">
<div class="report-cover-top"><span class="report-brand">Residual Inertia | 余势</span><span class="report-category">{E(category_label(r['category']))}</span></div>
<div class="report-title-block"><p class="report-series">{series}</p>{('<p class="report-issue">'+E(issue)+'</p>') if issue else ''}<h3>{E(cover_title)}</h3></div>
<div class="report-cover-bottom"><span class="mono">{E(identity)}</span><span>{E(date_note)}</span></div></div>'''
        cards.append(f'<article class="research-card report-card"><a class="report-card-link" href="{url("research/"+r["slug"]+".html")}" aria-label="{E(title)}">{cover}<div class="report-card-body">{subtitle}<p class="research-summary">{E(summary)}</p><div class="card-foot"><div class="report-byline"><span>{E(author_display(r))}</span><time class="mono" datetime="{E(r["published"])}">{E(r["published"])}</time></div><span class="report-readmore">{action_content(L("read_full_article"))}</span></div></div></a></article>')
    return '<div class="research-grid">' + ''.join(cards) + '</div>'


COLLECTIONS = {
    'market': ('col_market', 'col_market_label', 'col_market_desc'),
    'personal': ('col_personal', 'col_personal_label', 'col_personal_desc'),
    'fomc': ('col_fomc', 'col_fomc_label', 'col_fomc_desc'),
}


def collection(r):
    return r.get('collection', 'market' if r['category'] in ('周报', '月报') else 'personal')


def report_variant(r):
    if r['category'] == '周报':
        return 'weekly'
    if r['category'] == '月报':
        return 'monthly'
    return 'fomc' if collection(r) == 'fomc' else 'personal'


def research_navigation(research, active='all'):
    items = [('all', 'research/index.html', L('research_all'), len(research))]
    items += [(key, f'research/{key}/index.html', L('col_'+key), sum(report_variant(r) == key for r in research)) for key in ('weekly','monthly','personal','fomc')]
    links = ''.join(f'<a class="filter-{key}" href="{url(route)}"' + (' aria-current="page"' if key == active else '') + f'>{E(label)}<span class="mono">{count}</span></a>' for key, route, label, count in items)
    return f'<nav class="research-filter" aria-label="{L("research_categories")}">{links}</nav>'


RESEARCH_PAGE_SIZE = 6


def research_page_count(reports):
    return max(1, (len(reports) + RESEARCH_PAGE_SIZE - 1) // RESEARCH_PAGE_SIZE)


def research_page_route(base, page):
    return f'{base}/index.html' if page == 1 else f'{base}/page/{page}/index.html'


def research_library(reports, page=1, base='research', empty=''):
    total_pages = research_page_count(reports)
    assert 1 <= page <= total_pages, 'Invalid research page'
    start = (page - 1) * RESEARCH_PAGE_SIZE
    body = '<section class="research-library" aria-label="' + L('research_title') + '">' + (research_cards(reports[start:start + RESEARCH_PAGE_SIZE]) if reports else empty)
    if total_pages > 1:
        def page_link(number, label, cls=''):
            return f'<a class="{cls}" href="{url(research_page_route(base, number))}" aria-label="{E(L("research_page_label").format(number))}"' + (' aria-current="page"' if number == page else '') + f'>{label}</a>'
        previous = page_link(page - 1, L('research_previous'), 'research-page-direction') if page > 1 else f'<span class="research-page-direction" aria-disabled="true">{L("research_previous")}</span>'
        following = page_link(page + 1, L('research_next'), 'research-page-direction') if page < total_pages else f'<span class="research-page-direction" aria-disabled="true">{L("research_next")}</span>'
        numbers = sorted({1, total_pages} | set(range(max(1, page - 2), min(total_pages, page + 2) + 1)))
        links = []
        for i, number in enumerate(numbers):
            if i and number > numbers[i - 1] + 1:
                links.append('<span class="research-page-gap" aria-hidden="true">…</span>')
            links.append(page_link(number, str(number)))
        body += f'<div class="research-pagination"><p class="caption">{L("research_page_range").format(start + 1, min(start + RESEARCH_PAGE_SIZE, len(reports)), len(reports))}</p><nav aria-label="{L("research_pagination")}">{previous}<div class="research-page-numbers">' + ''.join(links) + f'</div>{following}</nav></div>'
    return body + '</section>'


def research_landing(research, page=1):
    body = head('RESEARCH ARCHIVE', L('research_head'), L('research_sub')) + research_navigation(research)
    body += f'<p class="library-actions"><a class="report-import" data-import-report href="https://global.residualinertia.com/auth/login?next=/research/manage" hidden>{L("import_report")}</a></p>'
    body += '<p class="eyebrow">' + ('最新研究' if LANG == 'zh' else 'Latest Research') + '</p>' if page == 1 else ''
    body += research_library(research, page)
    if page == 1:
        items = []
        for key in ('weekly', 'monthly', 'personal', 'fomc', 'scholarly'):
            scholarly = key == 'scholarly'
            reports = [r for r in research if (bool(external_publications(r)) if scholarly else report_variant(r) == key)]
            latest = max(reports, key=lambda r: r.get('dataThrough') or r['published']) if reports else None
            route = 'research/personal/index.html#scholarly-research' if scholarly else 'research/' + key + '/index.html'
            label, desc = (L('scholarly_label'), L('scholarly_desc')) if scholarly else (L('col_' + key), L('col_' + key + '_desc'))
            latest_link = action_link('research/' + latest['slug'] + '.html', rfield(latest, 'title')) if latest else L('empty_text')
            byline = ('<br><span class="caption">' + L('author_label') + author_links(latest) + '</span>') if latest else ''
            items.append('<li><h3>' + action_link(route, label) + '</h3><p>' + E(desc) + '</p>' + latest_link + byline + '</li>')
        body += '<details class="archive-more" id="research-directions"><summary>' + L('hub_directions') + '</summary><ul class="action-list research-directions">' + ''.join(items) + '</ul></details>'
    return body


def research_folders(research):
    cards = []
    for i, (key, (tkey, lkey, dkey)) in enumerate(COLLECTIONS.items(), 1):
        count = sum(collection(r) == key for r in research)
        status = f'{count} {L("reports_count")}' if count else L('reports_pending')
        cards.append(anchor(f'research/{key}/index.html', f'<span class="folder-tab mono">0{i} / {L(lkey)}</span><h2>{L(tkey)}</h2><p>{L(dkey)}</p><div class="folder-foot"><span>{status}</span><span>{L("open_folder")}</span></div>', 'folder-card'))
    return '<div class="folder-grid">' + ''.join(cards) + '</div>'


def about(research=()):
    works = []
    for report in research:
        publications = external_publications(report)
        if publications and any(a['@id'].endswith('#taiyang-feng') for a in research_authors(report)):
            works.append('<li>' + action_link('research/' + report['slug'] + '.html', rfield(report, 'title')) + '<p class="caption">' + E(author_display(report)) + '</p></li>')
    works_markup = ('<h3>' + L('founder_works') + '</h3><ul class="action-list publication-list">' + ''.join(works) + '</ul>') if works else ''
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
<p>{L('founder_role')}</p><p class="caption">{L('founder_focus')}</p>{works_markup}
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
    selected = [('research/weekly/index.html', L('col_weekly')), ('research/fomc/index.html', L('col_fomc')),
                ('research/personal/index.html', L('col_personal')), ('research/personal/index.html#scholarly-research', L('scholarly_label')),
                ('overview.html', L('nav_overview')), ('global/index.html', L('nav_global'))]
    process = '<article class="prose"><h2 id="research-process">' + L('research_process') + '</h2><p>' + L('research_process_desc') + '</p>'
    process += '<h3>' + L('selected_work') + '</h3><ul class="action-list">' + ''.join('<li>' + action_link(route, label) + '</li>' for route, label in selected) + '</ul></article>'
    return head('ABOUT / RESIDUAL INERTIA', L('about_title'), L('about_lede')) + intro_text + principles() + founder_intro + process + f'''<article class="prose">
<h2 id="disclosure">{L('disclosure_title')}</h2><p>{L('disclosure_text')}</p></article>'''


def inline(text):
    return re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', E(text))


def related_reports(record, research):
    """Use actual period, manuscript references and academic keywords; never add generic link blocks."""
    related = []
    if report_variant(record) in ('weekly', 'monthly'):
        cutoff = record.get('dataThrough')
        previous = [r for r in research if r['slug'] != record['slug'] and report_variant(r) == report_variant(record)
                    and cutoff and r.get('dataThrough') and r['dataThrough'] < cutoff]
        if previous:
            related.append(max(previous, key=lambda r: r['dataThrough']))
        manuscript = record.get('articleBody') or record.get('markdown') or ''
        if 'FOMC' in manuscript:
            policies = [r for r in research if report_variant(r) == 'fomc' and cutoff and r.get('dataThrough', '') <= cutoff]
            if policies:
                related.append(max(policies, key=lambda r: r.get('dataThrough', '')))
    if external_publications(record):
        keywords = {k.casefold() for k in record.get('keywords', [])}
        related += [r for r in research if r['slug'] != record['slug'] and external_publications(r)
                    and keywords.intersection(k.casefold() for k in r.get('keywords', []))][:2]
    return list({r['slug']: r for r in related}.values())


def research_article(r, research=()):
    back_key = report_variant(r) if r['category'] in ('周报', '月报') else collection(r)
    body = action_link('research/' + back_key + '/index.html', '← ' + L('col_'+back_key), 'back')
    date_label = rfield(r, 'dateLabel') or L('report_date')
    dates = f'{date_label} {r["published"]}'
    if r.get('updated'):
        dates += f' · {L("revised_at")} {r["updated"]}'
    if r.get('dataThrough'):
        dates += f' · {L("data_through")} {r["dataThrough"]}'
    body += head(category_label(r['category']) + ' / RESEARCH', rfield(r, 'title'), dates)
    if r.get('subtitle'):
        body += '<p class="paper-subtitle">' + E(r['subtitle']) + '</p>'
    intro_label = ('本期判断' if LANG == 'zh' else 'Our view') if r.get('articleBody') else L('intro_heading')
    body += '<article class="prose"><section class="article-intro"><h2>' + intro_label + '</h2><p>' + E(rfield(r, 'summary')) + '</p>'
    body += '<p class="caption">' + L('author_label') + author_links(r) + '</p>'
    if r.get('researchId'):
        body += '<p class="caption">' + L('report_id_label') + '<span class="mono">' + E(r['researchId']) + ((' · v' + E(r['version'])) if r.get('version') else '') + '</span></p>'
    if r.get('pdf'):
        pdf = r['pdf']
        local = (ROOT / pdf).resolve()
        assert local.is_relative_to((ROOT/'assets/papers').resolve()) and local.is_file(), 'PDF must be a published asset'
        assert local.read_bytes().startswith(b'%PDF-'), 'Invalid PDF file'
        size = local.stat().st_size / 1024 / 1024
        digest = hashlib.sha256(local.read_bytes()).hexdigest()[:12]
        pdf_url = url(pdf) + '?v=' + digest
        body += f'<div class="paper-actions"><a class="cover-primary" href="{E(pdf_url)}">{action_content(L("view_pdf"))}</a><span class="caption">PDF · {size:.1f} MB</span></div>'
    publications = external_publications(r)
    if publications:
        body += '<p class="caption">' + L('paper_external') + '</p>'
        if r.get('manuscriptStatus'):
            body += '<p class="caption">' + L('paper_local_version') + '：' + L(r['manuscriptStatus']) + '</p>'
        for publication in publications:
            label = L('view_ssrn') if publication['kind'] == 'SSRN' else L('view_doi')
            body += '<div class="paper-actions">' + action_link(publication['url'], label, external=True) + '</div>'
    body += '</section>'
    if rfield(r, 'note'):
        body += '<div class="notice">' + E(rfield(r, 'note')) + '</div>'
    manuscript = (rfield(r, 'articleBody') if r.get('articleBody') else rfield(r, 'markdown')) or ''
    notes = ''
    if LANG == 'zh' and '\n## 数据口径\n' in manuscript:
        manuscript, notes = manuscript.split('\n## 数据口径\n',1)
        notes = '## 数据口径\n'+notes
    elif LANG == 'zh' and '\n## 方法与数据\n' in manuscript and r.get('articleBody'):
        manuscript, notes = manuscript.split('\n## 方法与数据\n',1)
        notes = '## 方法与数据\n'+notes
    body += markdown(manuscript)
    if notes:
        body += '<details class="report-notes"><summary>数据说明与参考来源</summary>' + markdown(notes) + '</details>'
    source = rfield(r, 'sourceNote') or ( '来源：Residual Inertia 研究门户的历史报告。' if LANG == 'zh' else 'Source: historical reports from the Residual Inertia research portal.')
    body += '<h2>' + L('sources_heading') + '</h2><p>' + E(source) + '</p><p>' + L('not_advice') + '</p></article>'
    related = related_reports(r, research)
    if related or report_variant(r) in ('weekly', 'monthly'):
        links = []
        if report_variant(r) in ('weekly', 'monthly'):
            links.append('<li>' + action_link('overview.html', L('nav_overview')) + '</li>')
        links += ['<li>' + action_link('research/' + report['slug'] + '.html', rfield(report, 'title')) + '</li>' for report in related]
        body += '<section class="prose"><h2>' + L('related_research') + '</h2><ul class="action-list">' + ''.join(links) + '</ul></section>'
    return body


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


def snapshot_page(s, previous, following, research=()):
    m = s['market']
    body = action_link('overview.html#daily-snapshots', L('back_overview'), 'back') + head('DAILY SNAPSHOT', s['observationDate'] + ' · ' + L('snapshot_suffix'), L('snapshot_lede'))
    body += f'<div class="notice"><strong>{L("archived_at")} {E(s["capturedAt"])}</strong><span>{L("archive_note")}</span></div>' + metrics(s)
    alerts = ''.join(f'<p><strong>{E(a["title"])}</strong> · {E(a["detail"])}</p>' for a in s['alerts'])
    body += f'<div class="two-col">{pillars(s)}<section class="panel"><p class="eyebrow">{L("summary_eyebrow")}</p><h2>{E(state_label(m["regimeState"]))} · {L("score_label")} {number(m["regimeScore"])}</h2><p>{E(s["brief"]["posture"])}</p>{alerts}<p class="caption">{L("summary_caption")}</p></section></div>'
    rows = ''.join(f'<tr><td>{E(source_label(src["name"]))}</td><td>{shortdate(src["asOf"])}</td><td>{E(status_label(src["status"]))}</td><td>{E(quality_label(src["qualityStatus"]))}</td></tr>' for src in s['sources'])
    body += '<section class="section"><h2>' + L('sources_title') + '</h2><p class="caption">' + L('sources_caption') + '</p><div class="table-scroll" tabindex="0" role="region" aria-label="data sources"><table><thead><tr><th>' + L('th_source') + '</th><th>' + L('th_asof') + '</th><th>' + L('th_freshness') + '</th><th>' + L('th_quality') + '</th></tr></thead><tbody>' + rows + '</tbody></table></div></section>'
    body += f'<details class="provenance"><summary>{L("provenance_summary")}</summary><p>{L("src_label")}<code>{E(s["snapshotId"])}</code></p><p>{L("hash_label")}<code>{E(s["contentHash"])}</code></p></details>'
    matching = [r for r in research if r.get('dataThrough') == m['regimeDate'][:10] and report_variant(r) in ('weekly', 'monthly')]
    if matching:
        body += '<section class="section"><h2>' + L('related_research') + '</h2><ul class="action-list">' + ''.join('<li>' + action_link('research/' + r['slug'] + '.html', rfield(r, 'title')) + '</li>' for r in matching) + '</ul></section>'
    body += '<div class="pager">' + (action_link('snapshots/' + previous['observationDate'] + '.html', '← ' + previous['observationDate']) if previous else '<span></span>') + (action_link('snapshots/' + following['observationDate'] + '.html', following['observationDate'] + ' →') if following else '<span>' + L('pager_latest') + '</span>') + '</div>'
    return body


def current_market_page(s):
    body = action_link('overview.html', L('back_overview'), 'back') + head('LATEST MARKET READING', L('current_title'), L('current_lede'))
    body += overview_reading(s) + metrics(s) + pillars(s)
    body += '<p class="caption">' + L('summary_caption') + '</p>'
    body += action_link('overview.html#daily-snapshots', L('ov_archive_title'))
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
        intro += '<div class="overview-current">' + overview_reading(latest)
        intro += f'<section class="overview-pillars"><p class="eyebrow">{L("ov_pillars_eyebrow")}</p><h2>{L("pillars_title")}</h2>{overview_pillars(latest)}<p class="caption">{L("pillars_caption")}</p></section></div>'
        intro += score_legend()
        intro += '<div class="action-group">' + action_link('about.html#research-process', L('research_process')) + action_link('global/index.html', L('nav_global')) + '</div>'
        intro += f'<section class="overview-trend"><div class="editorial-heading"><div><p class="eyebrow">{L("ov_trend_eyebrow")}</p><h2>{L("ov_trend_title")}</h2></div><span class="mono">{L("chart_rolling")}</span></div>{history_chart(snapshots, embedded=True)}</section>'
        intro += f'<section class="overview-archive" id="daily-snapshots"><p class="eyebrow">{L("ov_archive_eyebrow")}</p><h2>{L("ov_archive_title")}</h2><p class="section-intro">{L("ov_archive_intro").format(len(snapshots))}</p>{overview_snapshot_list(snapshots)}</section>'
        market_reports = [r for r in research if collection(r) == 'market'][:2]
        if market_reports:
            intro += f'<section class="overview-research"><p class="eyebrow">{L("ov_research_eyebrow")}</p><h2>{L("ov_research_title")}</h2>{research_cards(market_reports)}</section>'
        return intro

    write('index.html', L('home_title'), lambda: homepage(latest, research), 'home', L('home_desc'))
    write('overview.html', L('overview_title'), overview, 'overview', archive_snapshots=snapshots)
    if latest.get('kind') == 'current':
        write('market/latest.html', L('current_title'), lambda: current_market_page(latest), 'overview')
    write('global/index.html', L('global_title'), global_pulse, 'global', L('global_intro'))
    redirect('snapshots/index.html', url('overview.html#daily-snapshots'), L('snapshots_redirect'))
    for i, s in enumerate(snapshots):
        # Archive commentary has no English translation yet; do not claim a translated pair.
        write('snapshots/' + s['observationDate'] + '.html', s['observationDate'] + ' ' + L('snapshot_suffix'), lambda s=s, i=i: snapshot_page(s, snapshots[i-1] if i else None, snapshots[i+1] if i+1 < len(snapshots) else None, research), 'overview', description=s['brief']['posture'], translated=False, indexable=should_index_snapshot(s, snapshots[:i]), snapshot=s)
    for page in range(1, research_page_count(research) + 1):
        write(research_page_route('research', page), L('research_title'), lambda page=page: research_landing(research, page), 'research', L('research_desc'), archive_research=research[(page-1)*RESEARCH_PAGE_SIZE:page*RESEARCH_PAGE_SIZE])
    for key, (tkey, lkey, dkey) in COLLECTIONS.items():
        def folder(page, key=key, lkey=lkey, dkey=dkey):
            reports = [r for r in research if collection(r) == key]
            empty = '<div class="empty-research"><h2>' + L('empty_title') + '</h2><p>' + (L('formal_reports_pending') if key == 'market' else L('empty_text')) + '</p></div>'
            scholarly = ('<div id="scholarly-research"><h2>' + L('scholarly_label') + '</h2><p class="caption">' + L('scholarly_desc') + '</p></div>') if key == 'personal' else ''
            return action_link('research/index.html', L('back_research'), 'back') + head(L(lkey), L(tkey), L(dkey)) + research_navigation(research, key) + (f'<p class="library-actions"><a class="report-import" data-import-report href="https://global.residualinertia.com/auth/login?next=/research/manage" hidden>{L("import_report")}</a></p>' if key == 'market' else '') + scholarly + research_library(reports, page, f'research/{key}', empty)
        reports = [r for r in research if collection(r) == key]
        for page in range(1, research_page_count(reports) + 1):
            write(research_page_route(f'research/{key}', page), L(tkey), lambda page=page: folder(page), 'research', L(dkey), archive_research=reports[(page-1)*RESEARCH_PAGE_SIZE:page*RESEARCH_PAGE_SIZE])
    for kind, label in [('weekly','WEEKLY LETTERS'),('monthly','MONTHLY LETTERS')]:
        def period_folder(page, kind=kind, label=label):
            reports = [r for r in research if report_variant(r) == kind]
            empty = '<div class="empty-research"><h2>' + L('empty_title') + '</h2><p>' + L('empty_text') + '</p></div>'
            return action_link('research/index.html', L('back_research'), 'back') + head(label, L('col_'+kind), L('col_'+kind+'_desc')) + research_navigation(research, kind) + '<p class="library-actions"><a class="report-import" data-import-report href="https://global.residualinertia.com/auth/login?next=/research/manage" hidden>' + L('import_report') + '</a></p>' + research_library(reports, page, f'research/{kind}', empty)
        reports = [r for r in research if report_variant(r) == kind]
        for page in range(1, research_page_count(reports) + 1):
            write(research_page_route(f'research/{kind}', page), L('col_'+kind), lambda page=page: period_folder(page), 'research', L('col_'+kind+'_desc'), indexable=kind != 'monthly' or bool(reports), archive_research=reports[(page-1)*RESEARCH_PAGE_SIZE:page*RESEARCH_PAGE_SIZE])
    for r in research:
        translated = bool(r.get('summary_en') and (r.get('articleBody_en') or r.get('markdown_en')))
        write('research/' + r['slug'] + '.html', rfield(r, 'title'), lambda r=r: research_article(r, research), 'research', rfield(r, 'summary'), translated=translated, record=r)
    write('about.html', L('about_title'), lambda: about(research), 'about', L('home_desc'))
    write('404.html', L('404_title'), lambda: head('404', L('404_title'), L('404_lede')) + action_link('index.html', L('back_home')), indexable=False)


def main():
    global LANG
    ALL_PAGES.clear()
    PAGE_SEO.clear()
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
    latest = latest_reading(snapshots)

    for lang in ('zh', 'en'):
        LANG = lang
        build_language(snapshots, research, latest)
    add_language_alternates()

    (OUT/'.nojekyll').write_text('', encoding='utf-8')
    (OUT/'CNAME').write_text(CONFIG['domain'] + '\n', encoding='utf-8')
    origin = 'https://' + CONFIG['domain']
    (OUT/'assets/brand/entity.json').write_text(json.dumps({'version': 1, 'organization': organization_node()}, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    (OUT/'robots.txt').write_text('User-agent: *\nAllow: /\nSitemap: ' + origin + '/sitemap.xml\n', encoding='utf-8')
    write_sitemap()
    print(f'Built {len(ALL_PAGES)} HTML pages ({len(ALL_PAGES)//2} per language) from {len(snapshots)} snapshots and {len(research)} research reports.')


if __name__ == '__main__':
    main()
