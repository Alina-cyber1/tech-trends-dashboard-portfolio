"""
data_loader.py - загрузка данных для дашборда
Реальные метрики из полных данных, AI Share из G06N* классификации
"""

import streamlit as st
import pandas as pd
import numpy as np
import os
import json
import requests
from pathlib import Path
from datetime import datetime, timedelta
import logging
from collections import Counter
import ast

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ========== КОНФИГУРАЦИЯ ==========
PROJECT_ROOT = Path(__file__).parent
DATA_PROCESSED = PROJECT_ROOT / "data" / "processed"
DATA_PROCESSED.mkdir(parents=True, exist_ok=True)

# ========== СЕРВЕРНЫЕ ПУТИ ==========
SERVER_OPENALEX_PATH = Path('/home/ubuntu/OpenAlex')
SERVER_PATENTS_SEMICONDUCTORS_PATH = Path('/home/ubuntu/patents/semiconductors')
SERVER_PATENTS_GE_PATH = Path('/home/ubuntu/patents/ge')
TREND_SCORE_PATH = Path('/home/ubuntu/indlab-techtrends-ds/src/data/processed/trend_score_ge.csv')
AI_SHARE_JSON = Path('/home/ubuntu/dashboard/ai_share.json')
SPEED_SCORE_PATH = Path('/home/ubuntu/indlab-techtrends-ds/src/data/processed/speed_score_ge.csv')
TIME_LAG_PATH = Path('/home/ubuntu/time_lag_family.csv')
TIME_LAG_GE_PATH = Path('/home/ubuntu/time_lag_ge_family.csv')

DOMAIN_MAP = {
    "Полупроводники": "semiconductors",
    "Генная инженерия": "gene_engineering"
}

COUNTRY_NAMES = {
    'US': 'США', 'CN': 'Китай', 'JP': 'Япония', 'KR': 'Южная Корея',
    'EP': 'Европа', 'WO': 'Мир', 'DE': 'Германия', 'FR': 'Франция',
    'GB': 'Великобритания', 'CA': 'Канада'
}

CPC_CODES = {
    'semiconductors': ['H01L', 'H10', 'G03F', 'C23C', 'H05K'],
    'gene_engineering': ['C12N15/00', 'A61K48/00', 'C12N9/22']
}

TOPIC_IDS = {
    'semiconductors': ['Semiconductor devices', 'Lithography', 'Thin films'],
    'gene_engineering': ['CRISPR/Cas', 'Gene therapy', 'Vectors']
}

AI_CPC_PREFIX = 'G06N'
SAMPLE_SIZE = 50000


# ========== ЗАГРУЗКА AI SHARE ИЗ JSON ==========
def load_ai_share_from_json(domain_key):
    try:
        if AI_SHARE_JSON.exists():
            with open(AI_SHARE_JSON, 'r') as f:
                data = json.load(f)
            ai_share = data.get(domain_key, 15)
            logger.info(f"AI Share из JSON: {domain_key} = {ai_share}%")
            return ai_share
        return 15
    except Exception as e:
        logger.error(f"Ошибка загрузки AI Share: {e}")
        return 15


# ========== ЗАГРУЗКА SPEED SCORE ИЗ CSV ==========
def load_speed_score_from_file(domain_key):
    topic_mapping = {
        'semiconductors': 'Semiconductor materials and devices',
        'gene_engineering': 'CRISPR and Genetic Engineering'
    }
    
    topic_name = topic_mapping.get(domain_key)
    if not topic_name or not SPEED_SCORE_PATH.exists():
        return {'speed_score': 0, 'speed_status': 'Нет данных', 'acceleration_rate': 0, 'time_to_market': 0}
    
    try:
        df = pd.read_csv(SPEED_SCORE_PATH)
        df_topic = df[df['topic_name'] == topic_name].copy()
        if len(df_topic) == 0:
            return {'speed_score': 0, 'speed_status': 'Нет данных', 'acceleration_rate': 0, 'time_to_market': 0}
        
        df_topic['month'] = pd.to_datetime(df_topic['month'])
        df_topic = df_topic.sort_values('month')
        latest = df_topic.iloc[-1]
        speed_score = int(latest.get('speed_score', 0) * 100)
        
        if len(df_topic) >= 12:
            recent_avg = df_topic['speed_score'].iloc[-6:].mean()
            older_avg = df_topic['speed_score'].iloc[-12:-6].mean()
            acceleration = (recent_avg - older_avg) * 100
        else:
            acceleration = 0
        
        if speed_score >= 80:
            status = "Very Fast"
        elif speed_score >= 60:
            status = "Fast"
        elif speed_score >= 40:
            status = "Moderate"
        elif speed_score >= 20:
            status = "Slow"
        else:
            status = "Very Slow"
        
        return {
            'speed_score': speed_score,
            'speed_status': status,
            'acceleration_rate': round(acceleration, 1),
            'time_to_market': 0
        }
    except Exception as e:
        logger.error(f"Ошибка Speed Score: {e}")
        return {'speed_score': 0, 'speed_status': 'Нет данных', 'acceleration_rate': 0, 'time_to_market': 0}


# ========== ЗАГРУЗКА TREND SCORE ==========
def load_trend_score_data(domain_key):
    """Загрузка Trend Score из CSV файла"""
    try:
        if TREND_SCORE_PATH.exists():
            df = pd.read_csv(TREND_SCORE_PATH)
            
            # Маппинг доменов на названия топиков в CSV
            topic_mapping = {
                'semiconductors': 'Semiconductor materials and devices',
                'gene_engineering': 'CRISPR and Genetic Engineering'
            }
            topic_name = topic_mapping.get(domain_key)
            
            if topic_name and 'topic_name' in df.columns:
                df_topic = df[df['topic_name'] == topic_name].copy()
                if len(df_topic) > 0:
                    # Сортируем по дате и берем последнюю запись
                    df_topic['month'] = pd.to_datetime(df_topic['month'])
                    df_topic = df_topic.sort_values('month')
                    latest = df_topic.iloc[-1]
                    
                    trend_score_raw = latest.get('trend_score', 0)
                    trend_label = latest.get('trend_label', 'Стабильный')
                    
                    status_map = {'Стабильный': 'Stable', 'Снижающийся': 'Cooling', 
                                 'Растущий': 'Growing', 'Зарождающийся': 'Emerging'}
                    
                    logger.info(f"Trend Score из CSV: {trend_score_raw}, метка: {trend_label}")
                    return {
                        'trend_score': int(trend_score_raw * 100),
                        'trend_status': status_map.get(trend_label, 'Stable')
                    }
    except Exception as e:
        logger.warning(f"Ошибка загрузки Trend Score из CSV: {e}")
    
    return {'trend_score': 65, 'trend_status': 'Growing'}


# ========== ЗАГРУЗКА ПУБЛИКАЦИЙ ==========
def load_publications(domain_key):
    file_path = SERVER_OPENALEX_PATH / f"{domain_key}_clean_signal.parquet"
    if not file_path.exists():
        return pd.DataFrame()
    
    try:
        df_full = pd.read_parquet(file_path, engine='pyarrow')
        total_count = len(df_full)
        if len(df_full) > SAMPLE_SIZE:
            df = df_full.sample(SAMPLE_SIZE, random_state=42)
        else:
            df = df_full
        
        if 'publication_date' in df.columns:
            df['date'] = pd.to_datetime(df['publication_date'], errors='coerce')
            df['year_month'] = df['date'].dt.strftime('%Y-%m')
        
        df.attrs['total_count'] = total_count
        return df
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        return pd.DataFrame()


# ========== ЗАГРУЗКА ПАТЕНТОВ ==========
def load_patents(domain_key):
    if domain_key == 'semiconductors':
        patents_dir = SERVER_PATENTS_SEMICONDUCTORS_PATH
    else:
        patents_dir = SERVER_PATENTS_GE_PATH
    patents_file = patents_dir / 'patents.parquet'
    if not patents_file.exists():
        return pd.DataFrame()
    
    try:
        df_full = pd.read_parquet(patents_file)
        total_count = len(df_full)
        if len(df_full) > SAMPLE_SIZE:
            df = df_full.sample(SAMPLE_SIZE, random_state=42)
        else:
            df = df_full
        
        if 'publication_date' in df.columns:
            df['publication_date'] = pd.to_datetime(df['publication_date'], format='%Y%m%d', errors='coerce')
            df['year_month'] = df['publication_date'].dt.strftime('%Y-%m')
        
        df.attrs['total_count'] = total_count
        return df
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        return pd.DataFrame()


# ========== ЗАГРУЗКА ЗАЯВИТЕЛЕЙ ==========
def load_assignees(domain_key):
    if domain_key == 'semiconductors':
        assignees_file = SERVER_PATENTS_SEMICONDUCTORS_PATH / 'assignee_harmonized.parquet'
    else:
        assignees_file = SERVER_PATENTS_GE_PATH / 'assignee_harmonized.parquet'
    if not assignees_file.exists():
        return None
    try:
        return pd.read_parquet(assignees_file)
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        return None


# ========== ЗАГРУЗКА ДАННЫХ О ЛАГАХ ==========
def load_lag_data(domain_key):
    """Загрузка данных о временных лагах для гистограммы"""
    lag_file = Path('/home/ubuntu/indlab-techtrends-ds/src/data/time_lag/time_lag.csv')
    
    if not lag_file.exists():
        logger.warning(f"Файл лагов не найден: {lag_file}")
        np.random.seed(42)
        return pd.Series(np.random.gamma(2, 3, 1000))
    
    df = pd.read_csv(lag_file)
    logger.info(f"Загружено лагов: {len(df):,}")
    
    lag_column = None
    for col in ['lag_years', 'time_lag', 'lag', 'years', 'median_lag']:
        if col in df.columns:
            lag_column = col
            break
    
    if lag_column:
        lags = df[lag_column].dropna()
        lags = lags[(lags >= 0) & (lags <= 30)]
        logger.info(f"Лаги после очистки: {len(lags):,} записей, медиана: {lags.median():.1f}")
        return lags
    else:
        logger.warning(f"Колонка с лагом не найдена. Доступны: {df.columns.tolist()}")
        np.random.seed(42)
        return pd.Series(np.random.gamma(2, 3, 1000))


# ========== ФУНКЦИИ ДЛЯ РАСЧЕТА МЕТРИК ==========
def calculate_real_growth(df, date_col, days_back, min_threshold=10):
    if df is None or len(df) == 0 or date_col not in df.columns:
        return 0
    
    df = df.copy()
    df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
    df = df.dropna(subset=[date_col])
    if len(df) == 0:
        return 0
    
    latest_date = df[date_col].max()
    period_ago = latest_date - pd.Timedelta(days=days_back)
    period_before = period_ago - pd.Timedelta(days=days_back)
    
    recent = df[df[date_col] >= period_ago]
    older = df[(df[date_col] >= period_before) & (df[date_col] < period_ago)]
    
    if len(older) < min_threshold:
        return 0
    growth = (len(recent) - len(older)) / len(older) * 100
    return round(growth, 1)


def calculate_cagr(series, years):
    if len(series) < 2:
        return 0
    start_val = series.iloc[0]
    end_val = series.iloc[-1]
    if start_val == 0:
        return 0
    cagr = (end_val / start_val) ** (1 / years) - 1
    return round(cagr * 100, 1)


def get_yearly_counts(df, date_col):
    if df is None or date_col not in df.columns:
        return pd.Series()
    dates = pd.to_datetime(df[date_col], errors='coerce')
    return dates.groupby(dates.dt.year).size()


def get_top_organizations(publications_df, limit=5):
    if publications_df is None or 'institutions' not in publications_df.columns:
        return ['Нет данных']
    
    all_orgs = []
    for inst in publications_df['institutions'].dropna():
        try:
            if isinstance(inst, str) and inst.startswith('['):
                inst_list = ast.literal_eval(inst)
            elif isinstance(inst, str):
                inst_list = [inst]
            else:
                inst_list = inst if isinstance(inst, list) else [inst]
            if isinstance(inst_list, list):
                all_orgs.extend([org.strip() for org in inst_list if org])
        except:
            if isinstance(inst, str) and inst.strip():
                all_orgs.append(inst.strip())
    
    top_orgs = Counter(all_orgs).most_common(limit)
    return [org for org, count in top_orgs if org] if top_orgs else ['Нет данных']


def get_evidence_papers(publications_df, limit=5):
    if publications_df is None or len(publications_df) == 0:
        return []
    
    evidence = []
    df = publications_df.copy()
    if 'cited_by_count' in df.columns:
        df = df.sort_values('cited_by_count', ascending=False)
    elif 'publication_date' in df.columns:
        df = df.sort_values('publication_date', ascending=False)
    
    for idx, row in df.head(limit).iterrows():
        evidence.append({
            'title': row.get('title', 'Без названия')[:120],
            'year': str(row.get('publication_date', ''))[:4] if 'publication_date' in row else 'N/A',
            'venue': row.get('host_venue', 'N/A')[:50],
            'doi': row.get('doi', None),
            'citations': row.get('cited_by_count', 0)
        })
    return evidence


def get_evidence_patents(patents_df, limit=5):
    if patents_df is None or len(patents_df) == 0:
        return []
    
    evidence = []
    df = patents_df.copy()
    if 'publication_date' in df.columns:
        df = df.sort_values('publication_date', ascending=False)
    
    for idx, row in df.head(limit).iterrows():
        evidence.append({
            'number': row.get('publication_number', 'N/A')[:25],
            'year': str(row.get('publication_date', ''))[:4] if 'publication_date' in row else 'N/A',
            'assignee': row.get('assignee', 'Неизвестно')[:50],
            'country': row.get('country_code', 'N/A')
        })
    return evidence


def get_cpc_codes_for_domain(domain_name):
    domain_key = DOMAIN_MAP.get(domain_name, domain_name.lower())
    return CPC_CODES.get(domain_key, [])


def get_topic_ids_for_domain(domain_name):
    domain_key = DOMAIN_MAP.get(domain_name, domain_name.lower())
    return TOPIC_IDS.get(domain_key, [])


def filter_assignees_by_country(assignees_df, patents_df, selected_countries):
    if assignees_df is None or patents_df is None or not selected_countries:
        return assignees_df
    
    filtered_patents = patents_df[patents_df['country_code'].isin(selected_countries)]
    filtered_numbers = set(filtered_patents['publication_number'].unique())
    
    if 'patent_id' in assignees_df.columns:
        return assignees_df[assignees_df['patent_id'].isin(filtered_numbers)]
    return assignees_df


# ========== ЗАГРУЗКА КЛАСТЕРОВ ==========
@st.cache_data(ttl=3600)
def load_clusters_data():
    clusters_file = DATA_PROCESSED / 'clusters_full.parquet'
    if not clusters_file.exists():
        return None
    return pd.read_parquet(clusters_file)


@st.cache_data(ttl=3600)
def load_cluster_timeseries():
    ts_file = DATA_PROCESSED / 'cluster_timeseries.parquet'
    if not ts_file.exists():
        return None
    return pd.read_parquet(ts_file)


# ========== ОСНОВНАЯ ФУНКЦИЯ ЗАГРУЗКИ ==========
@st.cache_data(ttl=3600)
def load_domain_data(domain_name):
    domain_key = DOMAIN_MAP.get(domain_name, domain_name.lower())
    
    publications_df = load_publications(domain_key)
    patents_df = load_patents(domain_key)
    assignees_df = load_assignees(domain_key)
    lags = load_lag_data(domain_key)
    
    # Агрегация для графиков
    dates, papers, patents = [], [], []
    
    if publications_df is not None and 'year_month' in publications_df.columns:
        papers_by_month = publications_df.groupby('year_month').size()
    else:
        papers_by_month = pd.Series(dtype=int)
    
    if patents_df is not None and 'year_month' in patents_df.columns:
        patents_by_month = patents_df.groupby('year_month').size()
    else:
        patents_by_month = pd.Series(dtype=int)
    
    all_months = sorted(set(papers_by_month.index) | set(patents_by_month.index))
    for month in all_months:
        dates.append(month)
        papers.append(int(papers_by_month.get(month, 0)))
        patents.append(int(patents_by_month.get(month, 0)))
    
    total_papers = publications_df.attrs.get('total_count', len(publications_df)) if publications_df is not None else 0
    total_patents = patents_df.attrs.get('total_count', len(patents_df)) if patents_df is not None else 0
    
    def calculate_growth(series, months):
        if len(series) <= months:
            return 0
        current = series[-1]
        previous = series[-months-1]
        return round((current - previous) / previous * 100, 1) if previous > 0 else 0
    
    papers_growth = calculate_growth(papers, 12)
    patents_growth = calculate_growth(patents, 12)
    
    # Расширенные метрики
    real_papers_growth_30d = calculate_real_growth(publications_df, 'publication_date', 30)
    real_papers_growth_90d = calculate_real_growth(publications_df, 'publication_date', 90)
    real_papers_growth_365d = calculate_real_growth(publications_df, 'publication_date', 365)
    real_patents_growth_6m = calculate_real_growth(patents_df, 'publication_date', 180)
    real_patents_growth_12m = calculate_real_growth(patents_df, 'publication_date', 365)
    real_patents_growth_24m = calculate_real_growth(patents_df, 'publication_date', 730)
    
    pub_yearly = get_yearly_counts(publications_df, 'publication_date')
    cagr_3y = calculate_cagr(pub_yearly.tail(3), 3) if len(pub_yearly) >= 3 else 0
    cagr_5y = calculate_cagr(pub_yearly.tail(5), 5) if len(pub_yearly) >= 5 else 0
    
    trend_signal = max(0, min(100, int((real_papers_growth_90d + 50 + real_patents_growth_12m + 50) / 2)))
    if trend_signal >= 80:
        trend_signal_status = "Emerging"
    elif trend_signal >= 60:
        trend_signal_status = "Growing"
    elif trend_signal >= 40:
        trend_signal_status = "Stable"
    else:
        trend_signal_status = "Cooling"
    
    # Топ заявители
    top_assignees = ['Нет данных']
    assignee_values = [0]
    if assignees_df is not None and 'name' in assignees_df.columns:
        assignee_counts = assignees_df['name'].value_counts().head(5)
        if len(assignee_counts) > 0:
            top_assignees = assignee_counts.index.tolist()
            assignee_values = assignee_counts.values.tolist()
    
    top_orgs = get_top_organizations(publications_df, 5)
    
    # География
    countries = ['Нет данных']
    country_values = [100]
    if patents_df is not None and 'country_code' in patents_df.columns:
        geo_counts = patents_df['country_code'].value_counts().head(5)
        if len(geo_counts) > 0:
            countries = [COUNTRY_NAMES.get(c, c) for c in geo_counts.index.tolist()]
            country_values = geo_counts.values.tolist()
    
    # Загрузка метрик
    ai_share = load_ai_share_from_json(domain_key)
    trend_data = load_trend_score_data(domain_key)
    speed_metrics = load_speed_score_from_file(domain_key)
    median_lag = lags.median() if lags is not None and len(lags) > 0 else 4.5
    evidence_papers = get_evidence_papers(publications_df, 5)
    evidence_patents = get_evidence_patents(patents_df, 5)
    
    # Расчет Trend Score
    cagr_score = min(100, max(0, int((cagr_3y + 50) / 2))) if cagr_3y != 0 else 50
    growth_score = min(100, max(0, int((real_papers_growth_90d + real_patents_growth_12m + 100) / 2)))
    trend_score = min(100, max(0, int((cagr_score + growth_score) / 2)))
    
    if trend_score >= 80:
        trend_status = "Emerging"
    elif trend_score >= 60:
        trend_status = "Growing"
    elif trend_score >= 40:
        trend_status = "Stable"
    else:
        trend_status = "Cooling"
    
    # ========== ПРОГНОЗНЫЕ МЕТРИКИ ==========
    if len(papers) >= 12:
        last_year_papers = papers[-12:]
        last_year_patents = patents[-12:]
        if last_year_papers[-2] > 0:
            papers_forecast = int(last_year_papers[-1] * (1 + (last_year_papers[-1] - last_year_papers[-2]) / last_year_papers[-2]))
        else:
            papers_forecast = last_year_papers[-1]
        if last_year_patents[-2] > 0:
            patents_forecast = int(last_year_patents[-1] * (1 + (last_year_patents[-1] - last_year_patents[-2]) / last_year_patents[-2]))
        else:
            patents_forecast = last_year_patents[-1]
    else:
        papers_forecast = papers[-1] if papers else 0
        patents_forecast = patents[-1] if patents else 0
    
    metrics = {
        'papers_total': total_papers,
        'patents_total': total_patents,
        'papers_growth': papers_growth,
        'patents_growth': patents_growth,
        'time_lag': median_lag,
        'trend_score': trend_score,
        'trend_status': trend_status,
        'ai_share': ai_share,
        'real_papers_growth_30d': real_papers_growth_30d,
        'real_papers_growth_90d': real_papers_growth_90d,
        'real_papers_growth_365d': real_papers_growth_365d,
        'real_patents_growth_6m': real_patents_growth_6m,
        'real_patents_growth_12m': real_patents_growth_12m,
        'real_patents_growth_24m': real_patents_growth_24m,
        'cagr_3y': cagr_3y,
        'cagr_5y': cagr_5y,
        'trend_signal': trend_signal,
        'trend_signal_status': trend_signal_status,
        'top_assignees': top_assignees,
        'assignee_values': assignee_values,
        'top_orgs': top_orgs,
        'countries': countries,
        'country_values': country_values,
        'evidence_papers': evidence_papers,
        'evidence_patents': evidence_patents,
        'speed_score': speed_metrics.get('speed_score', 0),
        'speed_status': speed_metrics.get('speed_status', 'Нет данных'),
        'speed_acceleration_rate': speed_metrics.get('acceleration_rate', 0),
        'speed_time_to_market': speed_metrics.get('time_to_market', 0),
        'lags': lags,
        'papers_forecast': max(0, papers_forecast),
        'patents_forecast': max(0, patents_forecast),
        'forecast_period': (datetime.now() + timedelta(days=365)).strftime('%Y-%m')
    }
    
    logger.info(f"Данные для {domain_name} загружены")
    return np.array(dates), np.array(papers), np.array(patents), metrics, publications_df, patents_df, assignees_df


logger.info("data_loader загружен")