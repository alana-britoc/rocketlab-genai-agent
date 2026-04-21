import json
import re
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from typing import Optional

def _fmt(col: str) -> str:
    col = re.sub(r'_brl$', ' (BRL)', col, flags=re.IGNORECASE)
    col = re.sub(r'_usd$', ' (USD)', col, flags=re.IGNORECASE)
    return col.replace('_', ' ').title()

def _is_numeric(series: pd.Series) -> bool:
    return pd.api.types.is_numeric_dtype(series)

def _is_datetime_like(col_name: str) -> bool:
    keywords = ["date", "month", "year", "mes", "ano", "data", "timestamp", "periodo"]
    return any(k in col_name.lower() for k in keywords)

def detect_chart_type(df: pd.DataFrame) -> dict:
    if df.empty or len(df.columns) < 2:
        return {"chart_type": "none"}
    cols = df.columns.tolist()
    numeric_cols = [c for c in cols if _is_numeric(df[c])]
    datetime_cols = [c for c in cols if _is_datetime_like(c)]
    text_cols = [c for c in cols if not _is_numeric(df[c])]

    if datetime_cols and numeric_cols:
        return {"chart_type": "line", "x_col": datetime_cols[0], "y_col": numeric_cols[0]}
    if len(text_cols) == 1 and len(numeric_cols) == 1:
        return {"chart_type": "pie" if df[text_cols[0]].nunique() <= 6 else "bar", "x_col": text_cols[0], "y_col": numeric_cols[0]}
    return {"chart_type": "bar", "x_col": cols[0], "y_col": numeric_cols[0]} if numeric_cols else {"chart_type": "none"}

_LIME = "#b8f53c"
_CYAN = "#3ce8e8"
_INK2 = "#13151c"
_LINE = "#252836"
_MUTE = "#6b7491"
_SNOW = "#e8eaf2"

_PALETTE = [_LIME, _CYAN, "#10b981", "#818cf8", "#f472b6", "#38bdf8"]
_SEQ_SCALE = [[0, "#0d3d3d"], [0.5, "#10b981"], [1, _LIME]]
_FONT_CFG = dict(family="'IBM Plex Mono', monospace", size=11, color=_MUTE)

def generate_chart(df: pd.DataFrame, title: str = "", chart_hint: Optional[dict] = None) -> Optional[dict]:
    if df.empty: return None

    detection = chart_hint or detect_chart_type(df)
    chart_type = detection.get("chart_type", "none")
    if chart_type == "none": return None

    x_c = detection.get("x_col", df.columns[0])
    y_c = detection.get("y_col", df.columns[1] if len(df.columns) > 1 else df.columns[0])
    
    df_plot = df.copy()
    df_plot.columns = [_fmt(c) for c in df_plot.columns]
    x_lab, y_lab = _fmt(x_c), _fmt(y_c)

    try:
        if chart_type == "bar":
            df_plot = df_plot.sort_values(y_lab, ascending=True)
            fig = px.bar(df_plot, x=y_lab, y=x_lab, orientation="h", template="plotly_dark")
            fig.update_traces(marker=dict(color=df_plot[y_lab], colorscale=_SEQ_SCALE, line_width=0))

        elif chart_type == "line":
            fig = px.line(df_plot, x=x_lab, y=y_lab, template="plotly_dark", markers=True)
            fig.update_traces(
                line=dict(color=_LIME, width=2, shape="spline", smoothing=0.8),
                marker=dict(size=7, color=_INK2, line=dict(color=_LIME, width=2)),
                fill="tozeroy", fillcolor="rgba(184,245,60,0.05)"
            )

        elif chart_type == "pie":
            fig = px.pie(df_plot, names=x_lab, values=y_lab, template="plotly_dark", hole=0.55)
            fig.update_traces(marker=dict(colors=_PALETTE, line=dict(color="#0d0e12", width=2)))

        elif chart_type == "scatter":
            fig = px.scatter(df_plot, x=x_lab, y=y_lab, template="plotly_dark")
            fig.update_traces(marker=dict(color=_CYAN, size=10, opacity=0.8))

        fig.update_layout(
            title=dict(text=title or f"{y_lab} por {x_lab}", font=dict(color=_SNOW, size=14)),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=_FONT_CFG,
            margin=dict(l=10, r=10, t=40, b=10), 
            showlegend=(chart_type == "pie"),
            xaxis=dict(gridcolor=_LINE, zeroline=False),
            yaxis=dict(gridcolor=_LINE, zeroline=False)
        )

        return json.loads(fig.to_json())
    except Exception:
        return None

def dataframe_from_result(result: dict) -> pd.DataFrame:
    if not result.get("data"): return pd.DataFrame()
    return pd.DataFrame(result["data"])