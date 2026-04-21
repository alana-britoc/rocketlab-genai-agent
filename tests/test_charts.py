"""
Unit tests for automatic chart type detection.
Run with: pytest tests/test_charts.py -v
"""

import pytest
import pandas as pd
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.charts.generator import detect_chart_type, generate_chart


def test_detects_bar_for_category_and_number():
    df = pd.DataFrame({
        "categoria": ["A", "B", "C", "D", "E", "F", "G", "H"],
        "total": [100, 80, 60, 40, 30, 20, 10, 5],
    })
    result = detect_chart_type(df)
    assert result["chart_type"] == "bar"
    assert result["x_col"] == "categoria"
    assert result["y_col"] == "total"


def test_detects_pie_for_few_categories():
    df = pd.DataFrame({
        "status": ["delivered", "canceled", "shipped"],
        "qtd": [800, 100, 50],
    })
    result = detect_chart_type(df)
    assert result["chart_type"] == "pie"


def test_detects_line_for_date_column():
    df = pd.DataFrame({
        "month": ["2017-01", "2017-02", "2017-03"],
        "revenue": [1000.0, 1200.0, 900.0],
    })
    result = detect_chart_type(df)
    assert result["chart_type"] == "line"


def test_detects_scatter_for_two_numerics():
    df = pd.DataFrame({
        "avg_score": [3.5, 4.0, 2.1],
        "total_orders": [100, 200, 50],
    })
    result = detect_chart_type(df)
    assert result["chart_type"] == "scatter"


def test_none_for_empty_df():
    df = pd.DataFrame()
    result = detect_chart_type(df)
    assert result["chart_type"] == "none"


def test_none_for_single_column():
    df = pd.DataFrame({"col": [1, 2, 3]})
    result = detect_chart_type(df)
    assert result["chart_type"] == "none"


def test_generate_chart_returns_dict():
    df = pd.DataFrame({
        "categoria": [f"Cat {i}" for i in range(10)],
        "total": list(range(10, 110, 10)),
    })
    chart = generate_chart(df, title="Test Chart")
    assert chart is not None
    assert "data" in chart
    assert "layout" in chart


def test_generate_chart_returns_none_for_empty():
    chart = generate_chart(pd.DataFrame())
    assert chart is None
