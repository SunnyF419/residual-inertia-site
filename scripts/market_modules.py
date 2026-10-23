"""Bilingual public dashboard views. All values come from the reviewed export."""
from html import escape
from datetime import date


def model_note(m, lang):
    if not m.get('estimateInput'):
        return ''
    zh = lang == 'zh'
    title = '估算输入版 · 部分数据待更新' if zh else 'Estimate-input model · source update pending'
    if m.get('publicationStatus') != 'PENDING_SOURCE':
        title = '估算输入版' if zh else 'Estimate-input model'
    body = ('综合状态与历史曲线采用同一新版模型，不与旧版分数直接作环比。各模块独立标注日期；估算输入不是官方 French 序列。' if zh else
            'The latest reading and history use the same revised model. Scores are not directly comparable with older model versions. Each module has its own cutoff; estimated inputs are not official French series.')
    return f'<aside class="market-method"><strong>{title}</strong><p>{body}</p></aside>'


def render_modules(m, lang, compact=False):
    data = m.get('modules')
    if not data:
        return ''
    zh = lang == 'zh'
    tr = lambda cn,en: cn if zh else en
    e = lambda x: escape(str(x if x is not None else '—'))
    fmt = lambda x,n=1: f'{x:.{n}f}' if isinstance(x,(int,float)) else '—'
    pct = lambda x: fmt(x*100 if isinstance(x,(int,float)) else None)+'%'
    day = lambda x: e(str(x)[:10]) if x else '—'
    def table(headers, rows):
        return '<div class="table-scroll" tabindex="0" role="region" aria-label="'+tr('模块数据','Module data')+'"><table><thead><tr>'+''.join('<th>'+e(h)+'</th>' for h in headers)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+e(c)+'</td>' for c in row)+'</tr>' for row in rows)+'</tbody></table></div>'
    cards = []
    def card(key,title,value,status,asof,note,detail=''):
        extra = '<details><summary>'+tr('展开数据','View data')+'</summary>'+detail+'</details>' if detail else ''
        cards.append(f'<article class="market-module" id="module-{key}"><h3>{e(title)}</h3><strong class="module-number">{e(value)}</strong><p class="module-state">{e(status)}</p><p class="module-date">{tr("数据截至","Data through")} <time>{day(asof)}</time></p><p>{e(note)}</p>{extra}</article>')
    nfci = data['nfci']
    card('nfci','NFCI − ANFCI',fmt(nfci['nfci_minus_anfci'],3),tr('周频观察','Weekly observation'),nfci['date'],tr('差值与综合状态中的金融压力分数是不同指标。','The spread is distinct from the Financial Stress pillar score.'),table(['NFCI','ANFCI'],[[fmt(nfci['nfci'],3),fmt(nfci['anfci'],3)]]))
    s2 = data['livermore']
    card('livermore','Livermore S2',fmt(s2.get('S2_score')),tr('正常','Normal') if s2.get('S2_state')=='Normal' else s2.get('S2_state','—'),s2.get('date'),tr('观察突破失败与上涨效率。','Monitors breakout failures and upside efficiency.'),table(['S2A','S2B'],[[fmt(s2.get('S2A_score')),fmt(s2.get('S2B_score'))]]))
    ai = data['ai']; composite = next(p for p in ai['pillars'] if p['pillar_id']=='composite')
    ai_names = {'composite':tr('综合状态','Composite'),'demand_momentum':tr('需求动量','Demand momentum'),'leadership_breadth':tr('领导力宽度','Leadership breadth'),'relative_risk_appetite':tr('相对风险偏好','Relative risk appetite'),'supply_chain_confirmation':tr('供应链确认','Supply-chain confirmation'),'crowding_heat':tr('拥挤与热度','Crowding / heat'),'divergence_fragility':tr('分化脆弱性','Divergence fragility')}
    detail = table([tr('支柱','Pillar'),tr('分数','Score'),tr('方向','Direction')],[[ai_names[p['pillar_id']],fmt(p['score']),tr('越高越强','Higher = stronger') if p['direction']=='constructive' else tr('越高风险越大','Higher = riskier')] for p in ai['pillars']])
    detail += table(['ETF','1D','5D','20D'],[[p['symbol'],pct(p['ret_1d']),pct(p['ret_5d']),pct(p['ret_20d'])] for p in ai['etfs']])
    detail += table([tr('产业链','Industry group'),'20D'],[[p['group'].rsplit(' / ',1)[-1 if zh else 0],pct(p['avg_ret_20d'])] for p in ai['groups']])
    card('ai',tr('半导体 / AI 硬件','Semiconductor / AI hardware'),fmt(composite['score'])+' / 100',composite['state_zh' if zh else 'state'],composite['date'],tr('综合分数越高越强；拥挤与分化子指标越高，风险越大。','Higher composite scores indicate strength; higher crowding and divergence scores indicate risk.'),detail)
    crowd = data['crowding']; ls = crowd['long_short_no_market']; lo = crowd['long_only_beta_adjusted']
    card('crowding',tr('因子拥挤度','Factor crowding'),f"LS {ls['level']} · LOβ {lo['level']}",tr('月频 · 保留最近一期','Monthly · latest available period'),ls['date'],tr('尚无更新月份；不将月频旧值标作日频新值。','The latest available month is retained; these are not daily readings.'),table([tr('口径','Variant'),tr('分数','Score')],[[k,fmt(v['crowding_score'],3)] for k,v in crowd.items()]))
    if not compact:
        weekly = data['weekly']
        card('weekly',tr('美股周频风险','US weekly risk'),weekly['risk_level']+' / '+pct(weekly['target_exposure']),tr('模型参考风险敞口','Model reference exposure'),weekly['signal_date'],tr('生效日期：','Effective date: ')+str(weekly['effective_date'])[:10]+tr('。不代表实际持仓。','. Does not represent actual holdings.'))
        breadth = data['breadth']
        card('breadth',tr('市场宽度','Market breadth'),pct(m['breadth']),tr('200 日均线上方 · 日频估计','Above 200DMA · daily nowcast'),m['breadthDate'],tr('月末正式口径与日频估计分开记录。','Month-end observations are separate from daily nowcasts.'),table([tr('月末指标','Month-end metric'),tr('数值','Value'),tr('日期','Date')],[[tr('200 日均线上方','Above 200DMA'),pct(breadth['above_200dma_ratio']['breadth_value']),day(breadth['above_200dma_ratio']['date'])],[tr('12 月跑赢基准','12M outperforming benchmark'),pct(breadth['outperform_sp500_12m_ratio']['breadth_value']),day(breadth['outperform_sp500_12m_ratio']['date'])]]))
        wqs = data['wqs']
        card('wqs',tr('WQS 动量脆弱性','WQS momentum fragility'),fmt(wqs.get('wqs'),4),tr('中性','Neutral') if wqs.get('signal')=='neutral' else wqs.get('signal','—'),wqs.get('date'),tr('生效日期：','Effective date: ')+str(wqs.get('effective_date','—'))[:10]+tr('。仅展示已生效值；未采用未来月份标签。','. Only effective observations are shown; future month labels are excluded.'))
        for key in ['hml','umd']:
            factor = data['factors'][key]
            pending = key=='hml' and data.get('hmlPending',{}).get('publication_allowed') is False
            note = tr('估算价值价差；非官方 French 数据。','Estimated value spread; not official French data.')
            if pending:
                note += tr(' 下一日期仍待数据，保留最近有效值。',' The next observation is pending; the last valid value is retained.')
            allowed = factor.get('publication_allowed') is True
            value = fmt(factor['metric_value'],3) if allowed else '—'
            status = tr('估算 · 等待下一期','Estimate · next observation pending') if pending else tr('估算','Estimate')
            if not allowed: status = tr('暂不可发布','Not publishable')
            detail = table([tr('历史百分位','Historical percentile')],[[fmt(factor['percentile_all_history'])+'%']]) if allowed else ''
            if key=='hml' and allowed:
                detail += table([tr('公司覆盖率','Company coverage'),tr('形成期市值覆盖率','Formation ME coverage')],[[pct(factor['company_coverage']),pct(factor['formation_me_reference_coverage'])]])
            card(key,key.upper()+tr(' 价值价差',' value spread'),value,status,factor['date'],note,detail)
        liq = data.get('liquidity',{})
        dates = [r['week_end'] for rows in liq.values() for r in rows]
        rows=[]; fresh=0
        for key,values in liq.items():
            for r in values:
                age=(date.fromisoformat(m['breadthDate'][:10])-date.fromisoformat(r['week_end'][:10])).days
                valid=r.get('quality_flag')=='OK' and 0 <= age <= 14
                fresh += int(valid)
                metric={'options':'atm_iv_30d','otc':'total_notional','defi':'tvl_usd'}[key]
                rows.append([key.upper()+' '+str(r.get('asset_class','')),day(r['week_end']),r.get('quality_flag','—'),fmt(r.get(metric),3) if valid else '—'])
        card('liquidity',tr('新时代流动性','New liquidity monitor'),str(fresh) if fresh else '—',tr('有效分项','Validated series') if fresh else tr('历史数据 · 未达到当前发布要求','Historical data · not current'),max(dates) if dates else None,tr('仅展示来源质量为 OK 且距市场数据日不超过 14 天的数值；缺失及质量异常不解释为市场信号。期权数值为 30 日 IV，OTC 为名义金额，DeFi 为 TVL（美元）。独立模块，不纳入周频风险分数。','Values require OK source quality and a cutoff within 14 days of the market data date. Missing or low-quality readings are not market signals. Options: 30D IV; OTC: notional; DeFi: TVL in USD. Excluded from weekly risk.'),table([tr('模块','Module'),tr('日期','Date'),tr('来源质量','Source quality'),tr('数值','Value')],rows))
    intro = tr('各模块按自己的更新频率和数据日期展示。综合分数更新不代表所有来源同时更新。','Each module retains its own frequency and cutoff. A composite update does not imply that every source updated together.')
    return '<section class="market-modules"><p class="eyebrow">RESEARCH MONITOR</p><h2>'+tr('市场研究模块','Market research modules')+'</h2><p class="section-intro">'+intro+'</p><div class="market-module-grid">'+''.join(cards)+'</div></section>'
