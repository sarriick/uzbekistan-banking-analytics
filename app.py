"""Streamlit banking monitor. Run: python -m streamlit run app.py."""
from pathlib import Path
import json

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from uzbank.analytics import indexed_series, latest_at
from uzbank.findings import completed_findings
from uzbank.research_charts import research_charts

ROOT = Path(__file__).resolve().parent
PROCESSED = ROOT / "data/processed"
TEAL, BLUE, AMBER, INK = "#167667", "#496FBA", "#D19B42", "#152A37"
PALETTE = [TEAL, BLUE, AMBER, "#8870AA", "#CB7260", "#458C9E"]
GROUPS = {"state": "С государственной долей", "other": "Остальные банки"}
METRICS = {"Активы": "assets", "Кредиты": "loans", "Депозиты": "deposits", "Капитал": "capital"}

st.set_page_config(page_title="Uzbekistan Banking Monitor", page_icon="📊", layout="wide")
st.markdown("""<style>
.block-container {max-width:1440px; padding-top:4.5rem; padding-bottom:3rem;}
h1 {letter-spacing:-1.6px; font-weight:700 !important;}
h2,h3 {letter-spacing:-.5px;}
[data-testid="stMetric"] {background:#fff; border:1px solid #e0e7eb; border-radius:12px; padding:18px 20px; min-height:142px;}
[data-testid="stMetricValue"] {font-variant-numeric:tabular-nums;}
.eyebrow {font-size:12px; letter-spacing:2px; font-weight:700; color:#167667; margin-bottom:8px;}
.context {color:#60717e; font-size:15px; margin-bottom:24px;}
.note {color:#60717e; font-size:12px; margin-top:12px;}
</style>""", unsafe_allow_html=True)


@st.cache_data
def load_data():
    banks = pd.read_csv(PROCESSED / "bank_month_metrics.csv", parse_dates=["date"])
    sector = pd.read_csv(PROCESSED / "sector_month_metrics.csv", parse_dates=["date"])
    groups = pd.read_csv(PROCESSED / "ownership_month_metrics.csv", parse_dates=["date"])
    summary = json.loads((PROCESSED / "build_summary.json").read_text(encoding="utf-8"))
    return banks, sector, groups, summary


def chart(fig, height=350, legend_below=False):
    fig.update_layout(
        height=height, margin=dict(l=10, r=20, t=18, b=30), paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)", font=dict(family="Arial, sans-serif", color=INK, size=12),
        legend=dict(orientation="h", y=1.12, x=0, title_text=""),
        hoverlabel=dict(bgcolor="white"), hovermode="x unified",
    )
    fig.update_xaxes(showgrid=False, zeroline=False)
    if fig.layout.xaxis.title.text == "date":
        fig.update_xaxes(title=None)
    fig.update_yaxes(gridcolor="#E4EAEE", zeroline=False)
    if legend_below:
        fig.update_layout(legend=dict(orientation="h", y=-.3), margin=dict(l=10,r=20,t=18,b=120))
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})


def pct(value, suffix="%"):
    return "Нет базы сравнения" if pd.isna(value) else f"{value:+.1f}{suffix}"


if not (PROCESSED / "bank_month_metrics.csv").exists():
    st.error("Данные ещё не собраны. Выполните: python -m uzbank.build")
    st.stop()

banks, sector, groups, summary = load_data()
st.markdown('<div class="eyebrow">UZBEKISTAN / BANKING MONITOR</div>', unsafe_allow_html=True)
st.title("Банки Узбекистана в цифрах")
st.markdown('<div class="context">Рост, доли рынка и структура фондирования на основе открытой статистики Центрального банка.</div>', unsafe_allow_html=True)

f1, f2, f3 = st.columns([1.1, 1.25, 2.1])
dates = sorted(banks.date.unique())
as_of = f1.selectbox("Отчётная дата", dates, index=len(dates)-1,
                     format_func=lambda d: pd.Timestamp(d).strftime("%d.%m.%Y"), key="as_of")
metric_name = f2.selectbox("Показатель для графиков", list(METRICS), key="metric")
metric = METRICS[metric_name]
f3.caption(f"{summary['snapshots']} месячных срезов · {summary['source_publications']} публикаций ЦБ\n\n"
           "01.01.2024 — 01.01.2026. Исторический срез, не текущий мониторинг.")
snapshot = latest_at(banks, as_of)
now = latest_at(sector, as_of).iloc[0]
history = sector[sector.date <= as_of]
cards = st.columns(4)
cards[0].metric("Активы, трлн сум", f"{now.assets/1000:,.1f}", pct(now.assets_yoy_pct)+" г/г")
cards[1].metric("Депозиты, трлн сум", f"{now.deposits/1000:,.1f}", pct(now.deposits_yoy_pct)+" г/г")
cards[2].metric("Кредиты, трлн сум", f"{now.loans/1000:,.1f}", pct(now.loans_yoy_pct)+" г/г")
cards[3].metric("Доля 5 крупнейших по активам", f"{now.cr5_pct:.1f}%", help=f"Всего на выбранную дату: {int(now.bank_count)} банков.")
st.write("")
overview, compare, funding, research, evidence = st.tabs(["Обзор рынка", "Сравнение банков", "Кредиты и депозиты", "Выводы исследования", "Данные и методика"])

with overview:
    left, right = st.columns([1.35, 1])
    with left:
        st.subheader(f"{metric_name}: динамика сектора")
        fig = px.area(history.assign(value=history[metric]/1000), x="date", y="value", color_discrete_sequence=[TEAL])
        fig.update_traces(line_width=3, fillcolor="rgba(22,118,103,.10)", hovertemplate="%{y:.1f} трлн сум<extra></extra>")
        fig.update_yaxes(title="трлн сум", rangemode="tozero")
        chart(fig)
    with right:
        st.subheader(f"Крупнейшие банки: {metric_name.lower()}")
        top = snapshot.nlargest(8, metric).sort_values(metric).assign(value=lambda d: d[metric]/1000)
        fig = px.bar(top, y="bank_name", x="value", orientation="h", color_discrete_sequence=[TEAL], text="value")
        fig.update_traces(texttemplate="%{text:.1f}", textposition="outside", cliponaxis=False,
                          hovertemplate="%{y}<br>%{x:.1f} трлн сум<extra></extra>")
        fig.update_layout(hovermode="closest")
        fig.update_yaxes(title=None)
        fig.update_xaxes(title="трлн сум", range=[0, top.value.max()*1.2])
        chart(fig)
    a, b = st.columns(2)
    with a:
        st.subheader("Как менялась концентрация")
        fig = px.line(history, x="date", y="cr5_pct", color_discrete_sequence=[BLUE], markers=True)
        fig.update_yaxes(title="Доля топ-5 по активам, %")
        chart(fig, 270)
        st.caption("Состав топ-5 пересчитывается на каждую дату. Доли для CR5 и HHI рассчитаны от суммы активов отдельных банков.")
    with b:
        st.subheader("Структура рынка по собственности")
        g = groups[(groups.date <= as_of)].copy()
        # Ownership mart has no capital; use the bank facts for this measure.
        if metric == "capital":
            g = banks[banks.date <= as_of].groupby(["date", "ownership"], as_index=False)[metric].sum()
        g["Доля, %"] = 100*g[metric]/g.groupby("date")[metric].transform("sum")
        g["Группа"] = g.ownership.map(GROUPS)
        fig = px.area(g, x="date", y="Доля, %", color="Группа", color_discrete_map={GROUPS['state']: BLUE, GROUPS['other']: TEAL})
        fig.update_yaxes(range=[0, 100])
        chart(fig, 270)
        st.caption("Классификация ЦБ на каждую дату. За 2024–2025 годы изменение объёмов активов снизило государственную долю на 4,21 п.п., переход Poytaxt Bank — на 0,06 п.п. Подробный расчёт — во вкладке «Выводы исследования».")

with compare:
    chosen = st.multiselect("Выберите банки", sorted(banks.bank_name.unique()),
                            default=["Kapitalbank", "TBC Bank Uzbekistan", "National Bank of Uzbekistan"], key="banks")
    mode = st.radio("Масштаб", ["трлн сум", "Индекс: первая доступная дата = 100"], horizontal=True, key="scale")
    comparison = banks[(banks.bank_name.isin(chosen)) & (banks.date <= as_of)].copy()
    if comparison.empty:
        st.info("Выберите хотя бы один банк с данными на выбранный период.")
    else:
        comparison = indexed_series(comparison, metric)
        comparison["value"] = comparison[metric]/1000 if mode == "трлн сум" else comparison["index"]
        fig = px.line(comparison, x="date", y="value", color="bank_name", markers=True, color_discrete_sequence=PALETTE)
        fig.update_traces(connectgaps=False)
        fig.update_yaxes(title=mode)
        chart(fig, 400)
        if mode != "трлн сум":
            st.caption("База каждого банка — его первая доступная дата в наборе. При нулевой базе индекс не рассчитывается. Даты начала могут различаться.")
    st.subheader("Показатели выбранных банков")
    columns = ["bank_name", "assets", "loans", "deposits", "assets_yoy_pct", "deposits_yoy_pct", "asset_share_pct", "asset_share_yoy_pp"]
    table = snapshot[snapshot.bank_name.isin(chosen)][columns]
    st.dataframe(table.rename(columns={"bank_name":"Банк", "assets":"Активы, млрд", "loans":"Кредиты, млрд", "deposits":"Депозиты, млрд",
        "assets_yoy_pct":"Рост активов г/г, %", "deposits_yoy_pct":"Рост депозитов г/г, %", "asset_share_pct":"Доля активов, %", "asset_share_yoy_pp":"Изменение доли г/г, п.п."}),
        hide_index=True, width="stretch")
    st.caption("Доли всегда рассчитаны относительно всего рынка. Выбор банков не меняет знаменатель. Пустое значение г/г означает отсутствие сопоставимой ненулевой базы год назад.")

with funding:
    st.subheader("Кредиты относительно депозитной базы")
    positive = snapshot[(snapshot.deposits > 0) & (snapshot.loans > 0)].copy()
    positive["Группа"] = positive.ownership.map(GROUPS)
    positive["Депозиты, трлн сум"] = positive.deposits/1000
    positive["Кредиты, трлн сум"] = positive.loans/1000
    fig = px.scatter(positive, x="Депозиты, трлн сум", y="Кредиты, трлн сум", size="assets", color="Группа",
                     hover_name="bank_name", size_max=48, color_discrete_map={GROUPS['state']: BLUE, GROUPS['other']: TEAL},
                     hover_data={"assets":":,.0f", "loan_to_deposit_pct":":.1f"})
    limit = max(positive["Депозиты, трлн сум"].max(), positive["Кредиты, трлн сум"].max())*1.04
    fig.add_trace(go.Scatter(x=[0,limit], y=[0,limit], mode="lines", line=dict(color="#A4AFB6", dash="dot"), name="Кредиты = депозиты", hoverinfo="skip"))
    fig.update_layout(hovermode="closest")
    chart(fig, 410)
    excluded = len(snapshot)-len(positive)
    st.caption(f"Размер круга — активы. Не показано банков с нулём кредитов или депозитов: {excluded}. "
               "Структура обязательств раскрыта ниже. Нормативы LCR и NSFR приведены во вкладке «Выводы исследования».")
    st.subheader("Состав обязательств по группам банков")
    mix = pd.read_csv(PROCESSED / "funding_structure.csv", parse_dates=["date"])
    mix = mix[mix.date == as_of].copy()
    mix["Группа"] = mix.ownership.map(GROUPS)
    mix = mix.rename(columns={"deposit_liability_share_pct":"Депозиты", "other_liability_share_pct":"Прочие обязательства"})
    fig = px.bar(mix, x="Группа", y=["Депозиты", "Прочие обязательства"], text_auto=".1f",
                 color_discrete_sequence=[TEAL, BLUE], labels={"value":"Доля обязательств, %", "variable":""})
    chart(fig, 300)
    st.caption("Обязательства = активы − балансовый капитал. Прочие обязательства = обязательства − депозиты. Доли рассчитаны по суммам каждой группы.")
    a,b = st.columns(2)
    for container, label, component, total in [(a,"Депозиты физических лиц","retail_deposits","deposits"), (b,"Кредиты физическим лицам","retail_loans","loans")]:
        with container:
            st.subheader(label)
            top = snapshot.nlargest(10, component).sort_values(component).copy()
            top["Физические лица"] = top[component]/1000
            top["Юридические лица"] = top["corporate_"+total]/1000
            fig = px.bar(top, y="bank_name", x=["Физические лица","Юридические лица"], orientation="h", color_discrete_sequence=[TEAL,"#C8D7E0"])
            fig.update_yaxes(title=None)
            fig.update_xaxes(title="трлн сум")
            chart(fig, 390)

with research:
    st.subheader("Результаты исследования 2024–2025")
    st.caption("Фиксированный период: 01.01.2024 — 01.01.2026. Разложения прироста депозитов и показатели ликвидности сравнивают 01.01.2025 и 01.01.2026. Фильтры других вкладок не меняют период исследования.")
    executive, findings = completed_findings(ROOT)
    st.success(executive)
    a, b = st.columns(2)
    for i, ((title, fig), container) in enumerate(zip(research_charts(ROOT), [a, b])):
        with container:
            st.subheader(title)
            chart(fig, 460, legend_below=i == 0)
    st.caption("Клиенты, валюта и срок — самостоятельные разрезы одного прироста депозитов. В каждом разрезе сумма вкладов составляет около 100%; отклонение клиентского разреза связано с округлением до млрд сум.")
    for i, item in enumerate(findings, 1):
        st.subheader(f"{i}. {item['title']}")
        st.write(item["evidence"])
        st.markdown(f"**Вывод.** {item['conclusion']}")
        with st.expander(f"Источники к выводу {i}"):
            for source in item["sources"]:
                st.markdown(f"[{source['label']}]({source['url']})")

with evidence:
    st.subheader("Проверяемые исходные данные")
    st.write(f"{summary['bank_observations']} наблюдений «банк × месяц», {summary['distinct_banks']} банков за весь период. "
             f"Успешно пройдено {summary['checks_passed']} сверок с опубликованными итогами ЦБ.")
    st.markdown("""- Денежные величины в выгрузке — **млрд сум**, на графиках — **трлн сум**.
- Дата — состояние баланса на первое число месяца. Балансовые остатки нельзя суммировать по месяцам.
- Годовой рост сравнивает точную дату с датой год назад. Пропуски и нулевая база не заменяются нулями роста.
- Базовые суммы номинальные. Реальный рост совокупного депозитного остатка за 2025 год рассчитан отдельно с ИПЦ 7,3%: 26,0%.
- Валютные остатки представлены в сумовом эквиваленте ЦБ; клиентский, валютный и срочный разрезы анализируются отдельно.
- Периметр — статистика ЦБ по коммерческим банкам. Балансовый капитал используется в структуре обязательств, регулятивный — в отдельной публикации о достаточности капитала.
- Опубликованные суммы округлены. Допуск сверки суммы N банков: (N + 1) / 2 млрд сум.
- Smart Bank и Open Bank объединены по подтверждённому переименованию. Исходные названия сохранены в выгрузке.
""")
    st.download_button("Скачать данные за выбранную дату (CSV)", snapshot.to_csv(index=False).encode("utf-8-sig"),
                        file_name=f"uzbekistan_banks_{pd.Timestamp(as_of):%Y-%m-%d}.csv", mime="text/csv")
    st.download_button("Скачать все месяцы (CSV)", banks.to_csv(index=False).encode("utf-8-sig"), file_name="uzbekistan_bank_month.csv", mime="text/csv")
    sources = json.loads((ROOT / "data/sources.json").read_text(encoding="utf-8"))
    selected_sources = [s for s in sources if s['date']==pd.Timestamp(as_of).strftime('%Y-%m-%d')]
    for source in selected_sources:
        st.markdown(f"[{source['title']}]({source['url']})")
    with st.expander("Дополнительные источники завершённого исследования"):
        for source in json.loads((ROOT / "data/research/sources.json").read_text(encoding="utf-8")):
            st.markdown(f"[{source['title']}]({source['url']})")
        st.dataframe(pd.read_csv(PROCESSED / "research_checks.csv"), hide_index=True, width="stretch")
    with st.expander("Результаты сверок"):
        checks = pd.read_csv(PROCESSED / "quality_checks.csv")
        st.dataframe(checks[checks.date==pd.Timestamp(as_of).strftime('%Y-%m-%d')], hide_index=True, width="stretch")

st.markdown('<div class="note">Источник: Центральный банк Республики Узбекистан · Аналитический проект на открытых данных · Исторический период 2024–2025</div>', unsafe_allow_html=True)
