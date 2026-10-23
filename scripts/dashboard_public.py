"""Read-only, allowlisted export of the dashboard's current public research modules."""
import json
import math
from datetime import date, datetime, timezone
from pathlib import Path

ESTIMATE_VERSION = 'HML_DUAL99_ESTIMATE_REGIME_V1'


def history_table(version):
    if version == ESTIMATE_VERSION:
        return 'market_regime_estimate_history'
    if version in (None, ''):
        return 'market_regime_history'
    raise ValueError('Unknown Regime model version; publication requires review')


def dashboard_paths(portal):
    import yaml
    config = json.loads((portal/'portal.config.json').read_text(encoding='utf-8-sig'))
    signals = Path(config['sources']['marketResearch'])
    if not signals.is_absolute():
        signals = portal/signals
    signals = signals.resolve()
    project = signals.parent.parent
    # Match src.config_loader, not the unrelated legacy factor configuration.
    current = project/'config/paths.yaml'
    if current.is_file():
        settings = yaml.safe_load(current.read_text(encoding='utf-8-sig'))
        database = Path(settings['duckdb_path'])
    else:
        settings = yaml.safe_load((project/'config.yaml').read_text(encoding='utf-8-sig'))
        database = Path(settings['paths']['duckdb_path'])
    if not database.is_absolute():
        database = project/database
    if not database.is_file():
        raise FileNotFoundError('Configured dashboard database is unavailable')
    return project, signals, database.resolve()


def fields(row, names):
    result = {}
    for key in names.split():
        value = row.get(key)
        if isinstance(value, (date, datetime)):
            value = value.isoformat()[:10]
        if isinstance(value, float) and not math.isfinite(value):
            raise ValueError('Non-finite public dashboard value: ' + key)
        result[key] = value
    return result


def dashboard_snapshot(portal):
    """Read the completed export directly; unrelated portal modules need not refresh."""
    _, signals, _ = dashboard_paths(portal)
    raw = json.loads(signals.read_text(encoding='utf-8-sig'))
    regime = raw['market_regime']; latest = regime['latest']
    risk = raw['weekly_risk_model']
    breadth = raw['market_breadth']['daily_nowcast']['above_200dma_ratio']
    market = dict(riskLevel=risk['risk_level'], riskScore=risk['overall_score'], targetExposure=risk['target_exposure'],
                  signalDate=risk['signal_date'], effectiveDate=risk['effective_date'],
                  regimeState=latest['regime_state_zh'], regimeScore=latest['regime_score'], regimeDate=latest['date'],
                  breadth=breadth['breadth_value'], breadthDate=breadth['asof_trade_date'],
                  pillars=[dict(name=p['pillar'], state=p['pillar_state_zh'], score=p['pillar_score']) for p in regime['pillars']])
    asof = max(market[k][:10] for k in ('signalDate','regimeDate','breadthDate'))
    return dict(generatedAt=datetime.fromtimestamp(signals.stat().st_mtime, timezone.utc).isoformat(), market=market,
                sources=[dict(id='marketResearch', asOf=asof, status='partial' if regime['publication_status']=='PENDING_SOURCE' else 'current', quality=dict(status='warning' if regime['publication_status']=='PENDING_SOURCE' else 'pass'))])


def effective_row(con, table, columns, cutoff, effective=False):
    # Identifiers are internal constants, never supplied by the source data.
    condition = 'AND effective_date <= ?' if effective else ''
    args = [cutoff, cutoff] if effective else [cutoff]
    cursor = con.execute(f'SELECT {columns} FROM {table} WHERE date <= ? {condition} ORDER BY date DESC LIMIT 1', args)
    row = cursor.fetchone()
    return fields(dict(zip([c[0] for c in cursor.description], row)), columns.replace(',', ' ')) if row else {}


def enrich_reading(portal, candidate):
    import duckdb
    project, signals, database = dashboard_paths(portal)
    raw = json.loads(signals.read_text(encoding='utf-8-sig'))
    regime = raw['market_regime']
    latest = regime['latest']
    version = latest.get('model_version', regime.get('model_version'))
    history_table(version)
    market = candidate['market']
    if latest['date'][:10] != market['regimeDate'][:10] or not math.isclose(latest['regime_score'], market['regimeScore'], abs_tol=0.001):
        raise ValueError('Portal summary and dashboard export disagree; refresh the summary')
    if version != ESTIMATE_VERSION or not regime.get('estimate_input'):
        raise ValueError('Current dashboard publication version requires review')
    expected = {p['pillar']: p['pillar_score'] for p in regime['pillars']}
    if any(p['name'] not in expected or not math.isclose(p['score'], expected[p['name']], abs_tol=0.001) for p in market['pillars']):
        raise ValueError('Portal and dashboard pillars disagree')
    risk = raw['weekly_risk_model']
    breadth = raw['market_breadth']['daily_nowcast']['above_200dma_ratio']
    if risk['signal_date'][:10] != market['signalDate'][:10] or not risk.get('signal_usable') or not math.isclose(risk['target_exposure'], market['targetExposure']):
        raise ValueError('Weekly signal is unavailable or differs from portal')
    if breadth['asof_trade_date'][:10] != market['breadthDate'][:10] or not math.isclose(breadth['breadth_value'], market['breadth']):
        raise ValueError('Breadth export differs from portal')
    cutoff = candidate['observationDate']
    market.update(modelVersion=version, estimateInput=True, publicationStatus=regime['publication_status'])
    market['inputDates'] = [fields(p, 'component_id component_name data_date effective_date') for p in regime['components_used']]
    modules = dict(
        weekly=fields(risk, 'signal_date effective_date risk_level overall_score target_exposure signal_status'),
        breadth={k: fields(raw['market_breadth'][k], 'date breadth_value numerator denominator') for k in ('above_200dma_ratio', 'outperform_sp500_12m_ratio')},
        nfci=fields(raw['nfci_anfci'], 'date nfci anfci nfci_minus_anfci nfci_4w_change anfci_4w_change'),
        crowding={k: fields(v, 'date crowding_score level signal_valid_from') for k,v in raw['factor_crowding'].items()},
        factors={k: fields(v, 'date metric_value percentile_all_history publication_allowed status company_coverage formation_me_reference_coverage minimum_company_coverage minimum_formation_me_reference_coverage') for k,v in raw['bubble_factor_layer'].items()},
        hmlPending=fields(raw.get('hml_daily_estimate', {}), 'date publication_allowed status'),
        ai={
            'pillars': [fields(p, 'date pillar_id pillar score raw_score state state_zh direction above_20dma_ratio above_50dma_ratio') for p in raw['semiconductor_ai_hardware']['pillars']],
            'etfs': [fields(p, 'date symbol ret_1d ret_5d ret_20d ret_20d_vs_spy') for p in raw['semiconductor_ai_hardware']['etfs']],
            'groups': [fields(p, 'date group members avg_ret_20d above_20dma_ratio') for p in raw['semiconductor_ai_hardware']['groups']],
        },
    )
    with duckdb.connect(str(database), read_only=True) as con:
        modules['livermore'] = effective_row(con, 'livermore_s2_signals', 'date, S2_score, S2A_score, S2B_score, S2_state', cutoff)
        modules['wqs'] = effective_row(con, 'wqs_signals', 'date, effective_date, wqs, qs, mom_12_1, signal', cutoff, effective=True)
    # The raw WQS export can carry a next-month label; do not present it as active.
    modules['wqsPending'] = bool(raw['wqs_momentum_fragility']['effective_date'][:10] > cutoff)
    modules['liquidity'] = liquidity(project, cutoff)
    market['modules'] = modules
    return candidate


def liquidity(project, cutoff):
    import duckdb
    import yaml
    cfg = yaml.safe_load((project/'config/new_liquidity_sources.yaml').read_text(encoding='utf-8-sig'))
    database = Path(cfg['database']['path'])
    if not database.is_absolute():
        database = project/database
    result = {}
    if not database.exists():
        return result
    specs = [
        ('options', 'options_surface_weekly_metrics', 'week_end underlying atm_iv_30d put_call_volume_ratio quality_flag', "AND underlying = 'SPY'"),
        ('otc', 'otc_derivatives_weekly_metrics', 'week_end asset_class total_notional trade_count quality_flag', ''),
        ('defi', 'defi_liquidity_weekly_metrics', 'week_end tvl_usd stablecoin_pool_depth_usd quality_flag', ''),
    ]
    with duckdb.connect(str(database), read_only=True) as con:
        tables = {r[0] for r in con.execute('SHOW TABLES').fetchall()}
        for key, table, names, condition in specs:
            if table not in tables:
                continue
            cursor = con.execute(f'SELECT * FROM {table} WHERE week_end <= ? {condition} ORDER BY week_end DESC', [cutoff])
            rows = cursor.fetchall()
            if rows:
                # Retain each OTC asset class at the latest date, not one arbitrary row.
                columns = [c[0] for c in cursor.description]
                index = columns.index('week_end')
                result[key] = [fields(dict(zip(columns, row)), names) for row in rows if row[index] == rows[0][index]]
    return result
