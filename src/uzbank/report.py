"""Generate the research memo and a self-contained interactive HTML report."""
from __future__ import annotations

from html import escape
import json
import pandas as pd
import plotly.express as px
from .fetch import ROOT
from .findings import completed_findings
from .research_charts import research_charts


def report(root=ROOT):
    p = root / "data/processed"
    banks = pd.read_csv(p / "bank_month_metrics.csv", parse_dates=["date"])
    sector = pd.read_csv(p / "sector_month_metrics.csv", parse_dates=["date"]).sort_values("date")
    manifest = json.loads((root / "data/sources.json").read_text(encoding="utf-8"))
    summary = json.loads((p / "build_summary.json").read_text(encoding="utf-8"))
    first, last = sector.iloc[0], sector.iloc[-1]
    current = banks[banks.date == last.date]
    gainers = current.nlargest(5, "deposit_share_yoy_pp")
    start, end = first.date.strftime("%d.%m.%Y"), last.date.strftime("%d.%m.%Y")
    executive, findings = completed_findings(root)
    evidence = [s for s in manifest if s["date"] in {"2024-01-01", "2025-01-01", "2026-01-01"}]
    research = json.loads((root / "data/research/sources.json").read_text(encoding="utf-8"))
    evidence += research
    header = f"# Банковский сектор Узбекистана: результаты исследования\n\nПериод: **{start} — {end}**. Годовое сравнение: **2025 год**.\n\n"
    header += "## Главный результат\n\n" + executive + "\n\n"
    sections = []
    for i, item in enumerate(findings, 1):
        refs = " · ".join(f"[{s['label']}]({s['url']})" for s in item['sources'])
        sections.append(f"## {i}. {item['title']}\n\n{item['evidence']}\n\n**Вывод.** {item['conclusion']}\n\nИсточники: {refs}")
    memo = header + "\n\n".join(sections)
    memo += f"\n\n## Основа расчётов\n\n{summary['bank_observations']} наблюдений, {summary['source_publications']} публикаций ЦБ и {summary['checks_passed']} успешных сверок. "
    memo += "Суммы представлены в номинальных сумах; реальный рост депозитного остатка отдельно рассчитан с дефлятором ИПЦ 7,3%. "
    memo += "Остатки валютных депозитов учитываются в опубликованном сумовом эквиваленте. Клиентский, валютный и срочный разрезы — три самостоятельных разложения одного прироста. "
    memo += "Разница в 1 млрд сум между приростом итога и суммой клиентских компонентов соответствует округлению исходных таблиц. "
    memo += "Выводы о LCR и NSFR относятся к сектору в целом. Балансовый и регулятивный капитал представлены раздельно. "
    memo += "Формулы и порядок разложения государственной доли раскрыты в [методике](../docs/methodology.md).\n\n"
    memo += "## Воспроизводимость\n\n`python -m uzbank.build` → `python -m uzbank.report` → `python -m pytest -q`. "
    memo += "Расчёты: [основные витрины](../sql/01_marts.sql), [витрины исследования](../sql/03_completed_research.sql), "
    memo += "[запросы к результатам](../sql/02_research_questions.sql). "
    memo += "Реестры источников: [50 месячных публикаций](../data/sources.json) и [6 дополнительных публикаций](../data/research/sources.json).\n"
    out = root / "reports"
    out.mkdir(exist_ok=True)
    (out / "findings.ru.md").write_text(memo, encoding="utf-8", newline="\n")
    charts = []
    trends = sector[["date","assets","loans","deposits"]].copy()
    for field in ("assets","loans","deposits"):
        trends[field] /= 1000
    trends = trends.rename(columns={"assets":"Активы","loans":"Кредиты","deposits":"Депозиты"})
    charts.append(("Рост балансовых показателей", px.line(trends,x="date",y=["Активы","Кредиты","Депозиты"],color_discrete_sequence=["#167667","#496FBA","#D19B42"],labels={"value":"трлн сум","date":"","variable":""})))
    charts.append(("Концентрация активов: доля топ-5",px.line(sector,x="date",y="cr5_pct",markers=True,color_discrete_sequence=["#496FBA"],labels={"cr5_pct":"% активов","date":""})))
    top = current.nlargest(10,"assets").sort_values("assets").assign(value=lambda x:x.assets/1000)
    charts.append((f"Крупнейшие банки на {end}",px.bar(top,x="value",y="bank_name",orientation="h",color_discrete_sequence=["#167667"],labels={"value":"Активы, трлн сум","bank_name":""})))
    leader_chart = gainers.sort_values("deposit_share_yoy_pp")
    charts.append(("Лидеры прироста доли депозитов за последний год",px.bar(leader_chart,x="deposit_share_yoy_pp",y="bank_name",orientation="h",color_discrete_sequence=["#496FBA"],labels={"deposit_share_yoy_pp":"Изменение доли, п.п.","bank_name":""})))
    charts += research_charts(root)
    chart_html = []
    for i,(title,fig) in enumerate(charts):
        fig.update_layout(template="plotly_white",height=380,margin=dict(l=15,r=25,t=20,b=35),font=dict(family="Arial",color="#152A37"),hovermode="x unified")
        if i < 4:
            fig.update_layout(legend=dict(orientation="h",y=1.12))
        elif i == 4:
            fig.update_layout(height=460, margin=dict(l=15,r=25,t=20,b=120))
        fig.update_xaxes(showgrid=False)
        fig.update_yaxes(gridcolor="#E6EBEF")
        chart_html.append(f"<section class='chart'><h2>{escape(title)}</h2>"+fig.to_html(full_html=False,include_plotlyjs=True if i==0 else False,div_id=f"chart-{i}",config={"displayModeBar":False,"responsive":True})+"</section>")
    cards = [("Активы",f"{last.assets/1000:.1f}","трлн сум"),("Депозиты",f"{last.deposits/1000:.1f}",f"+{last.deposits_yoy_pct:.1f}% г/г"),("Кредиты",f"{last.loans/1000:.1f}",f"+{last.loans_yoy_pct:.1f}% г/г"),("Доля топ-5",f"{last.cr5_pct:.1f}%","по активам")]
    html = """<!DOCTYPE html><html lang='ru'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>
<title>Uzbekistan Banking Monitor</title><style>
*{box-sizing:border-box}body{margin:0;background:#f4f7f8;color:#152a37;font:16px/1.6 Arial,sans-serif}main{max-width:1320px;margin:auto;padding:48px 32px}h1{font-size:44px;line-height:1.15;letter-spacing:-1.5px;margin:14px 0}h2{font-size:20px;line-height:1.4;margin:0 0 18px}.eyebrow{color:#167667;font-size:12px;letter-spacing:2px;font-weight:bold}.sub{color:#61737f;max-width:900px}.cards{display:grid;grid-template-columns:repeat(4,1fr);gap:16px;margin:32px 0}.card,.chart{background:white;border:1px solid #dfe7ec;border-radius:14px;padding:22px}.card strong{display:block;font-size:36px;letter-spacing:-1px}.card small{color:#167667}.charts{display:grid;grid-template-columns:1fr 1fr;gap:22px}.findings{margin-top:42px;max-width:1000px}.finding{padding:20px 0;border-top:1px solid #d7e1e7}.finding p{margin:0}.finding h2{margin-bottom:8px}a{color:#167667}footer{margin-top:32px;padding-top:22px;border-top:1px solid #d7e1e7;color:#61737f;font-size:13px}@media(max-width:800px){main{padding:24px 16px}h1{font-size:30px}.cards{grid-template-columns:1fr 1fr}.charts{grid-template-columns:1fr}.card strong{font-size:28px}.chart{min-width:0;padding:12px}}
</style></head><body><main><div class='eyebrow'>UZBEKISTAN / BANKING MONITOR</div><h1>Банки Узбекистана в цифрах</h1>"""
    html += f"<p class='sub'>Рост, концентрация и структура фондирования. {start} — {end}. Историческое исследование на открытых данных Центрального банка.</p><div class='cards'>"
    html += "".join(f"<div class='card'>{label}<strong>{value}</strong><small>{note}</small></div>" for label,value,note in cards)
    html += f"</div><section class='chart' style='margin-bottom:24px'><h2>Главный результат</h2><p>{escape(executive)}</p></section>"
    html += "<div class='charts'>"+"".join(chart_html)+"</div><div class='findings'><h2>Семь выводов исследования</h2>"
    for i, item in enumerate(findings, 1):
        refs = " · ".join(f"<a href='{escape(s['url'])}'>{escape(s['label'])}</a>" for s in item['sources'])
        html += f"<article class='finding'><h2>{i:02d}. {escape(item['title'])}</h2><p>{escape(item['evidence'])}</p>"
        html += f"<p style='margin-top:12px'><strong>Вывод.</strong> {escape(item['conclusion'])}</p><p class='sub' style='font-size:13px;margin-top:12px'>Источники: {refs}</p></article>"
    html += f"</div><footer>{summary['bank_observations']} наблюдений · {summary['source_publications']} публикаций · {summary['checks_passed']} сверок. "
    html += "Суммы номинальные; реальный рост депозитов отдельно рассчитан по ИПЦ. Разрезы прироста независимы; LCR и NSFR характеризуют сектор в целом.<p>Источники: "
    html += " · ".join(f"<a href='{escape(s['url'])}'>{s.get('date', '2025–2026')} / {s['kind']}</a>" for s in evidence)
    html += "</p>Графики интерактивны и работают без интернета. Полный дашборд с фильтрами: <code>python -m streamlit run app.py</code>.</footer></main></body></html>"
    (out / "overview.html").write_text(html, encoding="utf-8")
    print(f"Generated {out / 'findings.ru.md'} and {out / 'overview.html'}")


if __name__ == "__main__":
    report()
