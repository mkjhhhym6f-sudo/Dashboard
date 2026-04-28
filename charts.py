import plotly.graph_objects as go
import pandas as pd
import numpy as np

from theme import (
    UDES_GOLD,
    BG_DARK,
    BG_CARD,
    BG_DIVIDER,
    TEXT_PRIMARY,
    TEXT_MUTED,
    TEXT_SECONDARY,
    POSITIVE,
    NEGATIVE,
    NEUTRAL,
    INFO,
    SECTOR_COLORS,
    get_plotly_layout,
)


# ---------------------------------------------------------------------------
# Internal helper
# ---------------------------------------------------------------------------

def _apply_theme(fig, title="", height=400):
    """Apply UdeS theme to a Plotly figure without passing height twice."""
    layout = dict(get_plotly_layout(title))
    # get_plotly_layout already puts a 'height' key in the dict.
    # Remove it before adding ours so update_layout never gets height twice.
    layout.pop("height", None)
    layout["height"] = height
    fig.update_layout(**layout)
    return fig


# ---------------------------------------------------------------------------
# Chart functions
# ---------------------------------------------------------------------------

def price_chart(prices, ticker, benchmark=None):
    fig = go.Figure()

    if prices is None:
        return _apply_theme(fig, ticker + " - No data", 380)
    if hasattr(prices, "empty") and prices.empty:
        return _apply_theme(fig, ticker + " - No data", 380)

    if benchmark is not None and hasattr(benchmark, "empty") and not benchmark.empty:
        norm_p = prices / prices.iloc[0] * 100
        norm_b = benchmark / benchmark.iloc[0] * 100
        fig.add_trace(go.Scatter(
            x=norm_p.index,
            y=norm_p.values,
            name=ticker,
            line=dict(color=UDES_GOLD, width=2.5),
        ))
        fig.add_trace(go.Scatter(
            x=norm_b.index,
            y=norm_b.values,
            name="Benchmark",
            line=dict(color=NEUTRAL, width=1.5, dash="dot"),
        ))
        fig.update_yaxes(title_text="Indexed (100)")
    else:
        fig.add_trace(go.Scatter(
            x=prices.index,
            y=prices.values,
            name=ticker,
            line=dict(color=UDES_GOLD, width=2.5),
            fill="tozeroy",
            fillcolor="rgba(255,184,28,0.08)",
        ))
        fig.update_yaxes(title_text="Price ($)")

    return _apply_theme(fig, ticker + " - Price History", 380)


def returns_bar(returns, ticker=""):
    fig = go.Figure()

    if not returns:
        return _apply_theme(fig, "No return data", 300)

    labels = ["1D", "1W", "1M", "3M", "6M", "YTD", "1Y", "3Y", "5Y"]
    keys   = ["1d", "1w", "1m", "3m", "6m", "ytd", "1y", "3y", "5y"]

    valid_labels = []
    values = []
    colors = []

    for label, key in zip(labels, keys):
        v = returns.get(key)
        if v is None:
            continue
        try:
            v_pct = float(v) * 100
        except (TypeError, ValueError):
            continue
        valid_labels.append(label)
        values.append(v_pct)
        colors.append(POSITIVE if v_pct >= 0 else NEGATIVE)

    if not values:
        return _apply_theme(fig, "No return data", 300)

    text_vals = ["{:+.1f}%".format(v) for v in values]

    fig.add_trace(go.Bar(
        x=valid_labels,
        y=values,
        marker=dict(color=colors),
        text=text_vals,
        textposition="outside",
        cliponaxis=False,
    ))
    fig.update_yaxes(title_text="Return (%)")
    fig.update_layout(showlegend=False)
    return _apply_theme(fig, ticker + " - Returns by Period", 300)


def heatmap(df, title="", zmin=-25, zmax=25, fmt="+.1f"):
    if df is None:
        return _apply_theme(go.Figure(), "No data", 360)
    if hasattr(df, "empty") and df.empty:
        return _apply_theme(go.Figure(), "No data", 360)

    fmt_str = "{:" + fmt + "}"
    text = []
    for row in df.values:
        row_text = []
        for v in row:
            if pd.notna(v):
                row_text.append(fmt_str.format(v))
            else:
                row_text.append("")
        text.append(row_text)

    colorscale = [
        [0.0, NEGATIVE],
        [0.4, "#3D1A1A"],
        [0.5, BG_CARD],
        [0.6, "#1A3D2E"],
        [1.0, POSITIVE],
    ]

    fig = go.Figure(go.Heatmap(
        z=df.values,
        x=df.columns.tolist(),
        y=df.index.tolist(),
        colorscale=colorscale,
        zmin=zmin,
        zmax=zmax,
        zmid=0,
        text=text,
        texttemplate="%{text}",
        textfont=dict(size=11, color=TEXT_PRIMARY),
        colorbar=dict(
            thickness=10,
            len=0.8,
            tickfont=dict(color=TEXT_MUTED, size=10),
        ),
    ))

    h = max(360, 22 * len(df.index) + 100)
    return _apply_theme(fig, title, h)


def sector_allocation_pie(weights, title="Sector Allocation"):
    if not weights:
        return _apply_theme(go.Figure(), "No data", 380)

    sectors = list(weights.keys())
    values  = list(weights.values())
    colors  = [SECTOR_COLORS.get(s, NEUTRAL) for s in sectors]

    annotation_text = "<b>{}</b><br>SECTORS".format(len(sectors))

    fig = go.Figure(go.Pie(
        labels=sectors,
        values=values,
        hole=0.55,
        marker=dict(colors=colors, line=dict(color=BG_DARK, width=2)),
        textfont=dict(size=11, color=TEXT_PRIMARY),
        textposition="outside",
        textinfo="label+percent",
        showlegend=False,
    ))

    fig.update_layout(annotations=[dict(
        text=annotation_text,
        x=0.5,
        y=0.5,
        font=dict(size=20, color=UDES_GOLD),
        showarrow=False,
    )])

    return _apply_theme(fig, title, 380)


def gauge_chart(value, title, min_val=0, max_val=100):
    if value is None:
        value = 0

    try:
        value = float(value)
    except (TypeError, ValueError):
        value = 0

    if value >= 70:
        bar_color = POSITIVE
    elif value >= 55:
        bar_color = UDES_GOLD
    elif value >= 40:
        bar_color = "#E07B39"
    else:
        bar_color = NEGATIVE

    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=value,
        title={"text": title, "font": {"size": 13, "color": TEXT_SECONDARY}},
        number={"font": {"size": 36, "color": TEXT_PRIMARY}},
        gauge={
            "axis": {
                "range": [min_val, max_val],
                "tickfont": {"color": TEXT_MUTED, "size": 10},
            },
            "bar": {"color": bar_color, "thickness": 0.8},
            "bgcolor": BG_CARD,
            "borderwidth": 1,
            "bordercolor": BG_DIVIDER,
            "steps": [
                {"range": [0,  40],  "color": "#3D1A1A"},
                {"range": [40, 55],  "color": "#3D2A1A"},
                {"range": [55, 70],  "color": "#2A3D1A"},
                {"range": [70, 100], "color": "#1A3D2E"},
            ],
            "threshold": {
                "line": {"color": UDES_GOLD, "width": 3},
                "thickness": 0.85,
                "value": value,
            },
        },
    ))

    # gauge_chart manages its own layout (no axes needed)
    fig.update_layout(
        paper_bgcolor=BG_CARD,
        font={"color": TEXT_PRIMARY},
        height=240,
        margin=dict(l=10, r=10, t=40, b=10),
    )
    return fig


def macro_indicator_chart(series, title, color=None, threshold=None):
    fig = go.Figure()

    if series is None:
        return _apply_theme(fig, title + " - No data", 280)
    if hasattr(series, "empty") and series.empty:
        return _apply_theme(fig, title + " - No data", 280)

    line_color = color if color else UDES_GOLD
    fill_color = line_color + "1A"

    fig.add_trace(go.Scatter(
        x=series.index,
        y=series.values,
        line=dict(color=line_color, width=2),
        fill="tozeroy",
        fillcolor=fill_color,
        name=title,
    ))

    if threshold is not None:
        fig.add_hline(
            y=threshold,
            line_dash="dot",
            line_color=NEUTRAL,
            annotation_text="Threshold: {}".format(threshold),
            annotation_position="top right",
        )

    return _apply_theme(fig, title, 280)


def scatter_bubble(df, x_col, y_col, size_col, color_col, label_col, title=""):
    fig = go.Figure()

    if df is None:
        return _apply_theme(fig, "No data", 440)
    if hasattr(df, "empty") and df.empty:
        return _apply_theme(fig, "No data", 440)

    for sector in df[color_col].unique():
        sub   = df[df[color_col] == sector]
        color = SECTOR_COLORS.get(sector, NEUTRAL)
        sizes = sub[size_col].fillna(1e9) / 1e9 * 5
        sizes = sizes.clip(lower=8, upper=50)

        fig.add_trace(go.Scatter(
            x=sub[x_col],
            y=sub[y_col],
            mode="markers+text",
            marker=dict(
                size=sizes,
                color=color,
                line=dict(width=1, color=TEXT_PRIMARY),
                opacity=0.85,
            ),
            text=sub[label_col],
            textposition="top center",
            textfont=dict(size=10, color=TEXT_PRIMARY),
            name=sector,
        ))

    fig.update_layout(showlegend=False)
    fig.update_xaxes(title_text=x_col)
    fig.update_yaxes(title_text=y_col)
    return _apply_theme(fig, title, 440)


def sensitivity_heatmap(df, current_price=None, title="Valuation Sensitivity"):
    if df is None:
        return _apply_theme(go.Figure(), "No data", 380)
    if hasattr(df, "empty") and df.empty:
        return _apply_theme(go.Figure(), "No data", 380)

    text = []
    for row in df.values:
        row_text = []
        for v in row:
            if v:
                row_text.append("${:.0f}".format(v))
            else:
                row_text.append("-")
        text.append(row_text)

    fig = go.Figure(go.Heatmap(
        z=df.values,
        x=df.columns.tolist(),
        y=df.index.tolist(),
        colorscale=[[0.0, NEGATIVE], [0.5, BG_CARD], [1.0, POSITIVE]],
        text=text,
        texttemplate="%{text}",
        textfont=dict(size=11, color=TEXT_PRIMARY),
        colorbar=dict(
            title="$/share",
            thickness=10,
            len=0.8,
            tickfont=dict(color=TEXT_MUTED, size=10),
        ),
    ))

    if current_price is not None:
        fig.add_annotation(
            xref="paper",
            yref="paper",
            x=1.15,
            y=1.05,
            text="<b>Current: ${:.2f}</b>".format(current_price),
            showarrow=False,
            font=dict(color=UDES_GOLD, size=11),
            align="right",
        )

    return _apply_theme(fig, title, 380)
