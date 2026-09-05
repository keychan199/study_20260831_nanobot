from mini_nanobot.tools.basic import calculator, get_current_time


def test_calculator():
    assert calculator.invoke({"expression": "(1 + 12) * 3"}) == "39"


def test_get_current_time():
    value = get_current_time.invoke({})
    assert "T" in value
