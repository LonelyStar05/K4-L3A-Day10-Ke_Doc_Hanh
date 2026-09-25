"""Static observability dashboard (bonus B1).

Reads the artifacts produced by the pipelines (GX quality reports, freshness
reports, clean datasets, evaluation metrics, corruption log) and renders one
self-contained HTML page: quality-gate status, paper-age distribution against
the freshness SLA, drift alerts versus the baseline and metric comparison.

Run after ``pipelines.phase1`` and ``pipelines.corruption_flow``:

    python -m observability.dashboard
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from html import escape
from pathlib import Path
from typing import Any

import pandas as pd

from core.config import Settings, load_settings
from core.utils import read_json, write_text

STATES = ("baseline", "corrupted", "repaired")
METRICS = ("retrieval_hit_rate", "mean_token_f1", "judge_accuracy")
AGE_BUCKETS = ((0, 30, "0–30"), (31, 90, "31–90"), (91, 180, "91–180"), (181, 365, "181–365"), (366, None, "> 365"))
METRIC_DROP_ALERT = 0.10
MEDIAN_AGE_SHIFT_ALERT = 60


@dataclass
class StateSnapshot:
    name: str
    quality: dict[str, Any] | None = None
    freshness: dict[str, Any] | None = None
    metrics: dict[str, Any] | None = None
    ages: list[int] = field(default_factory=list)

    @property
    def available(self) -> bool:
        return self.quality is not None


@dataclass
class Alert:
    level: str  # "critical" | "warning" | "ok"
    state: str
    message: str


def _read_optional(path: Path) -> dict[str, Any] | None:
    return read_json(path) if path.exists() else None


def load_snapshots(settings: Settings) -> dict[str, StateSnapshot]:
    paths = settings.paths
    clean_files = {
        "baseline": paths.clean_csv,
        "corrupted": paths.corrupted_clean_csv,
        "repaired": paths.repaired_clean_csv,
    }
    metric_files = {
        "baseline": paths.baseline_metrics,
        "corrupted": paths.corrupted_metrics,
        "repaired": paths.repaired_metrics,
    }
    snapshots: dict[str, StateSnapshot] = {}
    for state in STATES:
        snapshot = StateSnapshot(
            name=state,
            quality=_read_optional(paths.quality_dir / f"{state}_quality_report.json"),
            freshness=_read_optional(paths.quality_dir / f"{state}_freshness_report.json"),
            metrics=_read_optional(metric_files[state]),
        )
        if clean_files[state].exists():
            ages = pd.to_numeric(pd.read_csv(clean_files[state])["age_days"], errors="coerce")
            snapshot.ages = [int(age) for age in ages.dropna()]
        snapshots[state] = snapshot
    return snapshots


def age_histogram(ages: list[int]) -> list[int]:
    counts = []
    for low, high, _ in AGE_BUCKETS:
        counts.append(sum(1 for age in ages if age >= low and (high is None or age <= high)))
    return counts


def _median(values: list[int]) -> float | None:
    return float(pd.Series(values).median()) if values else None


def detect_alerts(snapshots: dict[str, StateSnapshot]) -> list[Alert]:
    """Compare every state against its own SLA and against the baseline."""
    alerts: list[Alert] = []
    baseline = snapshots["baseline"]
    base_median = _median(baseline.ages)
    for state in STATES:
        snap = snapshots[state]
        if not snap.available:
            alerts.append(Alert("warning", state, "Chưa có quality report — hãy chạy pipeline tương ứng."))
            continue
        state_alerts_before = len(alerts)
        for check in snap.quality.get("checks", []):
            if not check["success"]:
                alerts.append(
                    Alert("critical", state, f"GX check `{check['name']}` FAIL (observed: {check['observed_value']}).")
                )
        fresh = snap.freshness or snap.quality.get("freshness") or {}
        if fresh and not fresh.get("is_fresh", True):
            alerts.append(
                Alert(
                    "critical",
                    state,
                    f"Vi phạm Freshness SLA: {fresh['stale_ratio']:.1%} bài báo có tuổi > "
                    f"{fresh['freshness_threshold_days']} ngày (ngưỡng {fresh['max_allowed_stale_ratio']:.0%}).",
                )
            )
        if state != "baseline":
            median = _median(snap.ages)
            if base_median is not None and median is not None and abs(median - base_median) >= MEDIAN_AGE_SHIFT_ALERT:
                alerts.append(
                    Alert(
                        "warning",
                        state,
                        f"Drift phân bố tuổi: median {median:.0f} ngày so với baseline {base_median:.0f} ngày.",
                    )
                )
            if snap.metrics and baseline.metrics:
                for metric in METRICS:
                    drop = float(baseline.metrics.get(metric, 0)) - float(snap.metrics.get(metric, 0))
                    if drop >= METRIC_DROP_ALERT:
                        alerts.append(
                            Alert(
                                "critical",
                                state,
                                f"`{metric}` giảm {drop:.3f} so với baseline "
                                f"({baseline.metrics[metric]:.3f} → {snap.metrics[metric]:.3f}).",
                            )
                        )
        if len(alerts) == state_alerts_before:
            alerts.append(Alert("ok", state, "Tất cả GX checks, Freshness SLA và metrics đều trong ngưỡng."))
    return alerts


# --------------------------------------------------------------------------- rendering


def _badge(ok: bool | None, yes: str = "PASS", no: str = "FAIL") -> str:
    if ok is None:
        return '<span class="badge muted">N/A</span>'
    return f'<span class="badge {"ok" if ok else "bad"}">{yes if ok else no}</span>'


def _fmt(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:.3f}"
    if isinstance(value, dict):
        return ", ".join(f"{k}: {v}" for k, v in value.items())
    return escape(str(value))


def _state_card(snap: StateSnapshot) -> str:
    if not snap.available:
        return f'<div class="card"><h3>{snap.name}</h3><p class="muted">Chưa có dữ liệu.</p></div>'
    fresh = snap.freshness or snap.quality.get("freshness", {})
    metrics = snap.metrics or {}
    rows = "".join(
        f"<div class='kv'><span>{label}</span><b>{value}</b></div>"
        for label, value in [
            ("Số dòng", snap.quality.get("row_count", "–")),
            ("Stale ratio", f"{fresh.get('stale_ratio', 0):.1%}" if fresh else "–"),
            ("Hit rate", _fmt(float(metrics["retrieval_hit_rate"])) if metrics else "–"),
            ("Token F1", _fmt(float(metrics["mean_token_f1"])) if metrics else "–"),
        ]
    )
    return f"""<div class="card state">
  <div class="card-head"><h3>{snap.name}</h3></div>
  <div class="badges">GX gate {_badge(snap.quality.get("success"))}
    Freshness {_badge(fresh.get("is_fresh") if fresh else None, "FRESH", "STALE")}</div>
  {rows}
</div>"""


def _checks_table(snapshots: dict[str, StateSnapshot]) -> str:
    names: list[str] = []
    for snap in snapshots.values():
        for check in (snap.quality or {}).get("checks", []):
            if check["name"] not in names:
                names.append(check["name"])
    header = "".join(f"<th class='st'>{s}</th>" for s in STATES)
    body = ""
    for name in names:
        cells = ""
        for state in STATES:
            check = next((c for c in (snapshots[state].quality or {}).get("checks", []) if c["name"] == name), None)
            if check is None:
                cells += "<td class='muted'>–</td>"
            else:
                cells += f"<td>{_badge(check['success'])}<div class='obs'>{_fmt(check['observed_value'])}</div></td>"
        body += f"<tr><td><code>{escape(name)}</code></td>{cells}</tr>"
    return f"<table><thead><tr><th>Expectation</th>{header}</tr></thead><tbody>{body}</tbody></table>"


def _grouped_bars_svg(
    categories: list[str],
    series: dict[str, list[float]],
    y_max: float,
    y_label: str,
    highlight_from: int | None = None,
    value_fmt=lambda v: f"{v:g}",
) -> str:
    width, height = 640, 260
    left, right, top, bottom = 44, 12, 16, 44
    plot_w, plot_h = width - left - right, height - top - bottom
    y_max = y_max or 1
    group_w = plot_w / len(categories)
    n = len(series)
    bar_w = min(26, (group_w - 16) / max(n, 1))
    parts = [f'<svg viewBox="0 0 {width} {height}" role="img" aria-label="{escape(y_label)}">']
    if highlight_from is not None:
        x = left + group_w * highlight_from
        parts.append(
            f'<rect x="{x:.1f}" y="{top}" width="{left + plot_w - x:.1f}" height="{plot_h}" class="zone"/>'
            f'<text x="{left + plot_w - 4:.1f}" y="{top + 12}" text-anchor="end" class="zone-label">vượt SLA 180 ngày</text>'
        )
    for i in range(5):
        value = y_max * i / 4
        y = top + plot_h - plot_h * i / 4
        parts.append(f'<line x1="{left}" x2="{left + plot_w}" y1="{y:.1f}" y2="{y:.1f}" class="grid"/>')
        parts.append(f'<text x="{left - 6}" y="{y + 4:.1f}" text-anchor="end" class="tick">{value_fmt(value)}</text>')
    for gi, category in enumerate(categories):
        gx = left + group_w * gi + (group_w - bar_w * n) / 2
        for si, (name, values) in enumerate(series.items()):
            value = values[gi]
            bh = plot_h * value / y_max
            x = gx + si * bar_w
            y = top + plot_h - bh
            parts.append(
                f'<rect x="{x + 1:.1f}" y="{y:.1f}" width="{bar_w - 2:.1f}" height="{bh:.1f}" rx="2" '
                f'class="s-{name}"><title>{name} · {category}: {value_fmt(value)}</title></rect>'
            )
        parts.append(
            f'<text x="{left + group_w * gi + group_w / 2:.1f}" y="{top + plot_h + 18}" text-anchor="middle" '
            f'class="tick">{escape(category)}</text>'
        )
    parts.append(
        f'<text x="{left + plot_w / 2:.1f}" y="{height - 6}" text-anchor="middle" class="axis">{escape(y_label)}</text>'
    )
    parts.append("</svg>")
    return "".join(parts)


def _legend(names: list[str]) -> str:
    return '<div class="legend">' + "".join(f'<span><i class="s-{n}"></i>{n}</span>' for n in names) + "</div>"


def _age_chart(snapshots: dict[str, StateSnapshot]) -> str:
    series = {s: age_histogram(snapshots[s].ages) for s in STATES if snapshots[s].ages}
    if not series:
        return "<p class='muted'>Chưa có dữ liệu clean.</p>"
    y_max = max(max(v) for v in series.values())
    y_max = max(4, ((y_max + 3) // 4) * 4)
    first_stale_bucket = next(i for i, (low, _, _) in enumerate(AGE_BUCKETS) if low > 180)
    svg = _grouped_bars_svg(
        [label for *_, label in AGE_BUCKETS],
        {k: [float(x) for x in v] for k, v in series.items()},
        y_max,
        "Tuổi bài báo (ngày) — số bài theo nhóm",
        highlight_from=first_stale_bucket,
        value_fmt=lambda v: f"{v:.0f}",
    )
    medians = " · ".join(f"{s}: median {_median(snapshots[s].ages):.0f} ngày" for s in series)
    return _legend(list(series)) + svg + f"<p class='note'>{medians}</p>"


def _metrics_chart(snapshots: dict[str, StateSnapshot]) -> str:
    series = {s: [float(snapshots[s].metrics[m]) for m in METRICS] for s in STATES if snapshots[s].metrics}
    if not series:
        return "<p class='muted'>Chưa có metrics.</p>"
    svg = _grouped_bars_svg(list(METRICS), series, 1.0, "Metric (0–1)", value_fmt=lambda v: f"{v:.2f}")
    return _legend(list(series)) + svg


def _alerts_html(alerts: list[Alert]) -> str:
    icon = {"critical": "●", "warning": "▲", "ok": "✓"}
    items = "".join(
        f'<li class="alert {a.level}"><span class="ic">{icon[a.level]}</span>'
        f"<b>{a.state}</b><span>{escape(a.message).replace('`', '')}</span></li>"
        for a in alerts
    )
    return f"<ul class='alerts'>{items}</ul>"


def _corruption_html(settings: Settings) -> str:
    if not settings.paths.corruption_log.exists():
        return "<p class='muted'>Chưa có corruption log.</p>"
    log = read_json(settings.paths.corruption_log)
    rows = "".join(
        f"<tr><td><code>{escape(e['type'])}</code></td><td class='num'>{e.get('count', '–')}</td></tr>"
        for e in log.get("events", [])
    )
    return (
        f"<p class='note'>{log.get('scenario_count', 0)} kịch bản · input {log.get('input_rows')} dòng → "
        f"output {log.get('output_rows')} dòng</p>"
        f"<table><thead><tr><th>Kịch bản</th><th class='num'>Số bản ghi</th></tr></thead><tbody>{rows}</tbody></table>"
    )


CSS = """
:root{--bg:#f6f7f9;--panel:#fff;--ink:#1d2330;--muted:#667085;--line:#e3e6ec;
--ok:#1a7f4b;--ok-bg:#e3f4ea;--bad:#b42318;--bad-bg:#fdecea;--warn:#a15c00;--warn-bg:#fff4df;
--s-baseline:#3b6fd8;--s-corrupted:#d0503c;--s-repaired:#2f9e6e;--zone:rgba(208,80,60,.08)}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#11141a;--panel:#1a1f28;--ink:#e6e9ef;
--muted:#98a2b3;--line:#2a313d;--ok:#4cc38a;--ok-bg:#15301f;--bad:#f97066;--bad-bg:#3a1a17;--warn:#f5b041;
--warn-bg:#352812;--s-baseline:#6e98f0;--s-corrupted:#f07b67;--s-repaired:#4cc38a;--zone:rgba(240,123,103,.10)}}
:root[data-theme="dark"]{--bg:#11141a;--panel:#1a1f28;--ink:#e6e9ef;--muted:#98a2b3;--line:#2a313d;--ok:#4cc38a;
--ok-bg:#15301f;--bad:#f97066;--bad-bg:#3a1a17;--warn:#f5b041;--warn-bg:#352812;--s-baseline:#6e98f0;
--s-corrupted:#f07b67;--s-repaired:#4cc38a;--zone:rgba(240,123,103,.10)}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);
font:15px/1.5 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
main{max-width:1080px;margin:0 auto;padding:24px 16px 48px}
h1{font-size:24px;margin:0 0 4px}h2{font-size:17px;margin:0 0 12px}h3{font-size:15px;margin:0;text-transform:capitalize}
.sub,.muted,.note{color:var(--muted)}.note{font-size:13px;margin:8px 0 0}
.grid3{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:12px;margin:20px 0}
.grid2{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,460px),1fr));gap:12px;margin-top:12px}
.stack{display:grid;gap:12px;margin-top:12px}
.card{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:16px;min-width:0}
.badges{margin:8px 0 10px;display:flex;gap:10px;flex-wrap:wrap;font-size:13px;color:var(--muted);align-items:center}
.badge{display:inline-block;padding:1px 8px;border-radius:999px;font-size:12px;font-weight:600;margin-left:4px}
.badge.ok{color:var(--ok);background:var(--ok-bg)}.badge.bad{color:var(--bad);background:var(--bad-bg)}
.badge.muted{background:var(--line)}
.kv{display:flex;justify-content:space-between;border-top:1px solid var(--line);padding:5px 0;font-size:14px}
.kv b{font-variant-numeric:tabular-nums}
.table-wrap{overflow-x:auto}table{border-collapse:collapse;width:100%;font-size:14px}
th,td{text-align:left;padding:7px 8px;border-bottom:1px solid var(--line);vertical-align:top}
th{color:var(--muted);font-weight:600}th.st{text-transform:capitalize}.num{text-align:right}
.obs{font-size:12px;color:var(--muted);margin-top:2px}code{font-size:13px}
svg{width:100%;height:auto;display:block}.grid{stroke:var(--line)}
.tick,.axis,.zone-label{fill:var(--muted);font-size:11px}.axis{font-size:12px}.zone{fill:var(--zone)}
.zone-label{fill:var(--bad)}
.s-baseline{fill:var(--s-baseline);background:var(--s-baseline)}
.s-corrupted{fill:var(--s-corrupted);background:var(--s-corrupted)}
.s-repaired{fill:var(--s-repaired);background:var(--s-repaired)}
.legend{display:flex;gap:14px;font-size:13px;color:var(--muted);margin-bottom:6px;flex-wrap:wrap}
.legend i{display:inline-block;width:10px;height:10px;border-radius:2px;margin-right:5px}
.alerts{list-style:none;margin:0;padding:0;display:grid;gap:6px}
.alert{display:grid;grid-template-columns:18px 90px 1fr;gap:8px;padding:8px 10px;border-radius:8px;font-size:14px}
.alert b{text-transform:capitalize}.alert.critical{background:var(--bad-bg)}.alert.critical .ic{color:var(--bad)}
.alert.warning{background:var(--warn-bg)}.alert.warning .ic{color:var(--warn)}
.alert.ok{background:var(--ok-bg)}.alert.ok .ic{color:var(--ok)}
@media (max-width:520px){.alert{grid-template-columns:18px 1fr}.alert span:last-child{grid-column:2}}
"""


def render_dashboard(settings: Settings, snapshots: dict[str, StateSnapshot], alerts: list[Alert]) -> str:
    generated = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    critical = sum(1 for a in alerts if a.level == "critical")
    warnings = sum(1 for a in alerts if a.level == "warning")
    cards = "".join(_state_card(snapshots[s]) for s in STATES)
    return f"""<!doctype html>
<html lang="vi"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Data Observability Dashboard</title>
<style>{CSS}</style></head>
<body><main>
<h1>Data Observability Dashboard</h1>
<p class="sub">Crossref papers · GX 1.x quality gate · Freshness SLA 180 ngày · sinh lúc {generated}
 · <b>{critical}</b> cảnh báo nghiêm trọng, <b>{warnings}</b> cảnh báo</p>
<div class="grid3">{cards}</div>
<div class="card"><h2>Cảnh báo chất lượng &amp; drift</h2>{_alerts_html(alerts)}</div>
<div class="grid2">
  <div class="card"><h2>Phân bố tuổi bài báo</h2>{_age_chart(snapshots)}</div>
  <div class="card"><h2>Chỉ số đánh giá RAG</h2>{_metrics_chart(snapshots)}</div>
</div>
<div class="stack">
  <div class="card"><h2>Great Expectations checks</h2><div class="table-wrap">{_checks_table(snapshots)}</div></div>
  <div class="card"><h2>Kịch bản làm bẩn dữ liệu</h2><div class="table-wrap">{_corruption_html(settings)}</div></div>
</div>
</main></body></html>
"""


def build_dashboard(settings: Settings | None = None, output_path: Path | None = None) -> Path:
    settings = settings or load_settings()
    output_path = output_path or settings.paths.project_dir / "data" / "reports" / "observability_dashboard.html"
    snapshots = load_snapshots(settings)
    alerts = detect_alerts(snapshots)
    write_text(output_path, render_dashboard(settings, snapshots, alerts))
    return output_path


def main() -> None:
    path = build_dashboard()
    print(f"Observability dashboard: {path}")


if __name__ == "__main__":
    main()
