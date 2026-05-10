# RepoScope — Top-100 OSS Projekt-Analyse

*Generiert: 2026-05-10 09:44 · CHAOSS-Framework · Zhao et al. (2021)*

## Benchmark-Übersicht (KPI-Mediane)

| KPI | Median | P25 | P75 | Einheit |
|-----|-------:|----:|----:|---------|
| commit_freq          |    0.000 |    0.000 |   53.000 | Commits/30T |
| bus_factor           |    2.000 |    1.000 |    6.000 | Contributors |
| contributor_count    |  354.000 |  134.000 |  424.000 | Personen |
| days_since_commit    |    1.000 |    0.000 |   19.000 | Tage |
| issue_close_rate     |    0.518 |    0.288 |    0.850 | % |
| release_frequency    |   13.854 |    5.434 |   37.824 | Ø Tage |
| issue_close_time     |    3.125 |    1.000 |   12.653 | Tage |
| issue_engagement     |    1.566 |    0.933 |    2.084 | Kommentare |
| fork_ratio           |    0.141 |    0.094 |    0.207 | Forks/Star |
| doc_quality          |    0.898 |    0.827 |    0.998 | Score 0–1 |
| project_age          | 3045.000 | 1209.000 | 4282.000 | Tage |
| stars                | 140498.500 | 116080.000 | 184741.000 | Stars |
| open_issue_ratio     |    0.002 |    0.000 |    0.016 | Issues/Star |

## Säulen-Benchmarks (Score 0–100)

| Säule | Mean | Median | P25 | P75 |
|-------|-----:|-------:|----:|----:|
| Aktivität & Community (40%)              |   45 |     38 |  29 |  61 |
| Reaktionsfähigkeit & Wartung (35%)       |   54 |     61 |  42 |  70 |
| Reichweite & Dokumentation (25%)         |   83 |     84 |  77 |  88 |
| Gesamt                                   |   57 |     58 |  48 |  68 |

## Top-10 nach Gesamt-Score

| Rang | Repository | Score | Aktivität | Wartung | Reichweite | Stars |
|-----:|-----------|------:|----------:|--------:|-----------:|------:|
|  1 | [freeCodeCamp/freeCodeCamp](https://github.com/freeCodeCamp/freeCodeCamp) | 82 | 82 | 79 | 86 | 444,413 |
|  2 | [langgenius/dify](https://github.com/langgenius/dify) | 81 | 86 | 75 | 82 | 140,761 |
|  3 | [huggingface/transformers](https://github.com/huggingface/transformers) | 80 | 83 | 75 | 82 | 160,428 |
|  4 | [langchain-ai/langchain](https://github.com/langchain-ai/langchain) | 80 | 76 | 82 | 84 | 136,271 |
|  5 | [n8n-io/n8n](https://github.com/n8n-io/n8n) | 79 | 77 | 76 | 85 | 187,270 |
|  6 | [vercel/next.js](https://github.com/vercel/next.js) | 79 | 80 | 78 | 79 | 139,347 |
|  7 | [kubernetes/kubernetes](https://github.com/kubernetes/kubernetes) | 79 | 85 | 69 | 83 | 122,162 |
|  8 | [nodejs/node](https://github.com/nodejs/node) | 79 | 83 | 69 | 86 | 117,125 |
|  9 | [facebook/react-native](https://github.com/facebook/react-native) | 77 | 85 | 65 | 80 | 125,769 |
| 10 | [open-webui/open-webui](https://github.com/open-webui/open-webui) | 76 | 63 | 86 | 84 | 136,358 |

## BENCH-Werte für index.html (copy-paste)
```javascript
const BENCH = {
  pillars: {
    p1      : { median: 38, p25: 29, p75: 61 },
    p2      : { median: 61, p25: 42, p75: 70 },
    p3      : { median: 84, p25: 77, p75: 88 },
    overall : { median: 58, p25: 48, p75: 68 },
  },
  kpis: {
    commit_freq         : { median:0.0000, p25:0.0000, p75:53.0000 },
    bus_factor          : { median:2.0000, p25:1.0000, p75:6.0000 },
    contributor_count   : { median:354.0000, p25:134.0000, p75:424.0000 },
    days_since_commit   : { median:1.0000, p25:0.0000, p75:19.0000 },
    issue_close_rate    : { median:0.5177, p25:0.2879, p75:0.8500 },
    release_frequency   : { median:13.8545, p25:5.4343, p75:37.8235 },
    issue_close_time    : { median:3.1250, p25:1.0000, p75:12.6533 },
    issue_engagement    : { median:1.5664, p25:0.9326, p75:2.0839 },
    fork_ratio          : { median:0.1412, p25:0.0938, p75:0.2066 },
    doc_quality         : { median:0.8983, p25:0.8273, p75:0.9975 },
    project_age         : { median:3045.0000, p25:1209.0000, p75:4282.0000 },
    stars               : { median:140498.5000, p25:116080.0000, p75:184741.0000 },
    open_issue_ratio    : { median:0.0024, p25:0.0003, p75:0.0163 },
  }
};
```