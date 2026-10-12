"""Shared chart styling: reference palette, light mode (categorical slots 1-3 validated for all pairs)."""
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

SURFACE, INK, INK_2, MUTED, GRID, AXIS = "#fcfcfb", "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7"
BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"


def style_axes(ax) -> None:
    """Recessive grid and axes, thin spines, muted ticks."""
    ax.set_facecolor(SURFACE)
    ax.grid(axis="y", color=GRID, lw=0.6)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(AXIS)
    ax.tick_params(colors=MUTED, labelsize=8, labelcolor=INK_2)


def new_figure(rows: int, height_per_row: float = 2.4, width: float = 11.0, sharex: bool = True):
    fig, axes = plt.subplots(rows, 1, figsize=(width, height_per_row * rows), sharex=sharex,
                             squeeze=False, facecolor=SURFACE)
    for ax in axes[:, 0]:
        style_axes(ax)
    return fig, axes[:, 0]


def save(fig, path, title: str) -> None:
    fig.suptitle(title, x=0.01, ha="left", color=INK, fontsize=11)
    fig.tight_layout()
    fig.savefig(path, dpi=130, facecolor=SURFACE)
    plt.close(fig)
