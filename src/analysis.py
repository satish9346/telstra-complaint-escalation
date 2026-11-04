"""
Telstra complaint escalation analysis.

Reads the four CSVs in data/, prints the key numbers used in the README,
and writes the charts in figures/ (PNG for the README, HTML for the
interactive dashboard).

Run from the repo root:
    pip install -r requirements.txt
    python src/analysis.py
"""
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
FIG = ROOT / "figures"
FIG.mkdir(exist_ok=True)

TELSTRA = "#0b3d91"
MUTED = "#a9b4c2"
ALERT = "#c0392b"

plt.rcParams.update({
    "font.size": 11,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.titleweight": "bold",
    "axes.titlelocation": "left",
})


def load():
    q = pd.read_csv(DATA / "telstra_quarterly.csv")
    q["escalation_rate_pct"] = q["tio_escalations"] / q["complaints"] * 100
    acma = pd.read_csv(DATA / "acma_carrier_comparison.csv")
    cats = pd.read_csv(DATA / "tio_unresolved_by_category.csv")
    net = pd.read_csv(DATA / "tio_network_split_q3fy26.csv")
    return q, acma, cats, net


def key_numbers(q, acma, cats, net):
    latest = acma[acma.period == "Jan-Mar 2026"].set_index("carrier")
    nbn_share = net.on_nbn.sum() / (net.on_nbn.sum() + net.telstra_network.sum())
    top = cats.sort_values("q3_fy26", ascending=False).iloc[0]
    print("Quarterly escalation rate (%):")
    print(q[["quarter", "complaints", "tio_escalations", "escalation_rate_pct"]].round(2).to_string(index=False))
    print(f"\nComplaint volume change, first to last quarter: "
          f"{(q.complaints.iloc[-1] / q.complaints.iloc[0] - 1) * 100:.1f}%")
    print(f"Escalation rate range: {q.escalation_rate_pct.min():.2f}% to {q.escalation_rate_pct.max():.2f}%")
    print(f"\nJan-Mar 2026 escalation rate: Telstra {latest.loc['Telstra', 'escalation_rate_pct']}%, "
          f"Optus {latest.loc['Optus', 'escalation_rate_pct']}%, TPG {latest.loc['TPG Telecom', 'escalation_rate_pct']}%, "
          f"industry {latest.loc['Industry average', 'escalation_rate_pct']}%")
    print(f"Top unresolved category Q3 FY26: {top.category} ({top.q3_fy26}), "
          f"{top.q3_fy26 / cats.q3_fy26.iloc[1]:.1f}x the next")
    print(f"Unresolved complaints on the NBN network, Q3 FY26: {nbn_share:.1%}")


def chart_trend(q):
    fig, ax1 = plt.subplots(figsize=(9, 4.8))
    ax1.bar(q.quarter, q.complaints, color=MUTED, label="Complaints")
    ax1.set_ylabel("Complaints per quarter")
    ax1.yaxis.set_major_formatter(lambda v, _: f"{v/1000:.0f}k")
    ax2 = ax1.twinx()
    ax2.plot(q.quarter, q.escalation_rate_pct, color=TELSTRA, marker="o", lw=2.2, label="Escalated to TIO (%)")
    ax2.set_ylim(0, 12)
    ax2.set_ylabel("Escalated to the TIO (%)")
    ax2.spines["right"].set_visible(True)
    for x, y in zip(q.quarter, q.escalation_rate_pct):
        ax2.annotate(f"{y:.1f}%", (x, y), textcoords="offset points", xytext=(0, 8), ha="center", fontsize=9, color=TELSTRA)
    ax1.set_title("Complaints fell, but the share escalating to the ombudsman did not")
    fig.text(0.01, 0.01, "Source: Telstra complaint-handling performance reports, Q4 FY24 to Q3 FY26", fontsize=8, color="grey")
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(FIG / "01_trend.png", dpi=200)
    plt.close(fig)


def chart_carriers(acma):
    d = acma[acma.period == "Jan-Mar 2026"].sort_values("escalation_rate_pct")
    colors = [TELSTRA if c == "Telstra" else (MUTED if c != "Industry average" else "#6c7a89") for c in d.carrier]
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.barh(d.carrier, d.escalation_rate_pct, color=colors)
    for y, (v, per) in enumerate(zip(d.escalation_rate_pct, d.complaints_per_10000_services)):
        label = f"{v:.1f}%" + (f"   ({per:.0f} complaints per 10k services)" if pd.notna(per) else "")
        ax.text(v + 0.15, y, label, va="center", fontsize=9)
    ax.set_xlim(0, 13)
    ax.set_xlabel("Complaints referred to the TIO (%)")
    ax.set_title("Fewest complaints per customer, highest escalation rate")
    fig.text(0.01, 0.01, "Source: ACMA Telecommunications consumer complaints, Jan-Mar 2026", fontsize=8, color="grey")
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.savefig(FIG / "02_carriers.png", dpi=200)
    plt.close(fig)


def chart_categories(cats):
    d = cats.sort_values("q3_fy26")
    colors = [ALERT if i == len(d) - 1 else TELSTRA for i in range(len(d))]
    fig, ax = plt.subplots(figsize=(9, 4.8))
    ax.barh(d.category, d.q3_fy26, color=colors)
    ax.scatter(d.q2_fy26, d.category, color="black", s=14, zorder=3, label="Previous quarter (Q2 FY26)")
    for y, (v, prev) in enumerate(zip(d.q3_fy26, d.q2_fy26)):
        ax.text(max(v, prev) + 14, y, f"{v}", va="center", fontsize=9)
    ax.legend(frameon=False, loc="lower right", fontsize=9)
    ax.set_xlabel("Unresolved Telstra complaints at the TIO, Q3 FY26")
    ax.set_title("Delayed action is double any other complaint category")
    fig.text(0.01, 0.01, "Source: TIO Data Hive, filtered to Telstra", fontsize=8, color="grey")
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(FIG / "03_categories.png", dpi=200)
    plt.close(fig)


def chart_network(net):
    d = net.copy()
    d["total"] = d.on_nbn + d.telstra_network
    d = d.sort_values("total")
    fig, ax = plt.subplots(figsize=(8, 3.6))
    ax.barh(d.service_type, d.telstra_network, color=TELSTRA, label="Fault on Telstra's own network")
    ax.barh(d.service_type, d.on_nbn, left=d.telstra_network, color=MUTED, label="Fault on the NBN")
    ax.legend(frameon=False, fontsize=9, loc="lower right")
    ax.set_xlabel("Unresolved complaints, Q3 FY26")
    ax.set_title("Most unresolved complaints are on Telstra's own network")
    fig.text(0.01, 0.01, "Source: TIO Data Hive, filtered to Telstra", fontsize=8, color="grey")
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.savefig(FIG / "04_network.png", dpi=200)
    plt.close(fig)


def dashboard(q, acma, cats, net):
    """One self-contained interactive HTML page for GitHub Pages."""
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    latest = acma[acma.period == "Jan-Mar 2026"].sort_values("escalation_rate_pct")
    c = cats.sort_values("q3_fy26")
    n = net.assign(total=net.on_nbn + net.telstra_network).sort_values("total")

    fig = make_subplots(
        rows=2, cols=2, vertical_spacing=0.16, horizontal_spacing=0.22,
        specs=[[{"secondary_y": True}, {}], [{}, {}]],
        subplot_titles=(
            "Complaints and TIO escalation rate by quarter",
            "Escalation rate vs other carriers (Jan-Mar 2026)",
            "Unresolved complaints by category (Q3 FY26)",
            "Where the fault sits (Q3 FY26)",
        ),
    )
    fig.add_bar(x=q.quarter, y=q.complaints, name="Complaints", marker_color=MUTED, row=1, col=1)
    fig.add_scatter(x=q.quarter, y=q.escalation_rate_pct.round(2), name="Escalated (%)", mode="lines+markers",
                    line=dict(color=TELSTRA, width=3), row=1, col=1, secondary_y=True)
    fig.add_bar(y=latest.carrier, x=latest.escalation_rate_pct, orientation="h", name="Escalation rate (%)",
                marker_color=[TELSTRA if v == "Telstra" else MUTED for v in latest.carrier],
                customdata=latest.complaints_per_10000_services,
                hovertemplate="%{y}: %{x}% escalated<br>%{customdata} complaints per 10k services<extra></extra>",
                row=1, col=2)
    fig.add_bar(y=c.category, x=c.q2_fy26, orientation="h", name="Q2 FY26", marker_color=MUTED, row=2, col=1)
    fig.add_bar(y=c.category, x=c.q3_fy26, orientation="h", name="Q3 FY26", marker_color=TELSTRA, row=2, col=1)
    fig.add_bar(y=n.service_type, x=n.telstra_network, orientation="h", name="Telstra network", marker_color=TELSTRA, row=2, col=2)
    fig.add_bar(y=n.service_type, x=n.on_nbn, orientation="h", name="NBN", marker_color=MUTED, row=2, col=2)
    fig.update_layout(
        barmode="group", height=900, template="plotly_white",
        title=dict(text="<b>Telstra complaint escalation</b><br><sup>Fewer complaints, but the share reaching the ombudsman hasn't fallen</sup>", x=0.02),
        legend=dict(orientation="h", y=-0.08), margin=dict(l=40, r=30, t=110, b=60),
    )
    fig.update_yaxes(title_text="Escalated (%)", range=[0, 12], secondary_y=True, row=1, col=1)
    fig.update_layout(barmode="stack")
    fig.data[3].update(offsetgroup="a"); fig.data[4].update(offsetgroup="b")
    fig.write_html(FIG / "dashboard.html", include_plotlyjs="cdn", full_html=True)


if __name__ == "__main__":
    q, acma, cats, net = load()
    key_numbers(q, acma, cats, net)
    chart_trend(q)
    chart_carriers(acma)
    chart_categories(cats)
    chart_network(net)
    dashboard(q, acma, cats, net)
    print(f"\nCharts written to {FIG}")
