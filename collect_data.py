#!/usr/bin/env python3
"""
RepoScope — Datensammlung Top-100 + Benchmark-Berechnung
=========================================================
Sammelt alle 13 KPIs des dreisäuligen CHAOSS-Frameworks
(nach Zhao et al. 2021) für die 100 größten Open-Source-Projekte.

Säule 1 — Aktivität & Community (40%)
  commit_freq       | Commits letzte 30 Tage
  bus_factor        | Min. N Contributors für 50% der Commits
  contributor_count | Anzahl menschlicher Contributors
  days_since_commit | Tage seit letztem Commit (invertiert)

Säule 2 — Reaktionsfähigkeit & Wartung (35%)
  issue_close_rate  | Anteil geschlossener Issues
  release_frequency | Ø Tage zwischen stabilen Releases (invertiert)
  issue_close_time  | Ø Tage bis Issue-Schließung (invertiert)
  issue_engagement  | Ø Kommentare pro Issue

Säule 3 — Reichweite & Dokumentation (25%)
  fork_ratio        | Forks / Stars
  doc_quality       | log(readme_size) normiert
  project_age       | Tage seit created_at (log-skaliert)
  stars             | stargazers_count (log-skaliert)
  open_issue_ratio  | open_issues / stars (invertiert)

Verwendung:
-----------
    pip install requests
    export GITHUB_TOKEN=ghp_xxx
    python collect_data.py

    # Für 1000 Repos:
    python collect_data.py --count 1000

Ausgabe:
--------
    top100_repos.json   — Rohdaten + berechnete KPIs + Säulen-Scores
    benchmarks.json     — Mediane, P25, P75 je KPI (→ index.html BENCH)
    analysis_report.md  — Lesbare Zusammenfassung
"""

import os, sys, json, time, math, re, statistics, argparse
from datetime import datetime, timezone

try:
    import requests
except ImportError:
    sys.exit("Fehler: 'requests' fehlt. Bitte: pip install requests")

# ── Konfiguration ────────────────────────────────────────────────
TOKEN    = os.environ.get("GITHUB_TOKEN", "")
BASE_URL = "https://api.github.com"
HEADERS  = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
if TOKEN:
    HEADERS["Authorization"] = f"Bearer {TOKEN}"

# Säulen-Gewichte (Zhao et al. 2021)
PILLAR_WEIGHTS = {"p1": 0.40, "p2": 0.35, "p3": 0.25}

# KPI-Gewichte innerhalb der Säulen
KPI_WEIGHTS = {
    "commit_freq":       ("p1", 0.30),
    "bus_factor":        ("p1", 0.40),
    "contributor_count": ("p1", 0.15),
    "days_since_commit": ("p1", 0.15),
    "issue_close_rate":  ("p2", 0.30),
    "release_frequency": ("p2", 0.30),
    "issue_close_time":  ("p2", 0.25),
    "issue_engagement":  ("p2", 0.15),
    "fork_ratio":        ("p3", 0.25),
    "doc_quality":       ("p3", 0.25),
    "project_age":       ("p3", 0.20),
    "stars":             ("p3", 0.15),
    "open_issue_ratio":  ("p3", 0.15),
}

# Invertierte KPIs (niedrigerer Wert = besser)
INVERTED = {"days_since_commit", "release_frequency", "issue_close_time", "open_issue_ratio"}

# ── HTTP-Helper ─────────────────────────────────────────────────
def get(url, params=None, silent=False):
    for attempt in range(3):
        resp = requests.get(url, headers=HEADERS, params=params, timeout=25)
        if resp.status_code == 200:
            return resp.json()
        if resp.status_code == 202:
            time.sleep(6)
            continue
        if resp.status_code in (403, 429):
            reset = int(resp.headers.get("X-RateLimit-Reset", time.time() + 60))
            wait  = max(reset - time.time(), 0) + 2
            if not silent:
                print(f"  ⏳ Rate-Limit. Warte {wait:.0f}s …")
            time.sleep(wait)
            continue
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
    return None

# ── Daten-Fetcher ────────────────────────────────────────────────
def fetch_top_repos(n=100):
    repos, page = [], 1
    per_page = min(100, n)
    while len(repos) < n:
        data = get(f"{BASE_URL}/search/repositories", params={
            "q": "stars:>5000 is:public fork:false",
            "sort": "stars", "order": "desc",
            "per_page": per_page, "page": page,
        })
        if not data or not data.get("items"):
            break
        repos.extend(data["items"])
        page += 1
        time.sleep(1.2)
    return repos[:n]

def fetch_readme_size(owner, repo):
    data = get(f"{BASE_URL}/repos/{owner}/{repo}/readme", silent=True)
    return data.get("size", 0) if data else 0

def fetch_contributors(owner, repo):
    """Holt bis zu 500 Contributors (5 Seiten × 100). Gibt sortierte Liste zurück."""
    all_c = []
    for page in range(1, 6):
        page_data = get(
            f"{BASE_URL}/repos/{owner}/{repo}/contributors",
            params={"per_page": 100, "page": page, "anon": "false"},
            silent=True
        )
        if not page_data:
            break
        all_c.extend(page_data)
        if len(page_data) < 100:
            break
        time.sleep(.2)
    return sorted(all_c, key=lambda c: -c.get("contributions", 0))

def fetch_commit_activity(owner, repo):
    """Gibt Commit-Aktivität der letzten 52 Wochen zurück (kann 202 liefern)."""
    return get(f"{BASE_URL}/repos/{owner}/{repo}/stats/commit_activity", silent=True)

def fetch_issues(owner, repo, state="all", pages=3):
    """Holt bis zu 3 × 100 Issues (ohne PRs)."""
    issues = []
    for page in range(1, pages + 1):
        data = get(
            f"{BASE_URL}/repos/{owner}/{repo}/issues",
            params={"state": state, "per_page": 100, "page": page},
            silent=True
        )
        if not data:
            break
        real = [i for i in data if "pull_request" not in i]
        issues.extend(real)
        if len(data) < 100:
            break
        time.sleep(.2)
    return issues

def fetch_stable_releases(owner, repo):
    """Holt bis zu 100 stabile Releases (kein Draft, kein Prerelease)."""
    data = get(f"{BASE_URL}/repos/{owner}/{repo}/releases", params={"per_page": 100})
    if not data:
        return []
    return [r for r in data if not r.get("draft") and not r.get("prerelease")]

# ── KPI-Berechnung ───────────────────────────────────────────────
def days_since(date_str):
    dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
    return (datetime.now(timezone.utc) - dt).days

def calc_bus_factor(contributors):
    """Min. N Contributors, sodass cumsum(contributions) >= 50% des Gesamts."""
    total = sum(c.get("contributions", 0) for c in contributors)
    if total == 0:
        return 1
    cum, n = 0, 0
    for c in contributors:
        cum += c.get("contributions", 0)
        n   += 1
        if cum >= total * 0.5:
            break
    return max(1, n)

def calc_kpis(repo, readme_size, contributors, commit_activity, issues, releases):
    k = {}

    # ── Säule 1: Aktivität & Community ──
    dsp = days_since(repo["pushed_at"])
    k["days_since_commit"] = dsp

    # commit_freq: Summe letzte 4 Wochen (≈30 Tage)
    if commit_activity and isinstance(commit_activity, list) and len(commit_activity) >= 4:
        k["commit_freq"] = sum(w.get("total", 0) for w in commit_activity[-4:])
    else:
        k["commit_freq"] = 0

    human_c = [c for c in contributors if c.get("type") == "User"]
    k["contributor_count"] = len(human_c) or len(contributors)
    k["bus_factor"] = calc_bus_factor(contributors)

    # ── Säule 2: Reaktionsfähigkeit & Wartung ──
    if issues:
        closed = [i for i in issues if i.get("state") == "closed"]
        k["issue_close_rate"] = len(closed) / len(issues)
        k["issue_engagement"] = sum(i.get("comments", 0) for i in issues) / len(issues)
        times = [
            (datetime.fromisoformat(i["closed_at"].replace("Z", "+00:00")) -
             datetime.fromisoformat(i["created_at"].replace("Z", "+00:00"))).days
            for i in closed if i.get("closed_at")
        ]
        k["issue_close_time"] = statistics.mean(times) if times else None
    else:
        k["issue_close_rate"] = None
        k["issue_engagement"] = None
        k["issue_close_time"] = None

    if len(releases) >= 2:
        dates = sorted([datetime.fromisoformat(r["published_at"].replace("Z", "+00:00"))
                        for r in releases], reverse=True)
        gaps  = [(dates[i] - dates[i+1]).days for i in range(len(dates)-1)]
        k["release_frequency"] = statistics.mean(gaps)
    else:
        k["release_frequency"] = None

    # ── Säule 3: Reichweite & Dokumentation ──
    stars = repo["stargazers_count"]
    forks = repo["forks_count"]
    k["stars"]            = stars
    k["fork_ratio"]       = forks / stars if stars > 0 else 0.0
    k["open_issue_ratio"] = repo["open_issues_count"] / stars if stars > 0 else 0.0
    k["project_age"]      = days_since(repo["created_at"])
    # Dokumentationsqualität: readme_present × log(size+1) normiert auf 0–1
    k["doc_quality"]      = min(1.0, math.log10(readme_size + 1) / math.log10(32000)) if readme_size > 0 else 0.0

    return k

# ── Scoring ─────────────────────────────────────────────────────
def score_kpi(kpi_id, val):
    """Bildet Rohwert auf 0–100 ab. Gibt None zurück wenn val=None."""
    if val is None or (isinstance(val, float) and math.isnan(val)):
        return None
    v = float(val)

    def log_s(x, top):
        return min(100, round(math.log10(x + 1) / math.log10(top) * 100)) if x > 0 else 0

    match kpi_id:
        case "commit_freq":
            return log_s(v, 250)
        case "bus_factor":
            return log_s(v, 40)
        case "contributor_count":
            return log_s(v, 5000)
        case "days_since_commit":
            if v <=  7: return 100
            if v <= 30: return 85
            if v <= 90: return 65
            if v <= 180: return 40
            if v <= 365: return 20
            return 5
        case "issue_close_rate":
            return min(100, round(v * 100))
        case "release_frequency":
            if v <=  7: return 100
            if v <= 14: return 90
            if v <= 30: return 75
            if v <= 60: return 55
            if v <= 90: return 35
            if v <= 180: return 15
            return 5
        case "issue_close_time":
            if v <=  1: return 100
            if v <=  3: return 90
            if v <=  7: return 75
            if v <= 30: return 55
            if v <= 90: return 30
            return 10
        case "issue_engagement":
            return log_s(v, 15)
        case "fork_ratio":
            return min(100, round(math.log10(v * 100 + 1) / math.log10(40) * 100))
        case "doc_quality":
            return round(v * 100)
        case "project_age":
            return log_s(v, 9000)
        case "stars":
            return log_s(v, 200000)
        case "open_issue_ratio":
            if v <= 0.001: return 100
            if v <= 0.005: return 85
            if v <= 0.01:  return 65
            if v <= 0.05:  return 35
            if v <= 0.10:  return 15
            return 5
    return 50

def calc_pillar_score(pillar_id, kpi_vals):
    pillar_kpis = [(k, w) for k, (p, w) in KPI_WEIGHTS.items() if p == pillar_id]
    pts, wt = 0.0, 0.0
    for k, w in pillar_kpis:
        s = score_kpi(k, kpi_vals.get(k))
        if s is not None:
            pts += s * w
            wt  += w
    return round(pts / wt) if wt > 0 else 0

def calc_scores(kpi_vals):
    p1 = calc_pillar_score("p1", kpi_vals)
    p2 = calc_pillar_score("p2", kpi_vals)
    p3 = calc_pillar_score("p3", kpi_vals)
    return {
        "p1": p1, "p2": p2, "p3": p3,
        "overall": round(p1 * 0.40 + p2 * 0.35 + p3 * 0.25),
        "kpi_scores": {k: score_kpi(k, kpi_vals.get(k)) for k in KPI_WEIGHTS}
    }

# ── Benchmarks ───────────────────────────────────────────────────
def compute_benchmarks(results):
    """P25, Median, P75, Mean für jeden KPI und jede Säule."""
    bench = {"kpis": {}, "pillars": {}}
    n     = len(results)

    # KPI-level
    for kpi_id in KPI_WEIGHTS:
        vals = sorted([r["kpis"][kpi_id] for r in results
                       if r["kpis"].get(kpi_id) is not None])
        if len(vals) < 4:
            continue
        m = len(vals)
        bench["kpis"][kpi_id] = {
            "mean":   round(statistics.mean(vals), 4),
            "median": round(statistics.median(vals), 4),
            "stdev":  round(statistics.stdev(vals), 4),
            "p10":    vals[max(0, int(m*.10)-1)],
            "p25":    vals[max(0, int(m*.25)-1)],
            "p75":    vals[min(m-1, int(m*.75))],
            "p90":    vals[min(m-1, int(m*.90))],
        }

    # Pillar-level (score 0–100)
    for pid in ("p1", "p2", "p3", "overall"):
        key = "overall" if pid == "overall" else pid
        vals = sorted([r["scores"][key] for r in results])
        m = len(vals)
        bench["pillars"][pid] = {
            "mean":   round(statistics.mean(vals)),
            "median": round(statistics.median(vals)),
            "p25":    vals[max(0, int(m*.25)-1)],
            "p75":    vals[min(m-1, int(m*.75))],
        }

    bench["sample_size"]  = n
    bench["generated_at"] = datetime.now().isoformat()
    return bench

# ── Report ───────────────────────────────────────────────────────
def write_report(results, bench):
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [
        f"# RepoScope — Top-{len(results)} OSS Projekt-Analyse",
        f"\n*Generiert: {now} · CHAOSS-Framework · Zhao et al. (2021)*\n",
        "## Benchmark-Übersicht (KPI-Mediane)\n",
        "| KPI | Median | P25 | P75 | Einheit |",
        "|-----|-------:|----:|----:|---------|",
    ]
    units = {
        "commit_freq":"Commits/30T", "bus_factor":"Contributors",
        "contributor_count":"Personen", "days_since_commit":"Tage",
        "issue_close_rate":"%", "release_frequency":"Ø Tage",
        "issue_close_time":"Tage", "issue_engagement":"Kommentare",
        "fork_ratio":"Forks/Star", "doc_quality":"Score 0–1",
        "project_age":"Tage", "stars":"Stars", "open_issue_ratio":"Issues/Star"
    }
    for k, b in bench.get("kpis", {}).items():
        lines.append(f"| {k:20s} | {b['median']:>8.3f} | {b['p25']:>8.3f} | {b['p75']:>8.3f} | {units.get(k,'')} |")

    lines += [
        "\n## Säulen-Benchmarks (Score 0–100)\n",
        "| Säule | Mean | Median | P25 | P75 |",
        "|-------|-----:|-------:|----:|----:|",
    ]
    labels = {"p1":"Aktivität & Community (40%)","p2":"Reaktionsfähigkeit & Wartung (35%)","p3":"Reichweite & Dokumentation (25%)","overall":"Gesamt"}
    for pid, b in bench.get("pillars", {}).items():
        lines.append(f"| {labels.get(pid,pid):40s} | {b['mean']:4d} | {b['median']:6d} | {b['p25']:3d} | {b['p75']:3d} |")

    lines += ["\n## Top-10 nach Gesamt-Score\n",
              "| Rang | Repository | Score | Aktivität | Wartung | Reichweite | Stars |",
              "|-----:|-----------|------:|----------:|--------:|-----------:|------:|"]
    for i, r in enumerate(sorted(results, key=lambda x: -x["scores"]["overall"])[:10], 1):
        s = r["scores"]
        lines.append(f"| {i:2d} | [{r['full_name']}]({r['html_url']}) | "
                     f"{s['overall']} | {s['p1']} | {s['p2']} | {s['p3']} | "
                     f"{r['kpis']['stars']:,} |")

    lines += [
        "\n## BENCH-Werte für index.html (copy-paste)\n```javascript",
        "const BENCH = {",
        "  pillars: {",
    ]
    for pid, b in bench.get("pillars", {}).items():
        lines.append(f"    {pid:8s}: {{ median:{b['median']:3d}, p25:{b['p25']:3d}, p75:{b['p75']:3d} }},")
    lines.append("  },\n  kpis: {")
    for k, b in bench.get("kpis", {}).items():
        lines.append(f"    {k:20s}: {{ median:{b['median']:.4f}, p25:{b['p25']:.4f}, p75:{b['p75']:.4f} }},")
    lines += ["  }\n};\n```"]

    with open("analysis_report.md", "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

# ── Hauptprogramm ────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=100, help="Anzahl Repos (max. 1000)")
    args = parser.parse_args()
    n = min(1000, max(10, args.count))

    print("=" * 65)
    print(f"  RepoScope — Datensammlung Top-{n} Open-Source-Projekte")
    print("=" * 65)
    print(f"  Token : {'✓ vorhanden (5.000 req/h)' if TOKEN else '✗ fehlt (60 req/h)'}")
    if not TOKEN:
        print("  ⚠  Ohne Token dauert das Script sehr lange!")
        print("     export GITHUB_TOKEN=ghp_xxxx")
        print("     Token: https://github.com/settings/tokens (Scope: public_repo)\n")

    # ── Schritt 1: Repos laden
    print(f"\n📦 Lade Top-{n} Repositories …")
    repos = fetch_top_repos(n)
    print(f"   ✓ {len(repos)} Repositories geladen\n")

    results = []

    for i, repo in enumerate(repos):
        owner = repo["owner"]["login"]
        name  = repo["name"]
        print(f"[{i+1:4d}/{n}] {owner}/{name}")

        # API Calls für dieses Repo
        readme_size    = fetch_readme_size(owner, name);          time.sleep(.2)
        contributors   = fetch_contributors(owner, name);         time.sleep(.3)
        commit_act     = fetch_commit_activity(owner, name);      time.sleep(.4)
        issues         = fetch_issues(owner, name, state="all");  time.sleep(.3)
        releases       = fetch_stable_releases(owner, name);      time.sleep(.2)

        kpis   = calc_kpis(repo, readme_size, contributors, commit_act, issues, releases)
        scores = calc_scores(kpis)

        # Fortschrittsanzeige
        bar = "█" * (scores["overall"]//10) + "░" * (10 - scores["overall"]//10)
        p2_disp = scores["p2"] if kpis.get("issue_close_rate") is not None else "n/a"
        print(f"           [{bar}] Gesamt={scores['overall']:3d}  "
              f"P1={scores['p1']:3d}  P2={p2_disp!s:>3}  P3={scores['p3']:3d}  "
              f"⭐{repo['stargazers_count']:>7,}  Bus={kpis['bus_factor']}")

        results.append({
            "rank":             i + 1,
            "full_name":        repo["full_name"],
            "html_url":         repo["html_url"],
            "description":      repo.get("description") or "",
            "language":         repo.get("language") or "",
            "license":          (repo.get("license") or {}).get("spdx_id", ""),
            "topics":           repo.get("topics") or [],
            "archived":         repo.get("archived", False),
            "fork":             repo.get("fork", False),
            "created_at":       repo["created_at"],
            "pushed_at":        repo["pushed_at"],
            "forks_count":      repo["forks_count"],
            "open_issues_count":repo["open_issues_count"],
            "kpis":             kpis,
            "scores":           scores,
        })

        time.sleep(.1)

    # ── Schritt 2: Speichern
    print("\n💾 Speichere …")
    out_file = f"top{'1000' if n>=1000 else '100'}_repos.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"   ✓ {out_file}")

    # ── Schritt 3: Benchmarks
    bench = compute_benchmarks(results)
    with open("benchmarks.json", "w", encoding="utf-8") as f:
        json.dump(bench, f, indent=2)
    print("   ✓ benchmarks.json")

    # ── Schritt 4: Report
    write_report(results, bench)
    print("   ✓ analysis_report.md")

    # ── Zusammenfassung
    print("\n" + "="*65)
    print("  BENCHMARK-ZUSAMMENFASSUNG (Säulen-Scores)")
    print("="*65)
    for pid in ("p1","p2","p3","overall"):
        b = bench["pillars"].get(pid, {})
        label = {"p1":"Aktivität & Community ","p2":"Reaktionsfähigkeit   ","p3":"Reichweite & Doku    ","overall":"Gesamt               "}[pid]
        print(f"  {label}  Mean={b.get('mean','?'):3}  Median={b.get('median','?'):3}  P25={b.get('p25','?'):3}  P75={b.get('p75','?'):3}")

    print(f"\n✅ Fertig! Benchmarks in benchmarks.json — die BENCH-Werte für")
    print(f"   index.html stehen in analysis_report.md (copy-paste Block).")

if __name__ == "__main__":
    main()
