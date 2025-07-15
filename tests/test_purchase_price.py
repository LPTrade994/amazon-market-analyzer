import ast
import math
import re
import types

# Minimal stub for pandas.isna used in app.py
class _PandasStub(types.SimpleNamespace):
    @staticmethod
    def isna(value):
        return isinstance(value, float) and math.isnan(value)

pd = _PandasStub()


def load_functions():
    with open('app.py', 'r') as f:
        source = f.read()
    module = ast.parse(source)
    env = {'re': re, 'pd': pd, 'math': math}
    for node in module.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == 'VAT_RATES':
                    exec(compile(ast.Module([node], []), 'app.py', 'exec'), env)
        elif isinstance(node, ast.FunctionDef) and node.name in {'normalize_locale', 'calc_final_purchase_price'}:
            exec(compile(ast.Module([node], []), 'app.py', 'exec'), env)
    return env['VAT_RATES'], env['normalize_locale'], env['calc_final_purchase_price']


VAT_RATES, normalize_locale, calc_final_purchase_price = load_functions()


def test_purchase_price_de():
    row = {"Price_Base": 100, "Locale (base)": "DE"}
    expected = 100 / (1 + 0.19) * (1 - 0.21)
    assert math.isclose(calc_final_purchase_price(row, 0.21), expected, rel_tol=1e-6)


def test_purchase_price_it():
    row = {"Price_Base": 100, "Locale (base)": "IT"}
    expected = 100 / (1 + 0.22) - 100 * 0.21
    assert math.isclose(calc_final_purchase_price(row, 0.21), expected, rel_tol=1e-6)


def test_locale_variants():
    for variant in ["Amazon.de", "de-DE"]:
        row = {"Price_Base": 100, "Locale (base)": variant}
        expected = 100 / (1 + 0.19) * (1 - 0.21)
        assert math.isclose(calc_final_purchase_price(row, 0.21), expected, rel_tol=1e-6)
    for variant in ["Amazon.it", "it_IT"]:
        row = {"Price_Base": 100, "Locale (base)": variant}
        expected = 100 / (1 + 0.22) - 100 * 0.21
        assert math.isclose(calc_final_purchase_price(row, 0.21), expected, rel_tol=1e-6)

