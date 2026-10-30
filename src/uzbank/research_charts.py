"""Research charts shared by the standalone report and Streamlit."""
import pandas as pd
import plotly.express as px
from .fetch import ROOT


def research_charts(root=ROOT):
    p = root / "data/processed"
    bridge = pd.read_csv(p / "deposit_growth_bridge.csv")
    labels = {"local": "Сумовые", "foreign": "Валютные", "individuals": "Физические лица",
              "legal_entities": "Юридические лица", "term": "Срочная часть", "demand": "До востребования"}
    bridge["Разрез"] = bridge.dimension.map({"currency": "Валюта", "customer": "Клиенты", "maturity": "Срок"})
    bridge["Компонент"] = bridge.component.map(labels)
    fig = px.bar(bridge, x="contribution_pct", y="Разрез", color="Компонент", orientation="h", text="contribution_pct",
                 labels={"contribution_pct": "Вклад в прирост депозитов, %"},
                 color_discrete_sequence=["#C8D7E0", "#167667", "#496FBA", "#D19B42", "#A7BDD8", "#8870AA"])
    fig.update_traces(texttemplate="%{text:.1f}%", textposition="inside")
    fig.update_layout(barmode="stack", legend=dict(orientation="h", y=-.25, title_text=""))
    context = pd.read_csv(p / "sector_research.csv")
    context["Дата"] = pd.to_datetime(context.date).dt.strftime("%d.%m.%Y")
    liquidity = context.rename(columns={"lcr_pct": "LCR", "nsfr_pct": "NSFR"})
    liquid = px.bar(liquidity, x="Дата", y=["LCR", "NSFR"], barmode="group", text_auto=".1f",
                    labels={"value": "%", "variable": "Показатель"}, color_discrete_sequence=["#167667", "#496FBA"])
    liquid.add_hline(y=100, line_dash="dot", line_color="#8D5C20", annotation_text="Минимум ЦБ: 100%", annotation_position="top left")
    liquid.update_yaxes(range=[0, 245])
    return [("Источники прироста депозитов в 2025 году", fig), ("Ликвидность и стабильное фондирование", liquid)]
