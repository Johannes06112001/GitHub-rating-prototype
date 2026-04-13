[README.md](https://github.com/user-attachments/files/26681205/README.md)
# GitHub-rating-prototype# RepoScope — GitHub Repository Quality Analyzer

Uni-Projekt: Analyse von Open-Source-Qualität anhand der GitHub REST API.

## Projektstruktur

```
repo-analyzer/
├── index.html        ← GitHub Pages Frontend (kein Backend nötig)
├── collect_data.py   ← Datensammlung Top-100 Repos + Benchmark-Berechnung
├── top100_repos.json ← (generiert) Rohdaten der 100 analysierten Repos
├── benchmarks.json   ← (generiert) Statistische Kennzahlen
└── analysis_report.md← (generiert) Markdown-Report
```

## Schnellstart

### 1. Daten sammeln (Python)
```bash
pip install requests
export GITHUB_TOKEN=ghp_xxxxxxxxxxxx   # empfohlen, sonst sehr langsam
python collect_data.py
```
Das Script gibt am Ende die aktuellen `BENCH`-Werte aus, die du in `index.html` eintragen kannst.

### 2. GitHub Pages aktivieren
1. Repo auf GitHub pushen
2. Settings → Pages → Branch: `main`, Folder: `/ (root)` → Save
3. Nach ~1 Minute: `https://<user>.github.io/<repo>/`

## Scoring-Methodik

| Dimension     | Gewicht | Datenquellen |
|---------------|--------:|--------------|
| Aktivität     | 30 %    | `pushed_at`, `/stats/commit_activity`, `/releases` |
| Dokumentation | 25 %    | `/community/profile`, `description`, `topics` |
| Community     | 25 %    | `stargazers_count`, `forks_count`, `/contributors` |
| Wartung       | 20 %    | `archived`, `has_issues`, `open_issues_count` |

### Verwendete API-Endpunkte

| Endpunkt | Zweck |
|----------|-------|
| `GET /repos/{owner}/{repo}` | Basis-Metadaten |
| `GET /repos/{owner}/{repo}/community/profile` | Dokumentations-Checkliste |
| `GET /repos/{owner}/{repo}/languages` | Sprachverteilung |
| `GET /repos/{owner}/{repo}/releases` | Release-Aktivität |
| `GET /repos/{owner}/{repo}/contributors` | Contributor-Anzahl |
| `GET /repos/{owner}/{repo}/stats/commit_activity` | Wöchentliche Commits |
| `GET /search/repositories` | Top-100-Suche |

## Benchmarks aktualisieren

Nach dem Ausführen von `collect_data.py` erscheint am Ende die Ausgabe:
```
const BENCH = {
  overall:       { p25: 54, median: 67, p75: 78 },
  activity:      { p25: 48, median: 69, p75: 87 },
  ...
};
```
Diese Werte in `index.html` im `BENCH`-Objekt ersetzen, um aktuelle Benchmarks zu verwenden.

## Rate-Limits

| Situation | Limit | Reicht für |
|-----------|-------|------------|
| Ohne Token | 60 req/h | ~12 Repo-Analysen |
| Mit Token  | 5.000 req/h | ~1.000 Repo-Analysen |

Token erstellen: https://github.com/settings/tokens (Scope: `public_repo`)

## Technologien

- **Frontend**: Vanilla HTML/CSS/JS — kein Framework, kein Build-Step
- **APIs**: GitHub REST API v3 (GraphQL für erweiterte Auswertungen möglich)
- **Hosting**: GitHub Pages (statisch, kein Backend)
- **Datensammlung**: Python 3.10+, `requests`
