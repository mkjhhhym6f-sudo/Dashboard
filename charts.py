"""
Plotly Chart Templates for the Fund Dashboard
Institutional-grade, dark-theme charts with consistent styling.
"""

import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from typing import Optional

# ─── Theme ────────────────────────────────────────────────────────────────────
DARK_THEME = dict(
    paper_bgcolor="#0a0e1a",
    plot_bgcolor="#111827",
    font=dict(family="IBM Plex Mono, monospace", color="#94a3b8", size=11),
    xaxis=dict(gridcolor="#1e293b", zerolinecolor="#334155", linecolor="#334155"),
    yaxis=dict(gridcolor="#1e293b", zerolinecolor="#334155", linecolor="#334155"),
    margin=dict(l=40, r=20, t=50, b=40),
)

COLORS = {
    "positive":  "#06d6a0",
    "negative":  "#ef233c",
    "warning":   "#ffd60a",
    "neutral":   "#8d99ae",
    "primary":   "#00b4d8",
    "secondary": "#7c3aed",
    "accent":    "#f77f00",
}

SECTOR_COLORS = {
    "Technology":             "#00b4d8",
    "Financials":             "#3b82f6",
    "Consumer_Staples":       "#06d6a0",
    "Consumer_Discretionary": "#f77f00",
    "Industrials":            "#6366f1",
    "Real_Estate":            "#ec4899",
    "Utilities":              "#8b5cf6",
    "Materials":              "#f59e0b",
    "Communication_Services": "#14b8a6",
    "Healthcare":             "#10b981",
}


def _apply_theme(fig: go.Figure, title: str = "") -> go.Figure:
    fig.update_layout(**DARK_THEME, title=dict(text=title, font=dict(color="#f8fafc", size=14)))
    return fig


def price_chart(
    prices: pd.Series,
    ticker: str,
    benchmark: pd.Series = None,
    show_volume: bool = True,
    volumes: pd.Series = None,
) -> go.Figure:
    """Candlestick/line chart with optional benchmark overlay and volume."""

    if show_volume and volumes is not None:
        fig = make_subplots(
            rows=2, cols=1,
            shared_xaxes=True,
            row_heights=[0.75, 0.25],
            vertical_spacing=0.03,
        )
        row_price, row_vol = 1, 2
    else:
        fig = go.Figure()
        row_price, row_vol = None, None

    # Normalize to 100 for relative performance
    norm_price = prices / prices.iloc[0] * 100

    kwargs = dict(row=row_price, col=1) if row_price else {}

    fig.add_trace(go.Scatter(
        x=prices.index, y=norm_price,
        name=ticker,
        line=dict(color=COLORS["primary"], width=2),
        **kwargs
    ))

    if benchmark is not None and not benchmark.empty:
        aligned = benchmark.reindex(prices.index, method="ffill").dropna()
        norm_bench = aligned / aligned.iloc[0] * 100 if not aligned.empty else None
        if norm_bench is not None:
            fig.add_trace(go.Scatter(
                x=aligned.index, y=norm_bench,
                name="Benchmark",
                line=dict(color=COLORS["neutral"], width=1.5, dash="dot"),
                **kwargs
            ))

    # 52w high/low
    high_52 = prices.tail(252).max() if len(prices) >= 252 else prices.max()
    low_52 = prices.tail(252).min() if len(prices) >= 252 else prices.min()
    curr = prices.iloc[-1]
    drawdown_pct = (curr / high_52 - 1) * 100

    if row_vol and volumes is not None:
        colors_vol = [COLORS["positive"] if v > volumes.mean() else COLORS["neutral"] for v in volumes]
        fig.add_trace(go.Bar(
            x=volumes.index, y=volumes,
            name="Volume",
            marker_color=colors_vol,
            opacity=0.6,
            row=row_vol, col=1
        ))

    _apply_theme(fig, f"{ticker} — Price Performance (Indexed to 100)")
    fig.update_layout(
        height=420,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        annotations=[dict(
            text=f"From 52W High: {drawdown_pct:.1f}%",
            xref="paper", yref="paper",
            x=0.01, y=0.98, showarrow=False,
            font=dict(color=COLORS["negative"] if drawdown_pct < -10 else COLORS["neutral"], size=10),
        )]
    )
    return fig


def returns_bar(returns: dict, ticker: str) -> go.Figure:
    """Bar chart of period returns."""
    labels = {"1d": "1D", "1w": "1W", "1m": "1M", "3m": "3M", "6m": "6M", "ytd": "YTD", "1y": "1Y", "3y": "3Y", "5y": "5Y"}
    xs, ys = [], []
    for k, label in labels.items():
        if returns.get(k) is not None:
            xs.append(label)
            ys.append(returns[k] * 100)

    colors = [COLORS["positive"] if y >= 0 else COLORS["negative"] for y in ys]
    fig = go.Figure(go.Bar(x=xs, y=ys, marker_color=colors, text=[f"{y:.1f}%" for y in ys], textposition="outside"))
    fig.add_hline(y=0, line_color="#334155")
    _apply_theme(fig, f"{ticker} — Period Returns (%)")
    fig.update_layout(height=280, showlegend=False)
    return fig


def financial_trend(df: pd.DataFrame, metrics: list, title: str = "Financial Trends") -> go.Figure:
    """
    Multi-line chart for financial metrics over time.
    df: index = years, columns = metric names
    metrics: list of column names to plot
    """
    palette = [COLORS["primary"], COLORS["positive"], COLORS["warning"], COLORS["accent"], COLORS["secondary"]]
    fig = go.Figure()
    for i, metric in enumerate(metrics):
        if metric in df.columns:
            fig.add_trace(go.Scatter(
                x=df.index.astype(str), y=df[metric],
                name=metric,
                mode="lines+markers",
                line=dict(color=palette[i % len(palette)], width=2),
                marker=dict(size=5),
            ))
    _apply_theme(fig, title)
    fig.update_layout(height=320, legend=dict(orientation="h", y=-0.15))
    return fig


def heatmap(df: pd.DataFrame, title: str = "", fmt: str = ".1f", zmin=None, zmax=None) -> go.Figure:
    """Correlation/performance heatmap."""
    fig = go.Figure(go.Heatmap(
        z=df.values,
        x=df.columns.tolist(),
        y=df.index.tolist(),
        colorscale=[[0, "#ef233c"], [0.5, "#1e293b"], [1, "#06d6a0"]],
        text=df.applymap(lambda v: f"{v:{fmt}}" if pd.notna(v) else "N/A").values,
        texttemplate="%{text}",
        hovertemplate="%{y} | %{x}: %{z:.2f}<extra></extra>",
        zmin=zmin, zmax=zmax,
        colorbar=dict(thickness=10, tickfont=dict(size=9)),
    ))
    _apply_theme(fig, title)
    fig.update_layout(height=max(300, len(df.index) * 28))
    return fig


def scatter_bubble(
    df: pd.DataFrame,
    x_col: str, y_col: str, size_col: str, color_col: str,
    label_col: str,
    title: str = "",
) -> go.Figure:
    """Bubble/scatter chart for peer comparison."""
    fig = px.scatter(
        df, x=x_col, y=y_col,
        size=size_col, color=color_col,
        text=label_col,
        color_discrete_sequence=list(SECTOR_COLORS.values()),
        size_max=60,
    )
    fig.update_traces(textposition="top center", marker=dict(opacity=0.8, line=dict(width=1, color="#1e293b")))
    _apply_theme(fig, title)
    fig.update_layout(height=420)
    return fig


def gauge_chart(value: float, title: str, min_val: float = 0, max_val: float = 100) -> go.Figure:
    """Gauge chart for scores."""
    if value >= 70:
        bar_color = COLORS["positive"]
    elif value >= 50:
        bar_color = COLORS["warning"]
    elif value >= 35:
        bar_color = COLORS["accent"]
    else:
        bar_color = COLORS["negative"]

    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=value,
        number=dict(font=dict(color=bar_color, size=28)),
        gauge=dict(
            axis=dict(range=[min_val, max_val], tickwidth=1, tickcolor="#334155"),
            bar=dict(color=bar_color, thickness=0.3),
            bgcolor="#111827",
            borderwidth=0,
            steps=[
                dict(range=[0, 40], color="#1a0a0e"),
                dict(range=[40, 55], color="#1a1500"),
                dict(range=[55, 70], color="#0a1a0f"),
                dict(range=[70, 100], color="#0a1a12"),
            ],
            threshold=dict(line=dict(color=bar_color, width=3), thickness=0.75, value=value),
        ),
        title=dict(text=title, font=dict(color="#94a3b8", size=12)),
    ))
    _apply_theme(fig)
    fig.update_layout(height=200, margin=dict(l=20, r=20, t=40, b=20))
    return fig


def waterfall_contribution(labels: list, values: list, title: str = "") -> go.Figure:
    """Waterfall chart for performance attribution."""
    colors = [COLORS["positive"] if v >= 0 else COLORS["negative"] for v in values]
    fig = go.Figure(go.Waterfall(
        orientation="v",
        measure=["relative"] * len(values),
        x=labels,
        y=values,
        connector=dict(line=dict(color="#334155")),
        increasing=dict(marker=dict(color=COLORS["positive"])),
        decreasing=dict(marker=dict(color=COLORS["negative"])),
        text=[f"{v:+.2f}%" for v in values],
        textposition="outside",
    ))
    _apply_theme(fig, title)
    fig.update_layout(height=320, showlegend=False)
    return fig


def sector_allocation_pie(sectors: dict, title: str = "Sector Allocation") -> go.Figure:
    """Donut chart for sector weights."""
    labels = list(sectors.keys())
    values = list(sectors.values())
    colors = [SECTOR_COLORS.get(l, COLORS["neutral"]) for l in labels]

    fig = go.Figure(go.Pie(
        labels=labels, values=values,
        hole=0.55,
        marker=dict(colors=colors, line=dict(width=1, color="#0a0e1a")),
        textinfo="label+percent",
        textfont=dict(size=10),
        hovertemplate="%{label}: %{value:.1f}%<extra></extra>",
    ))
    _apply_theme(fig, title)
    fig.update_layout(height=320, showlegend=False)
    return fig


def macro_indicator_chart(series: pd.Series, label: str, color: str = None, threshold: float = None) -> go.Figure:
    """Line chart for a macro time series."""
    c = color or COLORS["primary"]
    fig = go.Figure(go.Scatter(
        x=series.index, y=series.values,
        mode="lines",
        line=dict(color=c, width=2),
        fill="tozeroy",
        fillcolor=f"rgba({int(c[1:3], 16)},{int(c[3:5], 16)},{int(c[5:7], 16)},0.1)",
    ))
    if threshold is not None:
        fig.add_hline(y=threshold, line_dash="dash", line_color=COLORS["warning"],
                      annotation_text=f"Threshold: {threshold}", annotation_position="right")
    _apply_theme(fig, label)
    fig.update_layout(height=200, showlegend=False, margin=dict(l=40, r=10, t=35, b=30))
    return fig


def sensitivity_heatmap(df: pd.DataFrame, current_price: float = None, title: str = "DCF Sensitivity") -> go.Figure:
    """Sensitivity table as heatmap with current price highlighted."""
    z = df.values.astype(float)
    if current_price:
        # Color by upside/downside to current price
        z_pct = (z / current_price - 1) * 100
    else:
        z_pct = z

    text = [[f"${v:.2f}" for v in row] for row in z]
    text_color = [["#06d6a0" if v >= 0 else "#ef233c" for v in row] for row in (z_pct if current_price else z)]

    fig = go.Figure(go.Heatmap(
        z=z_pct if current_price else z,
        x=df.columns.tolist(),
        y=df.index.tolist(),
        colorscale=[[0, "#3b0a0a"], [0.5, "#1e293b"], [1, "#0a3b1a"]],
        text=text,
        texttemplate="%{text}",
        colorbar=dict(title="vs Current (%)" if current_price else "", thickness=10),
    ))
    _apply_theme(fig, title)
    fig.update_layout(height=300)
    return fig


def risk_radar(scores: dict, ticker: str) -> go.Figure:
    """Radar/spider chart for score breakdown."""
    categories = list(scores.keys())
    values = [scores[k].get("score", 50) for k in categories]
    values_norm = [v / 100 for v in values]

    fig = go.Figure(go.Scatterpolar(
        r=values + [values[0]],
        theta=categories + [categories[0]],
        fill="toself",
        fillcolor="rgba(0, 180, 216, 0.15)",
        line=dict(color=COLORS["primary"], width=2),
        name=ticker,
    ))
    _apply_theme(fig, f"{ticker} — Score Radar")
    fig.update_layout(
        height=350,
        polar=dict(
            bgcolor="#111827",
            radialaxis=dict(visible=True, range=[0, 100], gridcolor="#1e293b", tickfont=dict(size=9)),
            angularaxis=dict(gridcolor="#1e293b", linecolor="#334155"),
        ),
    )
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# ChartFactory — compatibility class wrapper for valuation_center.py
# ─────────────────────────────────────────────────────────────────────────────
class ChartFactory:
    """Thin class wrapper around module-level chart functions."""

    def price_chart(self, *args, **kwargs):      return price_chart(*args, **kwargs)
    def returns_bar(self, *args, **kwargs):      return returns_bar(*args, **kwargs)
    def financial_trend(self, *args, **kwargs):  return financial_trend(*args, **kwargs)
    def heatmap(self, *args, **kwargs):          return heatmap(*args, **kwargs)
    def scatter_bubble(self, *args, **kwargs):   return scatter_bubble(*args, **kwargs)
    def gauge_chart(self, *args, **kwargs):      return gauge_chart(*args, **kwargs)
    def waterfall_contribution(self, *args, **kwargs): return waterfall_contribution(*args, **kwargs)
    def sector_allocation_pie(self, *args, **kwargs):  return sector_allocation_pie(*args, **kwargs)
    def macro_indicator_chart(self, *args, **kwargs):  return macro_indicator_chart(*args, **kwargs)
    def sensitivity_heatmap(self, *args, **kwargs):    return sensitivity_heatmap(*args, **kwargs)
    def risk_radar(self, *args, **kwargs):       return risk_radar(*args, **kwargs)
