"""
Generates the ERD diagram using matplotlib (no Graphviz binary required).
Output: reports/figures/erd_diagram.png
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUTPUT_PATH = ROOT / "reports" / "figures" / "erd_diagram.png"
OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

fig, ax = plt.subplots(figsize=(14, 7))
ax.set_xlim(0, 14)
ax.set_ylim(0, 7)
ax.axis("off")
fig.patch.set_facecolor("#f8fafc")

HEADER_COLOR = "#2563eb"
PK_COLOR     = "#dbeafe"
FK_COLOR     = "#fef9c3"
ROW_COLOR    = "#ffffff"
BORDER_COLOR = "#64748b"
TEXT_COLOR   = "#1e293b"
FONT         = "monospace"

def draw_table(ax, x, y, title, columns):
    """
    columns: list of (label, kind) where kind in {'pk','fk','col'}
    Returns bottom-y of the table.
    """
    col_w, row_h = 3.2, 0.38
    n = len(columns)
    total_h = row_h + n * row_h  # header + rows

    # shadow
    shadow = mpatches.FancyBboxPatch(
        (x + 0.06, y - total_h - 0.06), col_w, total_h,
        boxstyle="round,pad=0.05", linewidth=0,
        facecolor="#00000018", zorder=1
    )
    ax.add_patch(shadow)

    # header
    header = mpatches.FancyBboxPatch(
        (x, y - row_h), col_w, row_h,
        boxstyle="round,pad=0.0", linewidth=1.5,
        edgecolor=BORDER_COLOR, facecolor=HEADER_COLOR, zorder=2
    )
    ax.add_patch(header)
    ax.text(x + col_w / 2, y - row_h / 2, title,
            ha="center", va="center", fontsize=10, fontweight="bold",
            color="white", fontfamily=FONT, zorder=3)

    # rows
    for i, (label, kind) in enumerate(columns):
        ry = y - row_h - (i + 1) * row_h
        bg = PK_COLOR if kind == "pk" else FK_COLOR if kind == "fk" else ROW_COLOR
        rect = mpatches.FancyBboxPatch(
            (x, ry), col_w, row_h,
            boxstyle="round,pad=0.0", linewidth=1,
            edgecolor=BORDER_COLOR, facecolor=bg, zorder=2
        )
        ax.add_patch(rect)
        prefix = "PK " if kind == "pk" else "FK " if kind == "fk" else "     "
        ax.text(x + 0.14, ry + row_h / 2, prefix + label,
                ha="left", va="center", fontsize=7.5,
                color=TEXT_COLOR, fontfamily=FONT, zorder=3)

    return y - total_h  # bottom y


def arrow(ax, x1, y1, x2, y2, label="1 : N"):
    mid_x = (x1 + x2) / 2
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle="-|>", color=HEADER_COLOR,
                                lw=1.8, connectionstyle="arc3,rad=0.0"))
    ax.text(mid_x, (y1 + y2) / 2 + 0.1, label,
            ha="center", va="bottom", fontsize=8,
            color=HEADER_COLOR, fontweight="bold")


# ── stores table (centre-left)
stores_cols = [
    ("store_id  INT", "pk"),
    ("store_type  CHAR(1)", "col"),
    ("size_sqft  INT", "col"),
]
draw_table(ax, x=0.5, y=5.8, title="stores", columns=stores_cols)
stores_right_x = 0.5 + 3.2   # 3.7
stores_mid_y   = 5.8 - (0.38 + 3 * 0.38 / 2)  # rough mid

# ── store_features table (top-right)
feat_cols = [
    ("feature_id  INT", "pk"),
    ("store_id  INT", "fk"),
    ("record_date  DATE", "col"),
    ("temperature  DECIMAL", "col"),
    ("fuel_price  DECIMAL", "col"),
    ("markdown1..5  DECIMAL", "col"),
    ("cpi  DECIMAL", "col"),
    ("unemployment  DECIMAL", "col"),
    ("is_holiday  BOOL", "col"),
]
draw_table(ax, x=5.5, y=6.8, title="store_features", columns=feat_cols)
feat_left_x = 5.5
feat_mid_y  = 6.8 - (0.38 + 9 * 0.38 / 2)

# ── sales table (bottom-right)
sales_cols = [
    ("sale_id  INT", "pk"),
    ("store_id  INT", "fk"),
    ("record_date  DATE", "col"),
    ("weekly_sales  DECIMAL", "col"),
    ("is_holiday  BOOL", "col"),
]
draw_table(ax, x=5.5, y=3.0, title="sales", columns=sales_cols)
sales_left_x = 5.5
sales_mid_y  = 3.0 - (0.38 + 5 * 0.38 / 2)

# ── arrows
arrow(ax, stores_right_x, 5.05, feat_left_x, feat_mid_y, "1 : N")
arrow(ax, stores_right_x, 4.55, sales_left_x, sales_mid_y, "1 : N")

# ── title
ax.text(7, 0.4, "ERD — Walmart Store Sales Forecasting (Task 2)",
        ha="center", va="center", fontsize=12, fontweight="bold",
        color=TEXT_COLOR)

# ── legend
for bx, color, label in [(0.5, PK_COLOR, "Primary Key"), (2.5, FK_COLOR, "Foreign Key"), (4.5, ROW_COLOR, "Column")]:
    rect = mpatches.FancyBboxPatch((bx, 0.05), 0.35, 0.28,
                                    boxstyle="round,pad=0.02", linewidth=1,
                                    edgecolor=BORDER_COLOR, facecolor=color)
    ax.add_patch(rect)
    ax.text(bx + 0.45, 0.19, label, va="center", fontsize=8, color=TEXT_COLOR)

plt.tight_layout(pad=0.3)
plt.savefig(OUTPUT_PATH, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
plt.close()
print(f"ERD saved to {OUTPUT_PATH}")
