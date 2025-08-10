import sys, pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from analysis import condition_flag
import pandas as pd


def test_condition_flag():
    rows = [
        {"title": "Prodotto Ricondizionato", "cat_sub": ""},
        {"title": "Prodotto Nuovo", "cat_sub": "Renewed"},
        {"title": "Prodotto", "cat_sub": ""},
    ]
    df = pd.DataFrame(rows)
    results = df.apply(condition_flag, axis=1)
    assert results.tolist() == [
        "refurbished/ricondizionato",
        "refurbished/ricondizionato",
        "new",
    ]
