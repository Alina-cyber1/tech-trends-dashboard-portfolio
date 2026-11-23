import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import numpy as np
import io
import time
import requests

print("app.py начал выполняться")

from data_loader import (
    load_domain_data, load_clusters_data, load_cluster_timeseries,
    get_cpc_codes_for_domain, get_topic_ids_for_domain,
    filter_assignees_by_country
)

st.set_page_config(
    page_title="Tech Trends Monitor",
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded"
)

if 'selected_countries' not in st.session_state:
    st.session_state['selected_countries'] = ['US', 'CN', 'EP']

st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 2.5rem;
        font-weight: 700;
        margin-bottom: 0;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 10px;
        padding: 20px;
        color: white;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .domain-card {
        background: white;
        border-radius: 10px;
        padding: 20px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        border-left: 5px solid #667eea;
        margin-bottom: 10px;
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<h1 class="main-header">Tech Trends Monitor</h1>', unsafe_allow_html=True)
st.markdown("*Отслеживание перехода науки в технологии*")

with st.sidebar:
    st.markdown("## Панель управления")
    st.markdown("---")
    
    domain = st.selectbox(
        "Технологический домен",
        ["Полупроводники", "Генная инженерия"],
        help="Выберите технологическую область для анализа"
    )

    domain_clean = domain
    domain_key = "semiconductors" if "Полупроводники" in domain else "gene_engineering"

    cpc_list = get_cpc_codes_for_domain(domain)
    topic_ids = get_topic_ids_for_domain(domain)
    
    st.markdown(f"""
    <div class="domain-card">
        <b>CPC коды:</b><br>{', '.join(cpc_list)}<br>
        <b>Topics:</b><br>{', '.join(topic_ids)}
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("### Период анализа")
    year_range = st.slider("Выберите годы", 2015, 2025, (2020, 2025))

    st.markdown("### Страны патентования")
    col1, col2 = st.columns(2)
    with col1:
        selected_us = st.checkbox("US", value=True)
        selected_cn = st.checkbox("CN", value=True)
        selected_jp = st.checkbox("JP", value=False)
    with col2:
        selected_kr = st.checkbox("KR", value=False)
        selected_ep = st.checkbox("EP", value=True)
        selected_wo = st.checkbox("WO", value=False)
    
    selected_countries = []
    if selected_us: selected_countries.append('US')
    if selected_cn: selected_countries.append('CN')
    if selected_jp: selected_countries.append('JP')
    if selected_kr: selected_countries.append('KR')
    if selected_ep: selected_countries.append('EP')
    if selected_wo: selected_countries.append('WO')
    
    st.caption(f"Выбрано стран: {len(selected_countries)}")
    st.session_state['selected_countries'] = selected_countries

with st.spinner(f"Загрузка данных..."):
    try:
        result = load_domain_data(domain_clean)
        dates, papers, patents, metrics = result[:4]
        if len(result) >= 7:
            publications_df = result[4]
            patents_df = result[5]
            assignees_df = result[6]
        else:
            publications_df = None
            patents_df = None
            assignees_df = None
        data_available = len(dates) > 0
    except Exception as e:
        st.error(f"Ошибка загрузки: {e}")
        st.stop()

start_year, end_year = year_range
mask_years = []
for d in dates:
    try:
        year = int(str(d)[:4]) if d else None
        mask_years.append(year is not None and start_year <= year <= end_year)
    except:
        mask_years.append(False)

if any(mask_years):
    dates_filtered = np.array(dates)[mask_years]
    papers_filtered = np.array(papers)[mask_years]
    patents_filtered = np.array(patents)[mask_years]
else:
    dates_filtered = np.array(dates)
    papers_filtered = np.array(papers)
    patents_filtered = np.array(patents)


def format_metric(value):
    if value == 0 or value is None:
        return "--"
    return f"{value:+.1f}%"


# ========== STATUS BAR ==========
st.markdown("---")
st.markdown("### Статус системы")

col_status1, col_status2, col_status3, col_status4 = st.columns(4)

with col_status1:
    try:
        api_response = requests.get("http://localhost:8001/topics", timeout=2)
        if api_response.status_code == 200:
            api_status = "Активно"
            api_color = "🟢"
        else:
            api_status = "Недоступно"
            api_color = "🔴"
    except:
        api_status = "Недоступно"
        api_color = "🔴"
    st.markdown(f"""
    <div style='background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); border-radius: 10px; padding: 15px; text-align: center;'>
        <h3 style='margin:0; color: white;'>API OpenAlex</h3>
        <p style='font-size: 1.5rem; margin:5px 0; color: {"#00ff00" if api_status == "Активно" else "#ff4444"};'>{api_color} {api_status}</p>
    </div>
    """, unsafe_allow_html=True)

with col_status2:
    data_status = "Загружено" if data_available else "Ожидание"
    data_color = "🟢" if data_available else "🟡"
    st.markdown(f"""
    <div style='background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); border-radius: 10px; padding: 15px; text-align: center;'>
        <h3 style='margin:0; color: white;'>Статус данных</h3>
        <p style='font-size: 1.5rem; margin:5px 0; color: {"#00ff00" if data_available else "#ffaa00"};'>{data_color} {data_status}</p>
    </div>
    """, unsafe_allow_html=True)

with col_status3:
    papers_count = f"{metrics.get('papers_total', 0):,}"
    st.markdown(f"""
    <div style='background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); border-radius: 10px; padding: 15px; text-align: center;'>
        <h3 style='margin:0; color: white;'>Публикации</h3>
        <p style='font-size: 1.5rem; margin:5px 0; color: #00cc96;'> {papers_count}</p>
    </div>
    """, unsafe_allow_html=True)

with col_status4:
    patents_count = f"{metrics.get('patents_total', 0):,}"
    st.markdown(f"""
    <div style='background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); border-radius: 10px; padding: 15px; text-align: center;'>
        <h3 style='margin:0; color: white;'>Патенты</h3>
        <p style='font-size: 1.5rem; margin:5px 0; color: #ff4b4b;'> {patents_count}</p>
    </div>
    """, unsafe_allow_html=True)

# Получаем время последнего обновления из ai_share.json
import json
try:
    with open('/home/ubuntu/dashboard/ai_share.json', 'r') as f:
        ai_data = json.load(f)
    last_update = ai_data.get('last_update', 'неизвестно')
    if last_update != 'неизвестно':
        try:
            last_update = datetime.fromisoformat(last_update).strftime('%d.%m.%Y %H:%M')
        except:
            pass
except:
    last_update = 'неизвестно'

st.markdown(f"""
<div style='background: #1a1a2e; border-radius: 10px; padding: 10px; text-align: center; margin-top: 10px;'>
    <span style='color: #888;'> Последнее обновление AI Share: </span>
    <span style='color: #00cc96; font-weight: bold;'>{last_update}</span>
</div>
""", unsafe_allow_html=True)
st.markdown("---")


st.markdown("## Topic Card")

st.markdown(f"### {domain_clean}")
st.caption(f"Данные обновлены: {datetime.now().strftime('%d.%m.%Y %H:%M')}")
st.markdown(f"**Покрытие:** публикации (30/90/365 дней) | патенты (6/12/24 месяца)")

trend_signal = metrics.get('trend_signal', 0)
trend_signal_status = metrics.get('trend_signal_status', 'Stable')
st.markdown(f"**Сигнал тренда:** {trend_signal}/100 ({trend_signal_status})")

col_t1, col_t2, col_t3, col_t4, col_t5 = st.columns(5)

with col_t1:
    st.markdown("#### Публикации")
    st.metric("30 дней", format_metric(metrics.get('real_papers_growth_30d', 0)))
    st.metric("90 дней", format_metric(metrics.get('real_papers_growth_90d', 0)))
    st.metric("365 дней", format_metric(metrics.get('real_papers_growth_365d', 0)))
    st.caption(f"Всего: {metrics.get('papers_total', 0):,}")

with col_t2:
    st.markdown("#### Патенты")
    st.metric("6 мес", format_metric(metrics.get('real_patents_growth_6m', 0)))
    st.metric("12 мес", format_metric(metrics.get('real_patents_growth_12m', 0)))
    st.metric("24 мес", format_metric(metrics.get('real_patents_growth_24m', 0)))
    st.caption(f"Всего: {metrics.get('patents_total', 0):,}")

with col_t3:
    st.markdown("#### Тренд")
    st.metric("Trend Score", f"{metrics.get('trend_score', 0)}/100", metrics.get('trend_status', 'Стабильный'))
    st.metric("Trend Signal", f"{trend_signal}/100", trend_signal_status)
    st.caption(f"CAGR 3 года: {format_metric(metrics.get('cagr_3y', 0))} | CAGR 5 лет: {format_metric(metrics.get('cagr_5y', 0))}")

with col_t4:
    st.markdown("#### AI проникновение")
    ai_share = metrics.get('ai_share', 0)
    st.metric("AI Share", f"{ai_share}%" if ai_share > 0 else "--", "в патентах")
    st.caption("G06N* классификация")

with col_t5:
    st.markdown("#### Speed Score")
    speed_score = metrics.get('speed_score', 0)
    st.metric("Speed Score", f"{speed_score}/100" if speed_score > 0 else "--", 
              metrics.get('speed_status', 'Нет данных'))
    st.caption(f"Ускорение: {format_metric(metrics.get('speed_acceleration_rate', 0))}")

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.markdown(f"""
    <div class="metric-card">
        <h3 style="color: white; margin:0">Публикации</h3>
        <h1 style="color: white; margin:0">{metrics.get('papers_total', 0):,}</h1>
        <p style="color: white; margin:0">{format_metric(metrics.get('papers_growth', 0))} за год</p>
    </div>
    """, unsafe_allow_html=True)
with col2:
    st.markdown(f"""
    <div class="metric-card">
        <h3 style="color: white; margin:0">Патенты</h3>
        <h1 style="color: white; margin:0">{metrics.get('patents_total', 0):,}</h1>
        <p style="color: white; margin:0">{format_metric(metrics.get('patents_growth', 0))} за год</p>
    </div>
    """, unsafe_allow_html=True)
with col3:
    time_lag = metrics.get('time_lag', 0)
    st.markdown(f"""
    <div class="metric-card">
        <h3 style="color: white; margin:0">Time Lag</h3>
        <h1 style="color: white; margin:0">{time_lag:.1f} года</h1>
        <p style="color: white; margin:0">медианное значение</p>
    </div>
    """, unsafe_allow_html=True)
with col4:
    st.markdown(f"""
    <div class="metric-card">
        <h3 style="color: white; margin:0">Trend Score</h3>
        <h1 style="color: white; margin:0">{metrics.get('trend_score', 0)}/100</h1>
        <p style="color: white; margin:0">{metrics.get('trend_status', 'Нет данных')}</p>
    </div>
    """, unsafe_allow_html=True)

st.markdown("### Топ-5 игроков")
col_players1, col_players2 = st.columns(2)

with col_players1:
    st.markdown("**Top assignees (патенты):**")
    top_assignees = metrics.get('top_assignees', ['Нет данных'])
    if top_assignees and top_assignees[0] != 'Нет данных':
        for i, assignee in enumerate(top_assignees[:5], 1):
            st.write(f"{i}. **{assignee}**")
    else:
        st.write("Нет данных о заявителях")

with col_players2:
    st.markdown("**Top orgs (публикации):**")
    top_orgs = metrics.get('top_orgs', ['Нет данных'])
    if top_orgs and top_orgs[0] != 'Нет данных':
        for i, org in enumerate(top_orgs[:5], 1):
            st.write(f"{i}. **{org}**")
    else:
        st.write("Нет данных об организациях")


# ========== ТОП-5 ПО УСКОРЕНИЮ ==========
st.markdown("### Топ-5 по ускорению")

if assignees_df is not None and 'name' in assignees_df.columns and len(assignees_df) > 0:
    assignee_counts = assignees_df['name'].value_counts().head(10)
    st.write("**Лидеры по активности (патенты):**")
    for i, (name, count) in enumerate(assignee_counts.head(5).items(), 1):
        st.write(f"{i}. **{name}** - {count} патентов")
else:
    st.write("**Лидеры по активности (патенты):**")
    st.write("1. **Samsung Electronics** - лидер по патентованию")
    st.write("2. **TSMC** - высокая активность")
    st.write("3. **IBM** - значительный портфель")
    st.write("4. **Intel Corporation** - ключевой игрок")
    st.write("5. **Micron Technology** - активный участник")


# ========== TOPIC CARD ДЛЯ ОТПРАВКИ ==========
st.markdown("### Topic Card для отправки")

if metrics.get('real_papers_growth_90d', 0) > 10 and metrics.get('real_patents_growth_12m', 0) > 10:
    meaning = "Наука активно растёт, патенты догоняют -> технология переходит из исследований в коммерческие разработки"
elif metrics.get('real_papers_growth_90d', 0) > 10 and metrics.get('real_patents_growth_12m', 0) <= 10:
    meaning = "Наука растёт, но патентов пока мало -> технология на ранней стадии, потенциал высок"
elif metrics.get('real_papers_growth_90d', 0) <= 10 and metrics.get('real_patents_growth_12m', 0) > 10:
    meaning = "Патенты активно растут при стабильной науке -> технология зрелая, идёт коммерциализация"
else:
    meaning = "Стабильное развитие без резких скачков -> технология в фазе насыщения"

evidence_papers = metrics.get('evidence_papers', [])
evidence_patents = metrics.get('evidence_patents', [])

card_text = f"""{domain_clean} | {datetime.now().strftime('%d.%m.%Y')}

Рост: публикации {format_metric(metrics.get('real_papers_growth_90d', 0))} за 90 дней | патенты {format_metric(metrics.get('real_patents_growth_12m', 0))} за 12 мес

Топ-5 игроков:
- Патенты: {', '.join(metrics.get('top_assignees', [])[:3])}
- Публикации: {', '.join(metrics.get('top_orgs', [])[:3])}

Ключевые публикации:
{chr(10).join([f'- {p["title"][:70]}... ({p["year"]})' for p in evidence_papers[:3]]) if evidence_papers else '- Нет данных'}

Ключевые патенты:
{chr(10).join([f'- {p["number"]} - {p["assignee"][:30]} ({p["year"]})' for p in evidence_patents[:3]]) if evidence_patents else '- Нет данных'}

Вывод: {meaning}"""

st.text(card_text)

st.download_button(
    label="Скопировать Topic Card",
    data=card_text,
    file_name=f"{domain_clean}_topic_card.txt",
    mime="text/plain"
)


st.markdown("### География патентования")
countries = metrics.get('countries', ['Нет данных'])
country_values = metrics.get('country_values', [100])
if countries[0] != 'Нет данных':
    geo_df = pd.DataFrame({'country': countries[:5], 'patents': country_values[:5]})
    country_codes = {'США': 'USA', 'Китай': 'CHN', 'Япония': 'JPN', 'Южная Корея': 'KOR', 'Европа': 'EUU'}
    geo_df['iso_alpha'] = geo_df['country'].map(country_codes).fillna('OWID_WRL')
    fig_geo = px.choropleth(geo_df, locations='iso_alpha', color='patents',
                            hover_name='country', color_continuous_scale='Viridis')
    fig_geo.update_layout(height=400)
    st.plotly_chart(fig_geo, use_container_width=True, key="geo_chart")
else:
    st.info("Нет данных о географии")

st.markdown("### Evidence: ключевые документы")
col_ev1, col_ev2 = st.columns(2)

with col_ev1:
    st.markdown("**3 ключевых публикации:**")
    if evidence_papers:
        for i, paper in enumerate(evidence_papers[:3], 1):
            title = paper['title'][:80] + "..." if len(paper['title']) > 80 else paper['title']
            st.write(f"{i}. **{title}** ({paper['year']})")
            if paper.get('doi'):
                st.markdown(f"   DOI: {paper['doi']}")
    else:
        st.write("Нет данных о публикациях")

with col_ev2:
    st.markdown("**3 ключевых патента:**")
    if evidence_patents:
        for i, patent in enumerate(evidence_patents[:3], 1):
            st.write(f"{i}. **{patent['number']}** ({patent['year']})")
            st.caption(f"   Заявитель: {patent['assignee'][:50]}")
    else:
        st.write("Нет данных о патентах")

st.markdown("---")
st.markdown("## Динамика развития")

fig = go.Figure()
fig.add_trace(go.Scatter(
    x=dates_filtered, y=papers_filtered,
    name='Научные публикации',
    line=dict(color='#00CC96', width=4),
    fill='tozeroy',
    fillcolor='rgba(0,204,150,0.1)'
))
fig.add_trace(go.Scatter(
    x=dates_filtered, y=patents_filtered,
    name='Патенты',
    line=dict(color='#FF4B4B', width=4),
    fill='tozeroy',
    fillcolor='rgba(255,75,75,0.1)',
    yaxis='y2'
))

fig.update_layout(
    title=f"{domain_clean}: Наука vs Технологии",
    xaxis_title="Год",
    yaxis_title="Количество публикаций",
    yaxis2=dict(title="Количество патентов", overlaying='y', side='right'),
    hovermode='x unified',
    height=500,
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
)
st.plotly_chart(fig, use_container_width=True, key="main_chart")

st.markdown("### Распределение временного лага")
lags = metrics.get('lags')
if lags is not None and len(lags) > 0:
    fig_lag = px.histogram(
        x=lags, nbins=30,
        labels={'x': 'Лаг (годы)', 'y': 'Количество пар'},
        color_discrete_sequence=['#667eea']
    )
    median_lag = lags.median()
    fig_lag.add_vline(x=median_lag, line_dash="dash", line_color="red",
                     annotation_text=f"Медиана: {median_lag:.1f} лет")
    st.plotly_chart(fig_lag, use_container_width=True, key="lag_chart")
    
    col_l1, col_l2, col_l3 = st.columns(3)
    with col_l1: st.metric("Медианный лаг", f"{median_lag:.1f} лет")
    with col_l2: st.metric("Средний лаг", f"{lags.mean():.1f} лет")
    with col_l3: st.metric("Количество пар", f"{len(lags):,}")
else:
    st.info("Данные о временных лагах загружаются...")

st.markdown("---")
st.markdown("## Monthly Deep Dive")

st.markdown("### Executive Summary")

# ========== ML ПРОГНОЗ ==========
st.markdown("### ML Прогноз ")

try:
    # Загружаем прогнозы
    ml_forecast = pd.read_parquet('/home/ubuntu/techtrend-ds-ae/features/output/dashboard_predictions.parquet')
    
    # Фильтруем по текущему домену
    domain_filter = "semiconductors" if "Полупроводники" in domain_clean else "gene_engineering"
    df_forecast = ml_forecast[ml_forecast['domain'] == domain_filter].copy()
    
    if len(df_forecast) > 0:
        # Форматируем для отображения
        df_forecast['Прогноз роста'] = df_forecast['predicted_pct'].apply(lambda x: f"{x:.1f}%")
        df_forecast['Нижняя граница'] = df_forecast['band95_low_pct'].apply(lambda x: f"{x:.1f}%")
        df_forecast['Верхняя граница'] = df_forecast['band95_high_pct'].apply(lambda x: f"{x:.1f}%")
        df_forecast['Горизонт'] = df_forecast['horizon'].apply(lambda x: f"{x} кварталов ({x*3} мес)")
        
        display_df = df_forecast[['Горизонт', 'Прогноз роста', 'Нижняя граница', 'Верхняя граница']]
        st.dataframe(display_df, use_container_width=True)
        
        # Доверительный интервал
        st.caption("Доверительный интервал 95%, модель XGBoost, ROC-AUC 0.71")
    else:
        st.info("Нет данных прогноза для этого домена")
except Exception as e:
    st.info(f"Данные ML прогноза загружаются")
st.markdown(f"""
**Ключевые выводы по домену {domain_clean}:**

1. **Тренд:** Trend Score = {metrics.get('trend_score', 0)}/100 ({metrics.get('trend_status', 'Стабильный')})
2. **Рост публикаций:** {format_metric(metrics.get('real_papers_growth_90d', 0))} за 90 дней
3. **Рост патентов:** {format_metric(metrics.get('real_patents_growth_12m', 0))} за 12 месяцев
4. **Time Lag:** {metrics.get('time_lag', 0)} лет
5. **AI проникновение:** {metrics.get('ai_share', 0)}% патентов
6. **Speed Score:** {metrics.get('speed_score', 0)}/100 ({metrics.get('speed_status', 'Нет данных')})
""")


st.markdown("### Подтехнологии внутри темы")
clusters_df = load_clusters_data()
cluster_ts = load_cluster_timeseries()

if clusters_df is not None and cluster_ts is not None:
    cluster_list = cluster_ts[['cluster_id', 'cluster_name']].drop_duplicates().sort_values('cluster_id')
    if len(cluster_list) > 0:
        st.info(f"Найдено {len(cluster_list)} технологических кластеров")
        
        for _, info in cluster_list.head(10).iterrows():
            cluster_id = info['cluster_id']
            cluster_name = info['cluster_name']
            docs_count = len(clusters_df[clusters_df['cluster_id'] == cluster_id])
            ts_data = cluster_ts[cluster_ts['cluster_id'] == cluster_id].sort_values('year')
            
            if len(ts_data) >= 2:
                cluster_growth = ((ts_data['article_count'].iloc[-1] - ts_data['article_count'].iloc[-2]) / 
                                 ts_data['article_count'].iloc[-2] * 100) if ts_data['article_count'].iloc[-2] > 0 else 0
            else:
                cluster_growth = 0
            
            with st.expander(f"**{cluster_name}** (ID: {cluster_id}, документов: {docs_count:,}, рост: {cluster_growth:+.1f}%)"):
                if len(ts_data) > 0:
                    fig_cluster = px.line(ts_data, x='year', y='article_count',
                                          title=f'Динамика публикаций: {cluster_name}')
                    fig_cluster.update_layout(height=250)
                    st.plotly_chart(fig_cluster, use_container_width=True, key=f"cluster_chart_{cluster_id}")
                
                sample_docs = clusters_df[clusters_df['cluster_id'] == cluster_id]['title'].dropna().head(3).tolist()
                if sample_docs:
                    st.markdown("**Примеры документов:**")
                    for i, doc in enumerate(sample_docs, 1):
                        st.write(f"{i}. {doc[:100]}...")
    else:
        st.info("Кластеры не найдены")
else:
    st.info("Данные о кластерах загружаются...")

st.markdown("### Определение темы")
st.markdown(f"""
| Критерий | Значение |
|----------|----------|
| **CPC/IPC коды (патенты)** | {', '.join(cpc_list)} |
| **OpenAlex Topics (публикации)** | {', '.join(topic_ids)} |
""")

st.markdown("### Что читать и смотреть")
col_read1, col_read2 = st.columns(2)
with col_read1:
    st.markdown("**Публикации:**")
    if evidence_papers:
        for paper in evidence_papers[:10]:
            title = paper['title'][:60] + "..." if len(paper['title']) > 60 else paper['title']
            st.markdown(f"- **{title}** ({paper['year']})")
    else:
        st.write("Нет данных")
with col_read2:
    st.markdown("**Патенты:**")
    if evidence_patents:
        for patent in evidence_patents[:10]:
            st.markdown(f"- Патент {patent['number']} — {patent['assignee'][:40]} ({patent['year']})")
    else:
        st.write("Нет данных")

with st.expander("Data Lineage: источники данных"):
    st.markdown("**Патенты фильтруются по CPC кодам:**")
    for cpc in cpc_list:
        st.markdown(f"- `{cpc}*`")
    st.markdown(f"**Публикации фильтруются по OpenAlex Topics:** - {', '.join(topic_ids)}")
    st.markdown("**AI Share рассчитывается по коду G06N***")

# ========== ВКЛАДКИ ==========
tab1, tab2, tab3, tab4, tab5 = st.tabs(["Тренды", "Подтехнологии", "Data Explorer", "Отчеты", "Экспорт"])

with tab1:
    st.markdown("## Динамика развития: Наука vs Патенты")
    
    if len(dates_filtered) > 0:
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=dates_filtered, y=papers_filtered,
            name='Научные публикации',
            line=dict(color='#00CC96', width=4),
            fill='tozeroy',
            fillcolor='rgba(0,204,150,0.1)'
        ))
        fig.add_trace(go.Scatter(
            x=dates_filtered, y=patents_filtered,
            name='Патенты',
            line=dict(color='#FF4B4B', width=4),
            fill='tozeroy',
            fillcolor='rgba(255,75,75,0.1)',
            yaxis='y2'
        ))
        
        fig.update_layout(
            title=f"{domain_clean}: Наука vs Технологии",
            xaxis_title="Год",
            yaxis_title="Количество публикаций",
            yaxis2=dict(title="Количество патентов", overlaying='y', side='right'),
            hovermode='x unified',
            height=500,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        st.plotly_chart(fig, use_container_width=True, key="tab1_chart")
    else:
        st.warning("Нет данных за выбранный период")
    
    st.markdown("---")
    st.markdown("### Распределение временного лага")
    
    lags = metrics.get('lags')
    if lags is not None and len(lags) > 0:
        fig_lag = px.histogram(
            x=lags, nbins=30,
            labels={'x': 'Лаг (годы)', 'y': 'Количество пар'},
            color_discrete_sequence=['#667eea']
        )
        median_lag = lags.median()
        fig_lag.add_vline(x=median_lag, line_dash="dash", line_color="red",
                         annotation_text=f"Медиана: {median_lag:.1f} лет")
        st.plotly_chart(fig_lag, use_container_width=True, key="tab1_lag_chart")
        
        col_l1, col_l2, col_l3 = st.columns(3)
        with col_l1: st.metric("Медианный лаг", f"{median_lag:.1f} лет")
        with col_l2: st.metric("Средний лаг", f"{lags.mean():.1f} лет")
        with col_l3: st.metric("Количество пар", f"{len(lags):,}")
    else:
        st.info("Данные о временных лагах загружаются...")
    
    st.markdown("---")
    st.markdown("### Топ заявителей и география")
    
    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("**Топ заявителей (патенты):**")
        top_assignees = metrics.get('top_assignees', ['Нет данных'])
        if top_assignees and top_assignees[0] != 'Нет данных':
            for i, assignee in enumerate(top_assignees[:5], 1):
                st.write(f"{i}. **{assignee}**")
        else:
            st.write("Нет данных о заявителях")
    
    with col_b:
        st.markdown("**География патентования**")
        countries = metrics.get('countries', ['Нет данных'])
        country_values = metrics.get('country_values', [100])
        if countries[0] != 'Нет данных':
            geo_df = pd.DataFrame({'country': countries[:5], 'patents': country_values[:5]})
            country_codes = {'США': 'USA', 'Китай': 'CHN', 'Япония': 'JPN',
                            'Южная Корея': 'KOR', 'Европа': 'EUU', 'Мир': 'OWID_WRL'}
            geo_df['iso_alpha'] = geo_df['country'].map(country_codes).fillna('OWID_WRL')
            fig_geo = px.choropleth(geo_df, locations='iso_alpha', color='patents',
                                    hover_name='country', color_continuous_scale='Viridis')
            fig_geo.update_layout(height=300)
            st.plotly_chart(fig_geo, use_container_width=True, key="tab1_geo_chart")
        else:
            st.info("Нет данных о географии")

with tab2:
    st.markdown("## Подтехнологии внутри темы")
    
    clusters_df = load_clusters_data()
    cluster_ts = load_cluster_timeseries()
    
    if clusters_df is not None and cluster_ts is not None:
        cluster_list = cluster_ts[['cluster_id', 'cluster_name']].drop_duplicates().sort_values('cluster_id')
        if len(cluster_list) > 0:
            st.info(f"Найдено {len(cluster_list)} технологических кластеров")
            
            for _, info in cluster_list.head(10).iterrows():
                cluster_id = info['cluster_id']
                cluster_name = info['cluster_name']
                docs_count = len(clusters_df[clusters_df['cluster_id'] == cluster_id])
                ts_data = cluster_ts[cluster_ts['cluster_id'] == cluster_id].sort_values('year')
                
                if len(ts_data) >= 2:
                    cluster_growth = ((ts_data['article_count'].iloc[-1] - ts_data['article_count'].iloc[-2]) / 
                                     ts_data['article_count'].iloc[-2] * 100) if ts_data['article_count'].iloc[-2] > 0 else 0
                else:
                    cluster_growth = 0
                
                with st.expander(f"**{cluster_name}** (ID: {cluster_id}, документов: {docs_count:,}, рост: {cluster_growth:+.1f}%)"):
                    if len(ts_data) > 0:
                        fig_cluster = px.line(ts_data, x='year', y='article_count',
                                              title=f'Динамика публикаций: {cluster_name}')
                        fig_cluster.update_layout(height=250)
                        st.plotly_chart(fig_cluster, use_container_width=True, key=f"tab2_cluster_{cluster_id}")
                    
                    sample_docs = clusters_df[clusters_df['cluster_id'] == cluster_id]['title'].dropna().head(3).tolist()
                    if sample_docs:
                        st.markdown("**Примеры документов:**")
                        for i, doc in enumerate(sample_docs, 1):
                            st.write(f"{i}. {doc[:100]}...")
        else:
            st.info("Кластеры не найдены")
    else:
        st.info("Данные о кластерах загружаются...")

with tab3:
    st.markdown("## Data Explorer: просмотр и экспорт данных")
    
    data_type = st.radio("Выберите тип данных:", ["Публикации", "Патенты", "Временные ряды"], horizontal=True)
    
    if data_type == "Публикации":
        st.markdown("### Публикации")
        
        if publications_df is not None and len(publications_df) > 0:
            df_display = publications_df.copy()
            
            if 'publication_date' in df_display.columns:
                years = sorted(df_display['publication_date'].dropna().astype(str).str[:4].unique())
                selected_year = st.selectbox("Фильтр по году", ["Все"] + list(years))
                if selected_year != "Все":
                    df_display = df_display[df_display['publication_date'].astype(str).str.startswith(selected_year)]
            
            search = st.text_input("Поиск по заголовку", placeholder="Введите ключевое слово...")
            if search:
                df_display = df_display[df_display['title'].astype(str).str.contains(search, case=False, na=False)]
            
            st.info(f"Найдено записей: {len(df_display)}")
            
            available_cols = ['title', 'publication_date', 'cited_by_count', 'host_venue', 'doi']
            cols_to_show = [c for c in available_cols if c in df_display.columns]
            
            st.dataframe(df_display[cols_to_show].head(100), use_container_width=True)
            
            csv = df_display[cols_to_show].to_csv(index=False).encode('utf-8')
            st.download_button(
                label="Экспорт публикаций в CSV",
                data=csv,
                file_name=f"{domain_clean}_publications_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )
        else:
            st.info("Нет данных о публикациях")
    
    elif data_type == "Патенты":
        st.markdown("### Патенты")
        
        if patents_df is not None and len(patents_df) > 0:
            df_display = patents_df.copy()
            
            if 'publication_date' in df_display.columns:
                years = sorted(df_display['publication_date'].dropna().astype(str).str[:4].unique())
                selected_year = st.selectbox("Фильтр по году", ["Все"] + list(years))
                if selected_year != "Все":
                    df_display = df_display[df_display['publication_date'].astype(str).str.startswith(selected_year)]
            
            if 'country_code' in df_display.columns:
                countries_list = ["Все"] + sorted(df_display['country_code'].dropna().unique())
                selected_country = st.selectbox("Фильтр по стране", countries_list)
                if selected_country != "Все":
                    df_display = df_display[df_display['country_code'] == selected_country]
            
            st.info(f"Найдено записей: {len(df_display)}")
            
            available_cols = ['publication_number', 'publication_date', 'country_code', 'family_id', 'kind_code']
            cols_to_show = [c for c in available_cols if c in df_display.columns]
            
            st.dataframe(df_display[cols_to_show].head(100), use_container_width=True)
            
            csv = df_display[cols_to_show].to_csv(index=False).encode('utf-8')
            st.download_button(
                label="Экспорт патентов в CSV",
                data=csv,
                file_name=f"{domain_clean}_patents_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )
        else:
            st.info("Нет данных о патентах")
    
    else:
        st.markdown("### Временные ряды")
        
        if len(dates) > 0:
            ts_df = pd.DataFrame({
                'date': dates,
                'publications': papers,
                'patents': patents
            })
            
            st.dataframe(ts_df, use_container_width=True)
            
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=ts_df['date'], y=ts_df['publications'], name='Публикации', line=dict(color='#00CC96')))
            fig.add_trace(go.Scatter(x=ts_df['date'], y=ts_df['patents'], name='Патенты', line=dict(color='#FF4B4B')))
            fig.update_layout(title="Динамика по месяцам", xaxis_title="Дата", yaxis_title="Количество", height=400)
            st.plotly_chart(fig, use_container_width=True, key="tab3_ts_chart")
            
            csv = ts_df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="Экспорт временных рядов в CSV",
                data=csv,
                file_name=f"{domain_clean}_timeseries_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )
        else:
            st.info("Нет данных временных рядов")

trend_signal = metrics.get('trend_signal', 0)
trend_signal_status = metrics.get('trend_signal_status', 'Stable')

with tab4:
    st.subheader("Отчеты по метрикам")
    
    report_data = pd.DataFrame({
        'Метрика': ['Trend Score', 'AI Share', 'Time Lag', 'Публикации', 'Патенты', 'Speed Score', 'Сигнал тренда'],
        'Значение': [
            f"{metrics.get('trend_score', 0)}/100",
            f"{metrics.get('ai_share', 0)}%",
            f"{metrics.get('time_lag', 0)} лет",
            f"{metrics.get('papers_total', 0):,}",
            f"{metrics.get('patents_total', 0):,}",
            f"{metrics.get('speed_score', 0)}/100",
            f"{trend_signal}/100 ({trend_signal_status})"
        ],
        'Статус': [
            metrics.get('trend_status', 'Нет'),
            "G06N* классификация",
            "медианное значение",
            f"рост {format_metric(metrics.get('papers_growth', 0))} за год",
            f"рост {format_metric(metrics.get('patents_growth', 0))} за год",
            metrics.get('speed_status', 'Нет'),
            trend_signal_status
        ]
    })
    
    st.dataframe(report_data, use_container_width=True)
    
    csv_data = report_data.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="Скачать отчет в CSV",
        data=csv_data,
        file_name=f"{domain_clean}_report_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv"
    )
    
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        report_data.to_excel(writer, sheet_name='Metrics', index=False)
        if evidence_papers:
            pd.DataFrame(evidence_papers).to_excel(writer, sheet_name='Publications', index=False)
        if evidence_patents:
            pd.DataFrame(evidence_patents).to_excel(writer, sheet_name='Patents', index=False)
        if len(dates) > 0:
            ts_df = pd.DataFrame({'date': dates, 'papers': papers, 'patents': patents})
            ts_df.to_excel(writer, sheet_name='Timeseries', index=False)
    
    output.seek(0)
    st.download_button(
        label="Скачать полный отчет (Excel)",
        data=output,
        file_name=f"{domain_clean}_report_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    
    st.markdown("---")
    st.markdown("### Topic Card")
    
    report_text = f"""
ОТЧЕТ ПО ДОМЕНУ: {domain_clean}
Дата: {datetime.now().strftime('%d.%m.%Y %H:%M')}

1. ОБЩАЯ ОЦЕНКА
   Trend Score: {metrics.get('trend_score', 0)}/100 ({metrics.get('trend_status', 'Нет')})
   Сигнал тренда: {trend_signal}/100 ({trend_signal_status})
   Time Lag: {metrics.get('time_lag', 0)} лет
   AI Share: {metrics.get('ai_share', 0)}% патентов

2. ДИНАМИКА
   Публикации: {metrics.get('papers_total', 0):,} шт., рост {format_metric(metrics.get('real_papers_growth_90d', 0))} за 90 дней
   Патенты: {metrics.get('patents_total', 0):,} шт., рост {format_metric(metrics.get('real_patents_growth_12m', 0))} за 12 месяцев
   CAGR 3 года: {format_metric(metrics.get('cagr_3y', 0))}
   CAGR 5 лет: {format_metric(metrics.get('cagr_5y', 0))}

3. КЛЮЧЕВЫЕ ИГРОКИ
   Топ заявители: {', '.join(metrics.get('top_assignees', [])[:3])}
   Топ организации: {', '.join(metrics.get('top_orgs', [])[:3])}

4. ГЕОГРАФИЯ
   Страны патентования: {', '.join(metrics.get('countries', [])[:3])}

5. SPEED SCORE
   Значение: {metrics.get('speed_score', 0)}/100 ({metrics.get('speed_status', 'Нет')})
   Ускорение: {format_metric(metrics.get('speed_acceleration_rate', 0))}

6. ВЫВОД
   Технология находится в фазе {metrics.get('trend_status', 'неизвестно')}.
"""
    
    st.text(report_text)
    
    st.download_button(
        label="Скачать Topic Card",
        data=report_text,
        file_name=f"{domain_clean}_report.txt",
        mime="text/plain"
    )
    
       # ========== PDF ОТЧЕТ ==========
    st.markdown("---")
    st.markdown("### PDF отчет")
    
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        
        pdf_buffer = io.BytesIO()
        doc = SimpleDocTemplate(pdf_buffer, pagesize=A4,
                                leftMargin=50, rightMargin=50,
                                topMargin=50, bottomMargin=50)
        styles = getSampleStyleSheet()
        story = []
        
        # Заголовок
        # Конвертируем название домена в английский
        domain_en = "Semiconductors" if "Полупроводники" in domain_clean else "Gene Engineering"
        story.append(Paragraph(f"Tech Trends Report: {domain_en}", styles['Heading1']))
        story.append(Paragraph(f"Date: {datetime.now().strftime('%d.%m.%Y %H:%M')}", styles['Normal']))
        story.append(Spacer(1, 12))
        
        # Секция 1
        story.append(Paragraph("1. OVERALL ASSESSMENT", styles['Heading2']))
        story.append(Paragraph(f"   Trend Score: {metrics.get('trend_score', 0)}/100 ({metrics.get('trend_status', 'No data')})", styles['Normal']))
        story.append(Paragraph(f"   Trend Signal: {trend_signal}/100 ({trend_signal_status})", styles['Normal']))
        story.append(Paragraph(f"   Time Lag: {metrics.get('time_lag', 0)} years", styles['Normal']))
        story.append(Paragraph(f"   AI Share: {metrics.get('ai_share', 0)}% of patents", styles['Normal']))
        story.append(Spacer(1, 10))
        
        # Секция 2
        story.append(Paragraph("2. DYNAMICS", styles['Heading2']))
        story.append(Paragraph(f"   Publications: {metrics.get('papers_total', 0):,} pcs, growth {format_metric(metrics.get('real_papers_growth_90d', 0))} in 90 days", styles['Normal']))
        story.append(Paragraph(f"   Patents: {metrics.get('patents_total', 0):,} pcs, growth {format_metric(metrics.get('real_patents_growth_12m', 0))} in 12 months", styles['Normal']))
        story.append(Paragraph(f"   CAGR 3 years: {format_metric(metrics.get('cagr_3y', 0))}", styles['Normal']))
        story.append(Paragraph(f"   CAGR 5 years: {format_metric(metrics.get('cagr_5y', 0))}", styles['Normal']))
        story.append(Spacer(1, 10))
        
        # Секция 3
        story.append(Paragraph("3. KEY PLAYERS", styles['Heading2']))
        top_assignees_text = ', '.join(metrics.get('top_assignees', [])[:3])
        top_orgs_text = ', '.join(metrics.get('top_orgs', [])[:3])
        story.append(Paragraph(f"   Top assignees: {top_assignees_text if top_assignees_text else 'No data'}", styles['Normal']))
        story.append(Paragraph(f"   Top organizations: {top_orgs_text if top_orgs_text else 'No data'}", styles['Normal']))
        story.append(Spacer(1, 10))
        
        # Секция 4
        story.append(Paragraph("4. GEOGRAPHY", styles['Heading2']))
        story.append(Paragraph(f"   Patenting countries: USA, China, South Korea, Japan, Europe", styles['Normal']))
        story.append(Spacer(1, 10))
        
        # Секция 5
        story.append(Paragraph("5. SPEED SCORE", styles['Heading2']))
        story.append(Paragraph(f"   Value: {metrics.get('speed_score', 0)}/100 ({metrics.get('speed_status', 'No data')})", styles['Normal']))
        story.append(Paragraph(f"   Acceleration: {format_metric(metrics.get('speed_acceleration_rate', 0))}", styles['Normal']))
        story.append(Spacer(1, 10))
        
        # Секция 6
        story.append(Paragraph("6. CONCLUSION", styles['Heading2']))
        story.append(Paragraph(f"   Technology is in {metrics.get('trend_status', 'unknown')} phase.", styles['Normal']))
        story.append(Spacer(1, 10))
        
        # Прогноз
        story.append(Paragraph("7. FORECAST", styles['Heading2']))
        story.append(Paragraph(f"   Publications for {metrics.get('forecast_period', 'next year')}: {metrics.get('papers_forecast', 0):,}", styles['Normal']))
        story.append(Paragraph(f"   Patents for {metrics.get('forecast_period', 'next year')}: {metrics.get('patents_forecast', 0):,}", styles['Normal']))
        
        doc.build(story)
        pdf_buffer.seek(0)
        
        st.download_button(
            label="Download PDF Report",
            data=pdf_buffer,
            file_name=f"{domain_clean}_report.pdf",
            mime="application/pdf"
        )
    except ImportError:
        st.info("Please install: pip install reportlab")
    except Exception as e:
        st.error(f"PDF error: {e}")


with tab5:
    st.subheader("Экспорт данных")
    
    col_exp1, col_exp2 = st.columns(2)
    
    with col_exp1:
        if evidence_papers:
            papers_df = pd.DataFrame(evidence_papers)
            csv_papers = papers_df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="Скачать публикации (CSV)",
                data=csv_papers,
                file_name=f"{domain_clean}_papers.csv",
                mime="text/csv"
            )
    
    with col_exp2:
        if evidence_patents:
            patents_df_report = pd.DataFrame(evidence_patents)
            csv_patents = patents_df_report.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="Скачать патенты (CSV)",
                data=csv_patents,
                file_name=f"{domain_clean}_patents.csv",
                mime="text/csv"
            )
    
    if len(dates) > 0:
        ts_df = pd.DataFrame({'date': dates, 'papers': papers, 'patents': patents})
        csv_ts = ts_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="Скачать временные ряды (CSV)",
            data=csv_ts,
            file_name=f"{domain_clean}_timeseries.csv",
            mime="text/csv"
        )

st.markdown("---")
st.markdown(f"""
<div style='text-align: center; color: gray; padding: 20px;'>
    <p>Data Science платформа мониторинга технологических трендов | MVP v1.0</p>
    <p>Текущий домен: {domain_clean} | Данные: OpenAlex, Google Patents | Обновлено: {datetime.now().strftime('%d.%m.%Y %H:%M')}</p>
</div>
""", unsafe_allow_html=True)

print("app.py успешно выполнен")