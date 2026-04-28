“””
charts.py — Plotly chart factory with UdeS branding.

Fix: _apply_theme merges caller overrides into the layout dict and pops any
duplicate keys (especially `height`) BEFORE calling fig.update_layout, so the
same keyword is never passed twice. Robust to any future overlap between
get_plotly_layout() defaults and per-chart overrides.
“””

import plotly.graph_objects as go
import pandas as pd
import numpy as np

from theme import (
UDES_GREEN, UDES_GREEN_DARK, UDES_GREEN_LIGHT, UDES_GOLD, UDES_GOLD_DARK,
BG_DARK, BG_CARD, BG_DIVIDER, TEXT_PRIMARY, TEXT_MUTED, TEXT_SECONDARY,
POSITIVE, NEGATIVE, NEUTRAL, INFO, SECTOR_COLORS,
get_plotly_layout,
)

def _apply_theme(fig: go.Figure, title: str = “”, height: int = 400, **overrides) -> go.Figure:
“””
Apply the SIF theme to a Plotly figure.

```
- Pulls the base layout dict from get_plotly_layout(title)
- Merges in `height` and any **overrides** (caller wins)
- Calls fig.update_layout(**layout) ONCE — no duplicate kwargs possible
"""
# Get the themed base layout (already a dict with `height` etc.)
try:
    layout = dict(get_plotly_layout(title))
except Exception:
    layout = {}

# Caller-supplied height always wins; remove any pre-existing one first
layout.pop("height", None)
if height is not None:
    layout["height"] = height

# Any extra overrides win over base layout (pop to avoid duplicate kwargs)
for k, v in overrides.items():
    layout.pop(k, None)
    layout[k] = v

try:
    fig.update_layout(**layout)
except TypeError:
    # Last-resort safety net: drop unknown keys and retry
    safe_layout = {k: v for k, v in layout.items() if k in {
        "title", "paper_bgcolor", "plot_bgcolor", "font", "height",
        "margin", "xaxis", "yaxis", "legend", "hoverlabel", "showlegend",
        "annotations", "barmode",
    }}
    fig.update_layout(**safe_layout)
return fig
```

def price_chart(prices: pd.Series, ticker: str, benchmark: pd.Series = None) -> go.Figure:
fig = go.Figure()
if prices is None or prices.empty:
return _apply_theme(fig, f”{ticker} — No price data available”)

```
if benchmark is not None and not benchmark.empty:
    norm_p = prices / prices.iloc[0] * 100
    norm_b = benchmark / benchmark.iloc[0] * 100
    fig.add_trace(go.Scatter(x=norm_p.index, y=norm_p.values, name=ticker,
                             line=dict(color=UDES_GOLD, width=2.5)))
    fig.add_trace(go.Scatter(x=norm_b.index, y=norm_b.values, name="Benchmark",
                             line=dict(color=NEUTRAL, width=1.5, dash="dot")))
    fig.update_yaxes(title_text="Indexed (Start = 100)")
else:
    fig.add_trace(go.Scatter(x=prices.index, y=prices.values, name=ticker,
                             line=dict(color=UDES_GOLD, width=2.5),
                             fill='tozeroy', fillcolor="rgba(255,184,28,0.08)"))
    fig.update_yaxes(title_text="Price ($)")

return _apply_theme(fig, f"{ticker} — Price History", height=380)
```

def returns_bar(returns: dict, ticker: str = “”) -> go.Figure:
fig = go.Figure()
labels = [“1D”, “1W”, “1M”, “3M”, “6M”, “YTD”, “1Y”, “3Y”, “5Y”]
keys = [“1d”, “1w”, “1m”, “3m”, “6m”, “ytd”, “1y”, “3y”, “5y”]
values = []
colors = []
valid_labels = []

```
for label, key in zip(labels, keys):
    v = returns.get(key)
    if v is None:
        continue
    v_pct = v * 100
    values.append(v_pct)
    colors.append(POSITIVE if v_pct >= 0 else NEGATIVE)
    valid_labels.append(label)

if not values:
    return _apply_theme(fig, "No return data")

fig.add_trace(go.Bar(x=valid_labels, y=values, marker=dict(color=colors),
                     text=[f"{v:+.1f}%" for v in values],
                     textposition="outside", cliponaxis=False))
fig.update_yaxes(title_text="Return (%)")
return _apply_theme(fig, f"{ticker} — Returns by Period", height=300, showlegend=False)
```

def heatmap(df: pd.DataFrame, title: str = “”, zmin: float = -25, zmax: float = 25,
fmt: str = “+.1f”) -> go.Figure:
if df is None or df.empty:
return _apply_theme(go.Figure(), “No data”)

```
text = [[f"{v:{fmt}}" if pd.notna(v) else "" for v in row] for row in df.values]

fig = go.Figure(go.Heatmap(
    z=df.values, x=df.columns.tolist(), y=df.index.tolist(),
    colorscale=[[0, NEGATIVE], [0.4, "#3D1A1A"], [0.5, BG_CARD],
                 [0.6, "#1A3D2E"], [1, POSITIVE]],
    zmin=zmin, zmax=zmax, zmid=0,
    text=text, texttemplate="%{text}",
    textfont=dict(size=11, color=TEXT_PRIMARY),
    colorbar=dict(thickness=10, len=0.8, tickfont=dict(color=TEXT_MUTED, size=10)),
))
return _apply_theme(fig, title, height=max(360, 22 * len(df.index) + 100))
```

def sector_allocation_pie(weights: dict, title: str = “Sector Allocation”) -> go.Figure:
if not weights:
return _apply_theme(go.Figure(), “No data”)

```
sectors = list(weights.keys())
values = list(weights.values())
colors = [SECTOR_COLORS.get(s, NEUTRAL) for s in sectors]

fig = go.Figure(go.Pie(
    labels=sectors, values=values, hole=0.55,
    marker=dict(colors=colors, line=dict(color=BG_DARK, width=2)),
    textfont=dict(size=11, color=TEXT_PRIMARY),
    textposition="outside", textinfo="label+percent", showlegend=False,
))
annotations = [
    dict(text=f"<b>{len(sectors)}</b><br><span style='font-size:10px'>SECTORS</span>",
         x=0.5, y=0.5, font=dict(size=22, color=UDES_GOLD), showarrow=False)
]
return _apply_theme(fig, title, height=380, annotations=annotations)
```

def gauge_chart(value: float, title: str, min_val: float = 0, max_val: float = 100) -> go.Figure:
if value is None:
value = 0

```
if value >= 70: bar_color = POSITIVE
elif value >= 55: bar_color = UDES_GOLD
elif value >= 40: bar_color = "#E07B39"
else: bar_color = NEGATIVE

fig = go.Figure(go.Indicator(
    mode="gauge+number",
    value=value,
    title={"text": title, "font": {"size": 13, "color": TEXT_SECONDARY}},
    number={"font": {"size": 36, "color": TEXT_PRIMARY}},
    gauge={
        "axis": {"range": [min_val, max_val], "tickfont": {"color": TEXT_MUTED, "size": 10}},
        "bar": {"color": bar_color, "thickness": 0.8},
        "bgcolor": BG_CARD, "borderwidth": 1, "bordercolor": BG_DIVIDER,
        "steps": [{"range": [0, 40], "color": "#3D1A1A"},
                   {"range": [40, 55], "color": "#3D2A1A"},
                   {"range": [55, 70], "color": "#2A3D1A"},
                   {"range": [70, 100], "color": "#1A3D2E"}],
        "threshold": {"line": {"color": UDES_GOLD, "width": 3},
                       "thickness": 0.85, "value": value},
    }
))
# Gauge has its own minimal layout (no axes), so we don't use _apply_theme here
fig.update_layout(paper_bgcolor=BG_CARD, font={"color": TEXT_PRIMARY},
                   height=240, margin=dict(l=10, r=10, t=40, b=10))
return fig
```

def macro_indicator_chart(series: pd.Series, title: str, color: str = None,
threshold: float = None) -> go.Figure:
fig = go.Figure()
if series is None or series.empty:
return _apply_theme(fig, f”{title} — No data available”, height=280)

```
color = color or UDES_GOLD
fig.add_trace(go.Scatter(
    x=series.index, y=series.values,
    line=dict(color=color, width=2),
    fill="tozeroy", fillcolor=f"{color}1A", name=title,
))
if threshold is not None:
    fig.add_hline(y=threshold, line_dash="dot", line_color=NEUTRAL,
                  annotation_text=f"Threshold: {threshold}",
                  annotation_position="top right")
return _apply_theme(fig, title, height=280)
```

def scatter_bubble(df: pd.DataFrame, x_col: str, y_col: str, size_col: str,
color_col: str, label_col: str, title: str = “”) -> go.Figure:
fig = go.Figure()
if df.empty:
return _apply_theme(fig, “No data”)

```
for sector in df[color_col].unique():
    sub = df[df[color_col] == sector]
    color = SECTOR_COLORS.get(sector, NEUTRAL)
    sizes = sub[size_col].fillna(1e9) / 1e9 * 5
    sizes = sizes.clip(lower=8, upper=50)
    fig.add_trace(go.Scatter(
        x=sub[x_col], y=sub[y_col], mode="markers+text",
        marker=dict(size=sizes, color=color, line=dict(width=1, color=TEXT_PRIMARY),
                    opacity=0.85),
        text=sub[label_col], textposition="top center",
        textfont=dict(size=10, color=TEXT_PRIMARY),
        name=sector,
    ))
fig.update_xaxes(title_text=x_col)
fig.update_yaxes(title_text=y_col)
return _apply_theme(fig, title, height=440, showlegend=False)
```

def sensitivity_heatmap(df: pd.DataFrame, current_price: float = None,
title: str = “Valuation Sensitivity”) -> go.Figure:
if df is None or df.empty:
return _apply_theme(go.Figure(), “No data”)

```
fig = go.Figure(go.Heatmap(
    z=df.values, x=df.columns.tolist(), y=df.index.tolist(),
    colorscale=[[0, NEGATIVE], [0.5, BG_CARD], [1, POSITIVE]],
    text=[[f"${v:.0f}" if v else "—" for v in row] for row in df.values],
    texttemplate="%{text}",
    textfont=dict(size=11, color=TEXT_PRIMARY),
    colorbar=dict(title="$/share", thickness=10, len=0.8,
                   tickfont=dict(color=TEXT_MUTED, size=10)),
))
if current_price is not None:
    fig.add_annotation(xref="paper", yref="paper", x=1.15, y=1.05,
                        text=f"<b>Current: ${current_price:.2f}</b>",
                        showarrow=False,
                        font=dict(color=UDES_GOLD, size=11), align="right")
return _apply_theme(fig, title, height=380)
```
