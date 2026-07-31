import html
import json
import numbers

import pandas as pd
import requests

BASE_URL = "http://localhost:8080/api"
HISTORY_METRICS = ["open", "high", "low", "close", "average", "volume"]
COLOR_PALETTE = ["#2F4B7C", "#1B7F5C", "#D97706", "#7C3AED", "#B3261E", "#0F766E"]


from datetime import datetime
import zoneinfo

def format_timestamp(ts: str) -> str:
    # Parse the ISO 8601 timestamp
    dt = datetime.fromisoformat(ts)

    # Convert to CET/CEST (Europe/Berlin handles DST automatically)
    berlin = zoneinfo.ZoneInfo("Europe/Berlin")
    dt_local = dt.astimezone(berlin)

    # Format the output
    return dt_local.strftime("%d %b %Y, %H:%M:%S %Z")





def fetch(endpoint, params):
    url = f"{BASE_URL}/{endpoint}"
    response = requests.get(url, params=params, timeout=20)
    response.raise_for_status()
    return response.json()


def _normalize_tickers(tickers):
    if isinstance(tickers, str):
        return [tickers]
    if tickers is None:
        return []
    return [str(ticker) for ticker in tickers]


def load_stock_dashboard_data(tickers, start, end):
    symbol_payloads = []
    for ticker in _normalize_tickers(tickers):
        stats = fetch(
            "stats",
            {
                "ticker": ticker,
                "start": start,
                "end": end,
            },
        )

        history = pd.DataFrame(stats["results"])
        if not history.empty:
            history["date"] = pd.to_datetime(history["date"])

        company = fetch(
            "company",
            {
                "ticker": ticker,
            },
        )

        quote = fetch(
            "quote",
            {
                "ticker": ticker,
            },
        )

        symbol_payloads.append(
            {
                "ticker": ticker,
                "history": history,
                "company": company.get("results", {}),
                "quote": quote.get("results", {}),
            }
        )

    return {
        "tickers": [entry["ticker"] for entry in symbol_payloads],
        "symbols": symbol_payloads,
    }


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------

def _is_number(value):
    return isinstance(value, numbers.Number) and not isinstance(value, bool)


def fmt_number(value, decimals=2):
    """Format a plain numeric value, e.g. price or percent."""
    if value is None:
        return "—"
    if _is_number(value):
        return f"{value:,.{decimals}f}"
    return html.escape(str(value))


def fmt_compact(value):
    """Format large magnitudes (market cap, shares outstanding) with a suffix."""
    if value is None:
        return "—"
    if not _is_number(value):
        return html.escape(str(value))
    abs_v = abs(value)
    if abs_v >= 1e12:
        return f"{value / 1e12:.2f}T"
    if abs_v >= 1e9:
        return f"{value / 1e9:.2f}B"
    if abs_v >= 1e6:
        return f"{value / 1e6:.2f}M"
    if abs_v >= 1e3:
        return f"{value / 1e3:.2f}K"
    return f"{value:,.0f}"


def fmt_label(key):
    """Turn a camelCase / snake_case API field name into a readable label."""
    spaced = "".join(f" {c}" if c.isupper() else c for c in key)
    spaced = spaced.replace("_", " ")
    return spaced.strip().title()


def safe_ticker_id(ticker):
    return "".join(ch if ch.isalnum() else "_" for ch in str(ticker))


# ---------------------------------------------------------------------------
# Section builders
# ---------------------------------------------------------------------------
def build_quote_section(ticker, company, quote):
    print(quote)
    price = quote.get("price")
    currency = quote.get("currency", "")
    change = quote.get("change")
    change_pct = quote.get("changePercent")

    prev_close = quote.get("previousClose")
    if change is None and _is_number(price) and _is_number(prev_close):
        change = price - prev_close
    if change_pct is None and _is_number(change) and _is_number(prev_close) and prev_close:
        change_pct = (change / prev_close) * 100

    is_positive = _is_number(change) and change >= 0
    trend_class = "up" if is_positive else "down"
    trend_sign = "+" if is_positive else ""

    change_html = ""
    if _is_number(change):
        change_html += f"{trend_sign}{fmt_number(change)}"
    if _is_number(change_pct):
        change_html += f" ({trend_sign}{fmt_number(change_pct)}%)"
    if not change_html:
        change_html = "—"

    stat_fields = [
        ("open", "Open"),
        ("previousClose", "Prev. Close"),
        ("dayHigh", "Day High"),
        ("dayLow", "Day Low"),
        ("high", "Day High"),
        ("low", "Day Low"),
        ("yearHigh", "52w High"),
        ("yearLow", "52w Low"),
        ("volume", "Volume"),
        ("marketCap", "Market Cap"),
        ("peRatio", "P/E Ratio"),
    ]
    seen = set()
    stat_cards = []
    for key, label in stat_fields:
        if key in seen or key not in quote or quote.get(key) is None:
            continue
        seen.add(key)
        value = quote[key]
        formatted = fmt_compact(value) if key in ("volume", "marketCap") else fmt_number(value)
        stat_cards.append(
            f'<div class="stat"><span class="stat-label">{html.escape(label)}</span>'
            f'<span class="stat-value">{formatted}</span></div>'
        )

    name = company.get("name", ticker)
    ts = quote.get("timestamp") or quote.get("asOf") or ""
    updated = format_timestamp(ts)

    return f"""
    <section class="card quote-card">
      <div class="quote-head">
        <div>
          <div class="eyebrow">{html.escape(ticker)} &middot; Latest quote</div>
          <h1>{html.escape(str(name))}</h1>
        </div>
        {f'<div class="asof">As of {html.escape(str(updated))}</div>' if updated else ''}
      </div>
      <div class="quote-price-row">
        <span class="price">{fmt_number(price)}</span>
        <span class="currency">{html.escape(str(currency))}</span>
        <span class="change {trend_class}">{change_html}</span>
      </div>
      <div class="stat-grid">
        {''.join(stat_cards) if stat_cards else '<div class="stat-empty">No additional quote fields returned.</div>'}
      </div>
    </section>
    """


def build_company_section(ticker, company):
    description = company.get("description")
    skip_keys = {"description", "name"}

    rows = []
    for key, value in company.items():
        if key in skip_keys or value is None or value == "":
            continue
        if isinstance(value, (dict, list)):
            continue
        rows.append(
            f'<div class="detail-row"><span class="detail-label">{html.escape(fmt_label(key))}</span>'
            f'<span class="detail-value">{html.escape(str(value))}</span></div>'
        )

    description_html = (
        f'<p class="company-description">{html.escape(description)}</p>' if description else ""
    )

    return f"""
    <details class="card company-card">
      <summary>
        <span class="eyebrow">Company profile</span>
        <span class="summary-title">All company data for {html.escape(ticker)}</span>
        <span class="chevron" aria-hidden="true">&#9660;</span>
      </summary>
      <div class="company-body">
        {description_html}
        <div class="detail-grid">
          {''.join(rows) if rows else '<div class="stat-empty">No additional company fields returned.</div>'}
        </div>
      </div>
    </details>
    """


def build_history_chart_payload(symbols, metric="close"):
    traces = []
    for index, symbol in enumerate(symbols):
        history = symbol["history"]
        if history.empty or metric not in history.columns:
            continue
        color = COLOR_PALETTE[index % len(COLOR_PALETTE)]
        traces.append(
            {
                "type": "scatter",
                "mode": "lines",
                "name": symbol["ticker"],
                "x": history["date"].dt.strftime("%Y-%m-%d").tolist(),
                "y": history[metric].tolist(),
                "line": {"color": color, "width": 2},
                "hovertemplate": f"{symbol['ticker']}<br>%{{x}}<br>{fmt_label(metric)}: %{{y:.2f}}<extra></extra>",
            }
        )

    layout = {
        "template": "plotly_white",
        "height": 470,
        "margin": {"l": 50, "r": 20, "t": 30, "b": 40},
        "hovermode": "x unified",
        "xaxis": {"title": "Date"},
        "yaxis": {"title": fmt_label(metric)},
        "legend": {"title": {"text": "Tickets"}},
    }
    return {"data": traces, "layout": layout}


def build_history_section(chart_payloads, metric_options):
    options_html = "".join(
        f'<option value="{metric}" {"selected" if metric == "close" else ""}>{html.escape(fmt_label(metric))}</option>'
        for metric in metric_options
    )
    return f"""
    <section class="card">
      <div class="section-head">
        <div class="eyebrow">Historical data</div>
        <h2>Multi-ticket performance</h2>
      </div>
      <label class="metric-label" for="metric-select">Metric</label>
      <select id="metric-select" class="metric-select">
        {options_html}
      </select>
      <div class="chart-wrap">
        <div id="historical-chart"></div>
      </div>
    </section>
    """


PAGE_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>{title}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;600;700&family=Inter:wght@400;500;600&family=IBM+Plex+Mono:wght@500;600&display=swap" rel="stylesheet">
<style>
  :root {
    --ink: #12151c;
    --muted: #5b6270;
    --line: #e3e6ec;
    --surface: #ffffff;
    --page: #f5f6f8;
    --brand: #2f4b7c;
    --up: #1b7f5c;
    --down: #b3261e;
  }
  * { box-sizing: border-box; }
  body {
    margin: 0;
    padding: 32px 16px 64px;
    background: var(--page);
    color: var(--ink);
    font-family: 'Inter', Helvetica, Arial, sans-serif;
  }
  .dashboard {
    max-width: 980px;
    margin: 0 auto;
    display: flex;
    flex-direction: column;
    gap: 20px;
  }
  .card {
    background: var(--surface);
    border: 1px solid var(--line);
    border-radius: 14px;
    padding: 28px 32px;
  }
  .eyebrow {
    text-transform: uppercase;
    letter-spacing: 0.08em;
    font-size: 12px;
    font-weight: 600;
    color: var(--brand);
  }
  h1 {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 28px;
    margin: 4px 0 0;
  }
  h2 {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 20px;
    margin: 4px 0 0;
  }
  .tab-list {
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
  }
  .tab-button {
    border: 1px solid var(--line);
    background: var(--surface);
    color: var(--ink);
    border-radius: 999px;
    padding: 10px 16px;
    cursor: pointer;
    font-weight: 600;
  }
  .tab-button.active {
    background: var(--brand);
    color: white;
    border-color: var(--brand);
  }
  .tab-panel { display: none; }
  .tab-panel.active { display: block; }
  .quote-head {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    flex-wrap: wrap;
    gap: 8px;
  }
  .asof {
    font-size: 13px;
    color: var(--muted);
    padding-top: 6px;
  }
  .quote-price-row {
    display: flex;
    align-items: baseline;
    gap: 10px;
    margin: 18px 0 4px;
    font-family: 'IBM Plex Mono', monospace;
  }
  .price {
    font-size: 42px;
    font-weight: 600;
  }
  .currency {
    font-size: 16px;
    color: var(--muted);
  }
  .change {
    font-size: 16px;
    font-weight: 600;
    padding: 4px 10px;
    border-radius: 999px;
  }
  .change.up { color: var(--up); background: rgba(27,127,92,0.1); }
  .change.down { color: var(--down); background: rgba(179,38,30,0.1); }
  .stat-grid {
    margin-top: 20px;
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
    gap: 16px;
    border-top: 1px solid var(--line);
    padding-top: 18px;
  }
  .stat { display: flex; flex-direction: column; gap: 4px; }
  .stat-label { font-size: 12px; color: var(--muted); }
  .stat-value { font-family: 'IBM Plex Mono', monospace; font-size: 15px; font-weight: 600; }
  .stat-empty, .company-body .stat-empty { color: var(--muted); font-size: 14px; }
  .section-head { margin-bottom: 8px; }
  .metric-label {
    display: inline-block;
    margin: 8px 0 6px;
    font-size: 13px;
    color: var(--muted);
    font-weight: 600;
  }
  .metric-select {
    border: 1px solid var(--line);
    border-radius: 8px;
    padding: 8px 10px;
    font: inherit;
  }
  .chart-wrap { margin-top: 12px; }
  .company-card summary {
    list-style: none;
    cursor: pointer;
    display: flex;
    align-items: center;
    gap: 12px;
    flex-wrap: wrap;
  }
  .company-card summary::-webkit-details-marker { display: none; }
  .summary-title {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 18px;
    font-weight: 600;
    flex: 1;
  }
  .chevron {
    color: var(--muted);
    transition: transform 0.15s ease;
  }
  .company-card[open] .chevron { transform: rotate(180deg); }
  .company-body { margin-top: 20px; }
  .company-description {
    color: var(--ink);
    line-height: 1.6;
    margin: 0 0 20px;
  }
  .detail-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 14px 24px;
  }
  .detail-row {
    display: flex;
    justify-content: space-between;
    gap: 12px;
    padding: 8px 0;
    border-bottom: 1px solid var(--line);
    font-size: 14px;
  }
  .detail-label { color: var(--muted); }
  .detail-value { font-weight: 500; text-align: right; }
  @media (max-width: 640px) {
    .card { padding: 20px; }
    .price { font-size: 32px; }
  }
</style>
</head>
<body>
  <div class="dashboard">
    <div class="tab-list" role="tablist">
      <button class="tab-button active" type="button" data-tab="historical">Historical</button>
      {ticket_tabs}
    </div>
    <div class="tab-panels">
      <div class="tab-panel active" id="tab-historical">
        {history_section}
      </div>
      {ticket_panels}
    </div>
  </div>
  <script src="https://cdn.plot.ly/plotly-2.32.0.min.js"></script>
  <script>
    const tabButtons = Array.from(document.querySelectorAll('.tab-button'));
    const tabPanels = Array.from(document.querySelectorAll('.tab-panel'));
    tabButtons.forEach((button) => {
      button.addEventListener('click', () => {
        tabButtons.forEach((entry) => entry.classList.remove('active'));
        tabPanels.forEach((panel) => panel.classList.remove('active'));
        button.classList.add('active');
        const target = document.getElementById(`tab-${button.getAttribute('data-tab')}`);
        if (target) {
          target.classList.add('active');
        }
      });
    });

    const metricSelect = document.getElementById('metric-select');
    const historicalChart = document.getElementById('historical-chart');
    const chartPayloads = {chart_payloads};

    if (metricSelect && historicalChart) {
      const renderMetric = (metric) => {
        const payload = chartPayloads[metric];
        if (!payload) {
          return;
        }
        Plotly.react(historicalChart, payload.data, payload.layout, {responsive: true});
      };

      metricSelect.addEventListener('change', (event) => renderMetric(event.target.value));
      renderMetric(metricSelect.value || 'close');
    }
  </script>
</body>
</html>
"""


def create_dashboard(data, filename="stock_dashboard.html"):
    symbols = data.get("symbols", [])
    if not symbols and data.get("history") is not None:
        symbols = [
            {
                "ticker": data.get("ticker", "Stock"),
                "history": data.get("history"),
                "company": data.get("company", {}),
                "quote": data.get("quote", {}),
            }
        ]

    metric_options = [metric for metric in HISTORY_METRICS if metric in {column for symbol in symbols for column in symbol["history"].columns}] or ["close"]
    chart_payloads = {
        metric: build_history_chart_payload(symbols, metric=metric)
        for metric in metric_options
    }

    if symbols:
        chart_payloads_json = json.dumps(chart_payloads, ensure_ascii=False)
        ticket_tabs = "".join(
            f'<button class="tab-button" type="button" data-tab="{safe_ticker_id(symbol["ticker"])}">{html.escape(symbol["ticker"])}</button>'
            for symbol in symbols
        )
        ticket_panels = "".join(
            f'<div class="tab-panel" id="tab-{safe_ticker_id(symbol["ticker"])}">{build_quote_section(symbol["ticker"], symbol["company"], symbol["quote"])}{build_company_section(symbol["ticker"], symbol["company"])} </div>'
            for symbol in symbols
        )
    else:
        chart_payloads_json = "{}"
        ticket_tabs = ""
        ticket_panels = ""

    title = "Stock dashboard"
    if symbols:
        title = f"{', '.join(symbol['ticker'] for symbol in symbols)} dashboard"
    history_section = build_history_section(chart_payloads, metric_options)
    page_html = (
        PAGE_TEMPLATE
        .replace("{title}", title)
        .replace("{ticket_tabs}", ticket_tabs)
        .replace("{history_section}", history_section)
        .replace("{ticket_panels}", ticket_panels)
        .replace("{chart_payloads}", chart_payloads_json)
    )

    with open(filename, "w", encoding="utf-8") as f:
        f.write(page_html)

    print(f"Dashboard written to {filename}")


if __name__ == "__main__":
    tickers = ["AAPL", "MSFT", "GOOG", "NVDA", "AMD"]
    start = "2025-07-01"
    end = "2026-07-30"

    data = load_stock_dashboard_data(
        tickers,
        start,
        end,
    )

    create_dashboard(data)