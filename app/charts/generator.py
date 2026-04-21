"""
Automatic chart generation from SQL query results using Plotly.
Detects the best chart type based on column types and data shape.
"""

import json
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from typing import Optional


# ---------------------------------------------------------------------------
# Chart type detection
# ---------------------------------------------------------------------------

def _is_numeric(series: pd.Series) -> bool:
    return pd.api.types.is_numeric_dtype(series)


def _is_datetime_like(col_name: str) -> bool:
    keywords = ["date", "month", "year", "mes", "ano", "data", "timestamp", "periodo"]
    return any(k in col_name.lower() for k in keywords)


def detect_chart_type(df: pd.DataFrame) -> dict:
    """
    Automatically detect the best chart type for a DataFrame.
    Returns a dict with: chart_type, x_col, y_col.
    """
    if df.empty or len(df.columns) < 2:
        return {"chart_type": "none"}

    cols = df.columns.tolist()
    numeric_cols = [c for c in cols if _is_numeric(df[c])]
    text_cols = [c for c in cols if not _is_numeric(df[c])]
    datetime_cols = [c for c in cols if _is_datetime_like(c)]

    # Time series: date + numeric → line
    if datetime_cols and numeric_cols:
        return {
            "chart_type": "line",
            "x_col": datetime_cols[0],
            "y_col": numeric_cols[0],
        }

    # 2-column: category + number → bar
    if len(text_cols) == 1 and len(numeric_cols) == 1:
        n_categories = df[text_cols[0]].nunique()
        if n_categories <= 6:
            return {
                "chart_type": "pie",
                "x_col": text_cols[0],
                "y_col": numeric_cols[0],
            }
        return {
            "chart_type": "bar",
            "x_col": text_cols[0],
            "y_col": numeric_cols[0],
        }

    # Multiple numeric cols → bar (grouped)
    if text_cols and len(numeric_cols) >= 2:
        return {
            "chart_type": "bar",
            "x_col": text_cols[0],
            "y_col": numeric_cols[0],
        }

    # 2 numeric cols → scatter
    if len(numeric_cols) == 2:
        return {
            "chart_type": "scatter",
            "x_col": numeric_cols[0],
            "y_col": numeric_cols[1],
        }

    return {"chart_type": "none"}


# ---------------------------------------------------------------------------
# Chart builder
# ---------------------------------------------------------------------------

PLOTLY_THEME = "plotly_dark"
COLOR_PALETTE = [
    "#6366f1", "#22d3ee", "#f59e0b", "#10b981",
    "#f43f5e", "#a78bfa", "#34d399", "#fb923c"
]


def generate_chart(
    df: pd.DataFrame,
    title: str = "",
    chart_hint: Optional[dict] = None,
) -> Optional[dict]:
    """
    Generate a Plotly chart JSON from a DataFrame.
    Returns the Plotly figure as a JSON-serializable dict, or None if not applicable.
    """
    if df.empty:
        return None

    detection = chart_hint or detect_chart_type(df)
    chart_type = detection.get("chart_type", "none")

    if chart_type == "none":
        return None

    x_col = detection.get("x_col", df.columns[0])
    y_col = detection.get("y_col", df.columns[1] if len(df.columns) > 1 else df.columns[0])

    # Sort by y value for bar charts (makes rankings clearer)
    if chart_type == "bar":
        df = df.sort_values(y_col, ascending=True)

    try:
        if chart_type == "bar":
            fig = px.bar(
                df, x=y_col, y=x_col, orientation="h",
                title=title or f"{y_col} por {x_col}",
                template=PLOTLY_THEME,
                color=y_col,
                color_continuous_scale="Viridis",
            )
            fig.update_layout(coloraxis_showscale=False, showlegend=False)

        elif chart_type == "line":
            fig = px.line(
                df, x=x_col, y=y_col,
                title=title or f"{y_col} ao longo do tempo",
                template=PLOTLY_THEME,
                markers=True,
            )
            fig.update_traces(line_color=COLOR_PALETTE[0], marker_color=COLOR_PALETTE[1])

        elif chart_type == "pie":
            fig = px.pie(
                df, names=x_col, values=y_col,
                title=title or f"Distribuição por {x_col}",
                template=PLOTLY_THEME,
                color_discrete_sequence=COLOR_PALETTE,
                hole=0.4,
            )

        elif chart_type == "scatter":
            fig = px.scatter(
                df, x=x_col, y=y_col,
                title=title or f"{x_col} vs {y_col}",
                template=PLOTLY_THEME,
            )
            fig.update_traces(marker_color=COLOR_PALETTE[0])

        else:
            return None

        # Common layout tweaks
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font_family="'DM Sans', sans-serif",
            title_font_size=15,
            margin=dict(l=20, r=20, t=50, b=20),
        )

        return json.loads(fig.to_json())

    except Exception:
        return None


def dataframe_from_result(result: dict) -> pd.DataFrame:
    """Convert a query result dict to a pandas DataFrame."""
    if not result.get("data"):
        return pd.DataFrame()
    return pd.DataFrame(result["data"])
