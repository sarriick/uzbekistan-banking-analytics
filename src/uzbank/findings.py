"""Completed, source-linked conclusions shared by the memo and dashboard."""
from __future__ import annotations

import json
import pandas as pd
from .fetch import ROOT


def completed_findings(root=ROOT):
    p = root / "data/processed"
    sector = pd.read_csv(p / "sector_month_metrics.csv").sort_values("date")
    banks = pd.read_csv(p / "bank_month_metrics.csv")
    context = pd.read_csv(p / "sector_research.csv").sort_values("date")
    bridge = pd.read_csv(p / "deposit_growth_bridge.csv").set_index(["dimension", "component"])
    state = pd.read_csv(p / "state_share_bridge.csv").iloc[0]
    top5 = pd.read_csv(p / "initial_top5_growth.csv").set_index("cohort")
    funding = pd.read_csv(p / "funding_structure.csv")
    growth = pd.read_csv(p / "bank_deposit_growth.csv")
    macro = json.loads((p / "macro_context.json").read_text(encoding="utf-8"))
    first, last = sector.iloc[0], sector.iloc[-1]
    if (first.date, last.date) != ("2024-01-01", "2026-01-01"):
        raise ValueError("Review study-period conclusions before changing the research window")
    opening, closing = context.iloc[0], context.iloc[-1]
    current = banks[banks.date == last.date]
    growth = growth[growth.date == last.date].set_index("bank_id")
    owned = funding[funding.date == last.date].set_index("ownership")
    leaders = current.nlargest(3, "deposit_share_yoy_pp")
    retail = current.nlargest(2, "retail_deposits")
    winner, runner = retail.iloc[0], retail.iloc[1]
    absolute = growth.sort_values("total_change", ascending=False).iloc[0]
    octo = growth.loc["octobank"]
    source_list = json.loads((root / "data/sources.json").read_text(encoding="utf-8"))
    research = json.loads((root / "data/research/sources.json").read_text(encoding="utf-8"))
    sources = {s["kind"]: s for s in research}

    def references(*kinds, bank_dates=()):
        result = [{"label": sources[k]["title"], "url": sources[k]["url"]} for k in kinds]
        result += [{"label": f"{s['date']} / {s['kind']}", "url": s["url"]}
                   for s in source_list if s["date"] in bank_dates]
        return result

    ends = ("2024-01-01", "2026-01-01")
    yearly = ("2025-01-01", "2026-01-01")
    items = []

    def add(title, evidence, conclusion, refs):
        items.append(dict(title=title, evidence=evidence, conclusion=conclusion, sources=refs))

    add("Рост депозитов обеспечили сумовые остатки и средства юридических лиц",
        f"За 2025 год депозиты выросли на {last.deposits_yoy_pct:.1f}% до {last.deposits/1000:.1f} трлн сум; "
        f"кредиты — на {last.loans_yoy_pct:.1f}%, активы — на {last.assets_yoy_pct:.1f}%. "
        f"Из прироста депозитов {(closing.deposits-opening.deposits)/1000:.3f} трлн сум "
        f"сумовые остатки дали {bridge.loc[('currency','local'),'change']/1000:.3f} трлн "
        f"({bridge.loc[('currency','local'),'contribution_pct']:.1f}%). "
        f"Валютная доля депозитов снизилась с {opening.deposit_fx_share_pct:.1f}% до {closing.deposit_fx_share_pct:.1f}%. "
        f"В отдельном клиентском разрезе юридические лица обеспечили {bridge.loc[('customer','legal_entities'),'contribution_pct']:.1f}% прироста "
        f"({bridge.loc[('customer','legal_entities'),'change']/1000:.3f} трлн сум), физические лица — "
        f"{bridge.loc[('customer','individuals'),'contribution_pct']:.1f}% ({bridge.loc[('customer','individuals'),'change']/1000:.3f} трлн). "
        f"При декабрьской инфляции {macro['cpi_dec_to_dec_pct']:.1f}% рост покупательной способности совокупного депозитного остатка составил "
        f"{closing.real_deposit_growth_pct:.1f}%. В январском решении ЦБ положительные реальные ставки названы фактором поддержки сбережений в национальной валюте.",
        "Депозитная база выросла и в номинальном выражении, и после корректировки на потребительскую инфляцию. "
        "Основной вклад в валютном разрезе внесли сумовые депозиты, а в клиентском — средства юридических лиц; долларизация депозитов снизилась.",
        references("sector_indicators", "monetary_policy", bank_dates=yearly))

    add("Запас ликвидности и стабильного фондирования сектора увеличился",
        f"В 2025 году LCR вырос с {opening.lcr_pct:.1f}% до {closing.lcr_pct:.1f}%, "
        f"NSFR — с {opening.nsfr_pct:.1f}% до {closing.nsfr_pct:.1f}%. При опубликованном ЦБ минимуме 100% "
        f"запас на 01.01.2026 составил {closing.lcr_headroom_pp:.1f} и {closing.nsfr_headroom_pp:.1f} п.п. соответственно. "
        f"Высоколиквидные активы увеличились с {opening.high_liquidity_assets/1000:.1f} до {closing.high_liquidity_assets/1000:.1f} трлн сум. "
        f"Срочная часть депозитов дала {bridge.loc[('maturity','term'),'contribution_pct']:.1f}% прироста; "
        f"их доля выросла с {opening.term_deposit_share_pct:.1f}% до {closing.term_deposit_share_pct:.1f}%. "
        f"Достаточность регулятивного капитала повысилась с {opening.car_pct:.1f}% до {closing.car_pct:.1f}%. "
        f"Отношение кредитов к депозитам за два года снизилось с {first.loan_to_deposit_pct:.1f}% до {last.loan_to_deposit_pct:.1f}%.",
        "На уровне банковского сектора улучшились оба опубликованных показателя ликвидности и стабильности фондирования. "
        "На конец 2025 года LCR и NSFR превышали нормативные минимумы; рост срочной части депозитов сопровождался увеличением высоколиквидных активов.",
        references("liquidity", "maturity", "capital_adequacy", bank_dates=ends))

    add("Рынок активов стал менее концентрированным за счёт опережающего роста вне начальной пятёрки",
        f"С 01.01.2024 по 01.01.2026 CR5 снизился с {first.cr5_pct:.1f}% до {last.cr5_pct:.1f}%, "
        f"HHI — с {first.hhi:.0f} до {last.hhi:.0f}. Активы фиксированной пятёрки лидеров начала периода "
        f"выросли на {top5.loc['initial_top5','growth_pct']:.1f}%, активы остальных банков — "
        f"на {top5.loc['outside_initial_top5','growth_pct']:.1f}%. В итоговой пятёрке Kapitalbank занял место Ipoteka-bank. "
        "При расчёте CR5 лидеры определяются заново на каждую дату; сравнение темпов использует постоянный список пяти банков начала периода.",
        "Снижение концентрации подтверждено двумя метриками и разложением роста: банки вне первоначальной пятёрки нарастили активы значительно быстрее, "
        "поэтому доля крупнейших банков в совокупных активах уменьшилась.", references(bank_dates=ends))

    add(f"{100*state.growth_effect_pp/(state.closing_share_pct-state.opening_share_pct):.1f}% снижения государственной доли объясняется относительной динамикой активов",
        f"Доля банков с государственной долей снизилась с {state.opening_share_pct:.2f}% до {state.closing_share_pct:.2f}% "
        f"({state.closing_share_pct-state.opening_share_pct:.2f} п.п.). При сохранении групп начала периода итоговая доля "
        f"составила бы {state.fixed_cohort_closing_share_pct:.2f}%. Последовательное разложение даёт "
        f"{state.growth_effect_pp:.2f} п.п. за счёт изменения объёмов активов "
        f"({100*state.growth_effect_pp/(state.closing_share_pct-state.opening_share_pct):.1f}% общего снижения) "
        f"и {state.reclassification_effect_pp:.2f} п.п. за счёт изменения классификации. "
        "Единственный переход между группами среди банков, присутствующих на обеих крайних датах, — Poytaxt Bank; "
        "в таблице за 01.10.2024 он уже включён в остальные банки. Разложение использует суммы активов отдельных банков.",
        "Почти всё снижение государственной доли объясняется опережающим увеличением активов вне исходной государственной группы. "
        "Вклад перехода Poytaxt Bank количественно мал — около 1,4% общего снижения.",
        references(bank_dates=("2024-01-01", "2024-09-01", "2024-10-01", "2026-01-01")))

    add("Octobank лидирует по приросту доли депозитов, Agrobank — по абсолютному приросту",
        "Лидеры прироста рыночной доли за 2025 год: "
        + ", ".join(f"{r.bank_name} ({r.deposit_share_yoy_pp:+.2f} п.п.)" for r in leaders.itertuples())
        + f". Депозиты Octobank увеличились на {octo.total_change/1000:.3f} трлн сум, из них "
        f"{octo.legal_entity_change/1000:.3f} трлн ({octo.legal_entity_contribution_pct:.1f}%) — средства юридических лиц. "
        f"Вклад банка в прирост депозитов сектора составил {octo.sector_growth_contribution_pct:.2f}%. "
        f"Максимальный абсолютный прирост у {absolute.bank_name}: {absolute.total_change/1000:.3f} трлн сум "
        f"({absolute.sector_growth_contribution_pct:.2f}% прироста сектора).",
        "Укрепление позиции Octobank обеспечено преимущественно депозитами юридических лиц. "
        "Agrobank внёс наибольший вклад в увеличение общей депозитной базы сектора; рейтинг прироста доли и рейтинг абсолютного вклада дают разные лидирующие банки.",
        references(bank_dates=yearly))

    add("Госбанки опираются преимущественно на недепозитные обязательства, остальные — на депозиты",
        f"На 01.01.2026 депозиты покрывали {owned.loc['state','deposit_liability_share_pct']:.1f}% обязательств госбанков "
        f"и {owned.loc['other','deposit_liability_share_pct']:.1f}% обязательств остальных банков. "
        f"Недепозитные обязательства госбанков составили {owned.loc['state','other_liabilities']/1000:.1f} трлн сум "
        f"({owned.loc['state','other_liability_share_pct']:.1f}% обязательств); у остальных — "
        f"{owned.loc['other','other_liabilities']/1000:.1f} трлн ({owned.loc['other','other_liability_share_pct']:.1f}%). "
        f"Кредиты к депозитам составили {owned.loc['state','loan_to_deposit_pct']:.1f}% и {owned.loc['other','loan_to_deposit_pct']:.1f}% соответственно. "
        f"По сектору доля депозитов в обязательствах выросла с {opening.deposit_liability_share_pct:.1f}% до {closing.deposit_liability_share_pct:.1f}%, "
        f"обеспечив {closing.deposit_liability_growth_contribution_pct:.1f}% прироста обязательств за 2025 год. "
        f"Крупнейшая отдельная недепозитная статья сводного баланса — привлечённые кредиты и лизинг: {closing.borrowings_leasing/1000:.1f} трлн сум.",
        "У групп различается структура обязательств: в госбанках преобладает недепозитная часть, в остальных банках — депозитная. "
        "За 2025 год сектор в целом увеличил долю депозитов в фондировании; именно депозиты обеспечили основную часть прироста обязательств.",
        references("balance", bank_dates=yearly))

    add(f"{winner.bank_name} — лидер по объёму депозитов физических лиц",
        f"На 01.01.2026 у {winner.bank_name} размещено {winner.retail_deposits/1000:.3f} трлн сум физических лиц "
        f"({100*winner.retail_deposits/last.retail_deposits:.1f}% сегмента). У следующего банка, {runner.bank_name}, — "
        f"{runner.retail_deposits/1000:.3f} трлн; отрыв лидера составляет {(winner.retail_deposits-runner.retail_deposits)/1000:.3f} трлн сум. "
        f"Доля физических лиц в депозитах самого {winner.bank_name} равна {winner.retail_deposit_share_pct:.1f}%. "
        f"За 2025 год розничный остаток вырос на {growth.loc[winner.bank_id,'individual_change']/1000:.3f} трлн сум.",
        f"{winner.bank_name} занимает первое место по объёму привлечённых средств физических лиц с существенным отрывом от следующего банка. "
        "Розничные средства составляют большинство его депозитной базы.", references(bank_dates=yearly))

    executive = (
        f"В 2024–2025 годах распределение банковских активов стало менее концентрированным. "
        f"В 2025 году депозитная база выросла на {last.deposits_yoy_pct:.1f}% "
        f"({closing.real_deposit_growth_pct:.1f}% после корректировки на ИПЦ), а её доля в обязательствах достигла {closing.deposit_liability_share_pct:.1f}%. "
        f"LCR {closing.lcr_pct:.1f}% и NSFR {closing.nsfr_pct:.1f}% подтверждают увеличение агрегированного запаса ликвидности и стабильного фондирования. "
        "Octobank лидировал по приросту доли депозитов, Agrobank — по абсолютному приросту, Kapitalbank — по объёму депозитов физических лиц."
    )
    return executive, items
