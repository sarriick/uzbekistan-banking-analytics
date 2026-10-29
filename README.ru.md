# Аналитика банков Узбекистана

Готовый проект для портфолио Data Analyst / BI: реальные данные ЦБ, Python, SQL, DuckDB, Streamlit и аналитическая записка.

**Период:** 01.01.2024 — 01.01.2026. В наборе 889 наблюдений «банк × месяц», 36 банков за весь период и 50 исходных публикаций. На каждой конкретной дате — 35 или 36 банков.

## С чего начать

1. Откройте [интерактивный отчёт](reports/overview.html) в браузере после скачивания: Python для него не нужен.
2. Прочитайте [семь аналитических выводов](reports/findings.ru.md).
3. Запустите приложение для сравнения банков и выбора отчётных дат.

## Запуск на Windows

Откройте PowerShell в папке проекта. Нужен Python 3.12.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m uzbank.build
.\.venv\Scripts\python.exe -m uzbank.report
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Откройте адрес, который напечатает Streamlit. Активация окружения не требуется: команды вызывают его Python напрямую.

## Что находится в проекте

- Дашборд с обзором рынка, сравнением банков, структурой кредитов и депозитов, выгрузкой CSV.
- Сохранённые исходные страницы ЦБ и ссылки на каждую публикацию.
- Автоматическая очистка и проверка данных, включая 750 сверок с опубликованными итогами.
- SQL-запросы: доли рынка, рост год к году, концентрация и структура фондирования.
- Английский README для GitHub и русская аналитическая записка.
- Тесты и workflow GitHub Actions. Workflow начнёт выполняться после публикации репозитория.

## Что показать на собеседовании

Начните с вопроса: «Какие банки увеличивают долю рынка и что происходит с их депозитной базой?» Покажите изменение долей, объясните различие между темпом роста и вкладом в рост рынка. Затем откройте SQL и источник одного результата.

Объясните три решения: почему остатки нельзя суммировать по месяцам; почему Smart Bank и Open Bank объединены; почему отношение кредитов к депозитам само по себе не является оценкой надёжности банка. Методика и ограничения подробно описаны в [документации](docs/methodology.md).

## Публикация на GitHub

Рекомендуемое имя: `uzbekistan-banking-analytics`.

Описание: `Uzbekistan banking sector analytics: 25 monthly snapshots, Python, SQL, DuckDB and an interactive Streamlit dashboard.`

Темы: `data-analysis`, `banking`, `uzbekistan`, `sql`, `python`, `streamlit`, `portfolio`, `duckdb`.

Создайте пустой репозиторий без автоматически добавленного README. Затем в папке проекта:

```bash
git init -b main
git add .
git commit -m "Build Uzbekistan banking analytics portfolio"
git remote add origin https://github.com/YOUR_USERNAME/uzbekistan-banking-analytics.git
git push -u origin main
```

Если репозиторий уже инициализирован, пропустите `git init`; если исходный коммит уже существует, пропустите также `git add` и `git commit`. Замените `YOUR_USERNAME` своим логином. Не добавляйте в GitHub файлы виртуального окружения или учётные данные.
