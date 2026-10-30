from streamlit.testing.v1 import AppTest
from uzbank.fetch import ROOT


def test_dashboard_controls_and_empty_selection():
    app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=45).run()
    assert not app.exception
    assert len(app.metric) == 4
    assert len(app.tabs) == 5
    assert any("депозитная база выросла" in item.value for item in app.success)
    app.selectbox(key="metric").select("Капитал").run()
    assert not app.exception
    app.radio(key="scale").set_value("Индекс: первая доступная дата = 100").run()
    assert not app.exception
    app.multiselect(key="banks").set_value([]).run()
    assert not app.exception
    assert any("Выберите" in info.value for info in app.info)
    app.selectbox(key="as_of").set_value(app.selectbox(key="as_of").options[0]).run()
    assert not app.exception
