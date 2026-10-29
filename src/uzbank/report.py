"""Generate the research memo and a self-contained interactive HTML report."""
from __future__ import annotations

from html import escape
import json
import pandas as pd
import plotly.express as px
from .fetch import ROOT


def report(root=ROOT):
    p = root / "data/processed"
    banks = pd.read_csv(p / "bank_month_metrics.csv", parse_dates=["date"])
    sector = pd.read_csv(p / "sector_month_metrics.csv", parse_dates=["date"]).sort_values("date")
    groups = pd.read_csv(p / "ownership_month_metrics.csv", parse_dates=["date"])
    manifest = json.loads((root / "data/sources.json").read_text(encoding="utf-8"))
    summary = json.loads((p / "build_summary.json").read_text(encoding="utf-8"))
    first, last = sector.iloc[0], sector.iloc[-1]
    current = banks[banks.date == last.date]
    gainers = current.nlargest(5, "deposit_share_yoy_pp")
    retail_leader = current.nlargest(1, "retail_deposits").iloc[0]
    owned = groups[groups.date == last.date].set_index("ownership")
    start, end = first.date.strftime("%d.%m.%Y"), last.date.strftime("%d.%m.%Y")
    findings = [
        ("Депозиты растут быстрее кредитов",
         f"За год до {end} депозиты выросли на {last.deposits_yoy_pct:.1f}%, кредиты — на {last.loans_yoy_pct:.1f}%, активы — на {last.assets_yoy_pct:.1f}%. "
         f"На конец периода это {last.deposits/1000:.1f}, {last.loans/1000:.1f} и {last.assets/1000:.1f} трлн сум соответственно. "
         "Следующий вопрос для анализа — какие ставки, валюты и типы клиентов обеспечили прирост депозитов. Этих разрезов в текущем наборе нет."),
        ("Соотношение кредитов и депозитов снизилось",
         f"За весь период показатель снизился с {first.loan_to_deposit_pct:.1f}% до {last.loan_to_deposit_pct:.1f}% "
         f"({last.loan_to_deposit_pct-first.loan_to_deposit_pct:+.1f} п.п.). Депозитная база увеличилась относительно кредитного портфеля. "
         "Это не доказывает улучшение ликвидности: здесь не учитываются сроки, валюты, заимствования и другие источники фондирования."),
        ("Доля крупнейшей пятёрки уменьшилась",
         f"CR5 по активам снизился с {first.cr5_pct:.1f}% до {last.cr5_pct:.1f}% "
         f"({last.cr5_pct-first.cr5_pct:+.1f} п.п.), HHI — с {first.hhi:.0f} до {last.hhi:.0f}. "
         "Распределение активов стало менее концентрированным по этим двум показателям. Состав топ-5 пересчитан на каждую дату. "
         "Из этих величин нельзя отдельно вывести интенсивность ценовой конкуренции."),
        ("Доля банков с государственной долей снизилась",
         f"Их доля в активах сектора изменилась с {first.state_asset_share_pct:.1f}% до {last.state_asset_share_pct:.1f}% "
         f"({last.state_asset_share_pct-first.state_asset_share_pct:+.1f} п.п.). Группы взяты из каждой публикации ЦБ. "
         "Внутри периода Poytaxt Bank меняет группу. Поэтому изменение групповой доли нельзя полностью приписать органическому росту."),
        ("Лидеры прироста доли депозитов не совпадают с крупнейшими банками",
         "За последний год наибольший прирост доли депозитов показали "
         + ", ".join(f"{r.bank_name} ({r.deposit_share_yoy_pp:+.2f} п.п.)" for r in gainers.head(3).itertuples())
         + ". Для сравнения используются процентные пункты рыночной доли: большие темпы роста небольшого банка сами по себе не означают большой вклад в рынок."),
        ("Структура фондирования групп заметно различается",
         f"На {end} кредиты к депозитам составляют {owned.loc['state','loan_to_deposit_pct']:.1f}% у банков с государственной долей "
         f"и {owned.loc['other','loan_to_deposit_pct']:.1f}% у остальных банков. Это отношения сумм, а не среднее индивидуальных коэффициентов. "
         "Различие требует изучения бизнес-моделей и привлечённых заимствований, прежде чем делать выводы о риске."),
        ("Крупнейшая база депозитов физических лиц — у Kapitalbank",
         f"На последнюю дату {retail_leader.bank_name} имеет {retail_leader.retail_deposits/1000:.1f} трлн сум депозитов физических лиц, "
         f"или {100*retail_leader.retail_deposits/last.retail_deposits:.1f}% таких депозитов в секторе. "
         f"Они составляют {retail_leader.retail_deposit_share_pct:.1f}% депозитов самого банка. Объём депозитов не показывает количество уникальных клиентов."),
    ]
    # The period and all numerical statements are computed from the same SQL marts.
    findings[-1] = (f"Крупнейшая база депозитов физических лиц — у {retail_leader.bank_name}", findings[-1][1])
    evidence = [s for s in manifest if s["date"] in {first.date.strftime("%Y-%m-%d"),last.date.strftime("%Y-%m-%d"), (last.date-pd.DateOffset(years=1)).strftime("%Y-%m-%d")}]
    source_md = "\n".join(f"- [{s['date']} — {s['kind']}]({s['url']})" for s in evidence)
    header = f"# Банковский сектор Узбекистана: рост, конкуренция и фондирование\n\nПериод: **{start} — {end}**. Последнее годовое сравнение: **2025 год**.\n\n"
    header += "Исследовательский вопрос: какие банки увеличивают долю рынка и как меняется соотношение кредитов и депозитов?\n\n"
    memo = header + "\n\n".join(f"## {i}. {title}\n\n{text}" for i,(title,text) in enumerate(findings,1))
    memo += f"\n\n## Проверки и ограничения\n\n{summary['bank_observations']} наблюдений, {summary['source_publications']} исходных публикаций, {summary['checks_passed']} успешных сверок с итогами. "
    memo += "Суммы номинальные, в национальной валюте. Рост не скорректирован на инфляцию и валютную переоценку. Остатки на отчётные даты не равны оборотам. "
    memo += "Таблицы ЦБ округлены до млрд сум. Коэффициенты и доли пересчитаны из сумм, а не из округлённых процентов источника. "
    memo += "Причины наблюдаемых изменений и надёжность банков по этим данным не устанавливаются.\n\n"
    memo += "## Как воспроизвести\n\n`python -m uzbank.build` → `python -m uzbank.report`. "
    memo += "Расчёты: [SQL-витрины](../sql/01_marts.sql), [исследовательские запросы](../sql/02_research_questions.sql). "
    memo += "[Полный реестр источников](../data/sources.json).\n\n## Основные источники\n\n" + source_md + "\n"
    out = root / "reports"
    out.mkdir(exist_ok=True)
    (out / "findings.ru.md").write_text(memo, encoding="utf-8")
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
    chart_html = []
    for i,(title,fig) in enumerate(charts):
        fig.update_layout(template="plotly_white",height=380,margin=dict(l=15,r=25,t=20,b=35),font=dict(family="Arial",color="#152A37"),legend=dict(orientation="h",y=1.12),hovermode="x unified")
        fig.update_xaxes(showgrid=False)
        fig.update_yaxes(gridcolor="#E6EBEF")
        chart_html.append(f"<section class='chart'><h2>{escape(title)}</h2>"+fig.to_html(full_html=False,include_plotlyjs=True if i==0 else False,div_id=f"chart-{i}",config={"displayModeBar":False,"responsive":True})+"</section>")
    cards = [("Активы",f"{last.assets/1000:.1f}","трлн сум"),("Депозиты",f"{last.deposits/1000:.1f}",f"+{last.deposits_yoy_pct:.1f}% г/г"),("Кредиты",f"{last.loans/1000:.1f}",f"+{last.loans_yoy_pct:.1f}% г/г"),("Доля топ-5",f"{last.cr5_pct:.1f}%","по активам")]
    html = """<!DOCTYPE html><html lang='ru'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>
<title>Uzbekistan Banking Monitor</title><style>
*{box-sizing:border-box}body{margin:0;background:#f4f7f8;color:#152a37;font:16px/1.6 Arial,sans-serif}main{max-width:1320px;margin:auto;padding:48px 32px}h1{font-size:44px;line-height:1.15;letter-spacing:-1.5px;margin:14px 0}h2{font-size:20px;line-height:1.4;margin:0 0 18px}.eyebrow{color:#167667;font-size:12px;letter-spacing:2px;font-weight:bold}.sub{color:#61737f;max-width:900px}.cards{display:grid;grid-template-columns:repeat(4,1fr);gap:16px;margin:32px 0}.card,.chart{background:white;border:1px solid #dfe7ec;border-radius:14px;padding:22px}.card strong{display:block;font-size:36px;letter-spacing:-1px}.card small{color:#167667}.charts{display:grid;grid-template-columns:1fr 1fr;gap:22px}.findings{margin-top:42px;max-width:1000px}.finding{padding:20px 0;border-top:1px solid #d7e1e7}.finding p{margin:0}.finding h2{margin-bottom:8px}a{color:#167667}footer{margin-top:32px;padding-top:22px;border-top:1px solid #d7e1e7;color:#61737f;font-size:13px}@media(max-width:800px){main{padding:24px 16px}h1{font-size:30px}.cards{grid-template-columns:1fr 1fr}.charts{grid-template-columns:1fr}.card strong{font-size:28px}.chart{min-width:0;padding:12px}}
</style></head><body><main><div class='eyebrow'>UZBEKISTAN / BANKING MONITOR</div><h1>Банки Узбекистана в цифрах</h1>"""
    html += f"<p class='sub'>Рост, конкуренция и структура фондирования. {start} — {end}. Историческое исследование на открытых данных Центрального банка.</p><div class='cards'>"
    html += "".join(f"<div class='card'>{label}<strong>{value}</strong><small>{note}</small></div>" for label,value,note in cards)
    html += "</div><div class='charts'>"+"".join(chart_html)+"</div><div class='findings'><h2>Что показывают данные</h2>"
    html += "".join(f"<article class='finding'><h2>{i:02d}. {escape(title)}</h2><p>{escape(text)}</p></article>" for i,(title,text) in enumerate(findings,1))
    html += f"</div><footer>{summary['bank_observations']} наблюдений · {summary['source_publications']} публикаций · {summary['checks_passed']} сверок. "
    html += "Номинальные суммы. Причины изменений и риск банков из этих показателей не следуют.<p>Источники: "
    html += " · ".join(f"<a href='{escape(s['url'])}'>{s['date']} / {s['kind']}</a>" for s in evidence)
    html += "</p>Графики интерактивны и работают без интернета. Полный дашборд с фильтрами: <code>python -m streamlit run app.py</code>.</footer></main></body></html>"
    (out / "overview.html").write_text(html, encoding="utf-8")
    print(f"Generated {out / 'findings.ru.md'} and {out / 'overview.html'}")


if __name__ == "__main__":
    report()
