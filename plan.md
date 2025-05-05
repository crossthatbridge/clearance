```markdown:plan/mdl
# clearpath – full development plan
(last updated {{date}})

---

## 0. purpose

deliver a revit-add-in that automatically flags uk approved document part m (vol 1 & 2) accessibility breaches in both plan and vertical dimensions, while remaining low-cost, revit-native and cloud-updatable.

---

## 1. vision & scope

| item | in scope (mvp) | out of scope (phase 2+) |
|------|---------------|-------------------------|
| revit versions | 2024+ only | 2023 and earlier |
| rules | door widths, turning circles, nibs, ramps, head-room, reach heights | stair risers, sanitary fixture spacing, acoustic/performance regs |
| workflow | flag non-compliance, pdf report, in-canvas overlay | automatic fixes / element repositioning |
| deployment | local bundle, s3 rule updates, 100 floating seats | autodesk acc / bim 360 integration |
| licensing | per-machine key, anonymous telemetry | floating server, lm tools |
| ui | single ribbon panel, rule selection dialog, settings window | real-time dashboard, clash matrix |

---

## 2. functional requirements

1. run check on active revit doc.
2. load latest rule set from `%ProgramData%\ClearPath\Rules` (auto-refresh from s3 every 24 h).
3. extract relevant geometry (doors, rooms, ramps, controls, ceilings etc.).
4. evaluate every rule and return `Pass / Warn / Fail`.
5. highlight offending zones & elements in-canvas.
6. generate pdf report (timestamp, summary table, element ids, clauses).
7. store run log locally and push anonymous stats to AWS API Gateway if telemetry opt-in.

---

## 3. non-functional requirements

| aspect | target |
|--------|--------|
| performance | < 30 s on a 300 MB central model |
| memory | +≤150 MB managed heap |
| security | no PII uploaded; tls 1.2; aws kms for bucket |
| usability | zero config install; ribbon → single click |
| accessibility | pdf report colour + text label, WCAG AA |
| maintainability | 90 % rule engine covered by unit tests |
| availability (updates) | s3 cloudfront 99.9 % SLA |

---

## 4. architecture overview

see “clearpath – architecture v0.2”; recap:

```
Revit 2024        Core libs                    Cloud (AWS)
───────────       ─────────────────────────    ─────────────────────────┐
 UI Ribbon ──┐    RuleEngine   GeometryHub     S3 bucket rules.zip      │
 Overlay UI  │          ▲          ▲          Lambda telemetry         │
             │          │          │          DynamoDB runs            │
             └──→ RunClearPath ────┘          CloudFront CDN  ⇦─────────┘
```

---

## 5. component details

### 5.1 add-in ui

| class | purpose |
|-------|---------|
| `RibbonManager` | registers “Run Check”, “Settings”, “Last Report” |
| `RulePickerWindow` | multi-select grid of rules, save selection in `%appdata%` |
| `OverlayPainter` | `TemporaryGraphicsManager` – red/green hatsched geometry |
| `SettingsWindow` | edits `settings.json`, shows licence GUID |

### 5.2 geometry hub

adapters wrap revit API into plain-pojo structs:

```csharp
struct Door { ElementId Id; double ClearOpening; XYZ Hinge; XYZ SwingVec; }
struct Ramp { ElementId Id; double Slope; Curve Axis; }
struct Control { ElementId Id; XYZ Center; }
```

### 5.3 rule engine

* interface `IRule`
* `PlanarRuleBase` and `VerticalRuleBase`
* rule registry loaded via reflection (dll) + yaml
* engine parallel-evaluates (`Parallel.ForEach`) but caps at `Environment.ProcessorCount - 1`.

### 5.4 services

| service | stack | key points |
|---------|-------|------------|
| rule update | S3 + CloudFront | bucket `clearpath-demo-rules-eu-west-2` (public read) |
| telemetry | API Gateway → Lambda (Python) → DynamoDB | single table `runs(pk=guid, sk=datetime)` |
| licensing | machine GUID hashed (SHA-256) → `license.json` | no online activation in MVP |

---

## 6. data & file formats

### 6.1 rule yaml schema

```yaml
id: M4_2_3_102
clause: "Doc M Vol 1 3.102"
domain: Planar     # Planar | Vertical
category: Door
geometry:
  shape: rectangle
  width: 850         # mm
condition: >
  door.clearOpening >= width
severity: Fail       # or Warn
```

### 6.2 settings.json (see earlier)

---

## 7. build, packaging, ci/cd

1. local build via `build_bundle.ps1`.
2. github actions workflow:
   * restore nuget
   * run unit tests (`dotnet test`)
   * powershell bundle
   * upload artefact
   * manual promotion to “releases” pushes zip to s3 bucket.

3. installer (optional): wix toolset msi that copies bundle + .addin.

---

## 8. testing strategy

| layer | tool | coverage target |
|-------|------|-----------------|
| rule engine | nunit | 90 % lines |
| geometry adapters | revit integration test (RvtCmdRunner) | sample models |
| ui | visual inspection + smoke test | every sprint |
| performance | jenkins perf job on 300 MB model | alert if >50 s |
| cloud | lambda unit + api gw postman tests | 100 % success |

sample models:  
`/Samples/flat.rvt`, `/Samples/office.rvt`, `/Samples/rampViolation.rvt`.

---

## 9. timeline & milestones (8 weeks)

| wk | deliverable |
|----|-------------|
| 1 | repo, scaffolding, build passes, hello world command |
| 2 | geometry hub (doors, rooms) + 2 planar rules |
| 3 | overlay painter + pdf report (PdfSharp) |
| 4 | 8 planar rules total, basic settings dialog |
| 5 | vertical adapters (ramps, ceilings) + 2 vertical rules |
| 6 | s3 rule updater, telemetry lambda, ci upload |
| 7 | beta installer, internal QA on 5 models |
| 8 | pilot release to 10 seats, feedback loop |

---

## 10. risks & mitigations

| risk | impact | mitigation |
|------|--------|-----------|
| revit api changes 2025 | med | tie build to LTS versions; abstract api in GeometryHub |
| performance on large federated models | high | profile early; cache element solids; parallel eval |
| rule ambiguity (Part M interpretations) | med | make tolerances configurable; allow warn/pass tiers |
| aws cost over-run | low | cloudfront + s3 at <£5/m; telemetry capped 5 kb/run |

---

## 11. future roadmap (post-mvp)

* auto-fix suggest/move (door nib extents, ramp slope lengthening)
* autodesk construction cloud integration (web-hooks on model versions)
* part K, part B rule sets
* multi-language ui (EN/DE/FR)
* powerbi dashboard of portfolio compliance

---

## 12. appendices

### a) pdf report layout

| section | content |
|---------|---------|
| title | project name, revit file, datetime |
| summary | table pass/warn/fail counts |
| detail | one row per failure (element id, view, clause, screenshot) |
| legend | colour key, tolerances used |

### b) sample telemetry payload

```json
{
  "guid": "3e4d…",
  "ver": "1.0.0",
  "revit": "2024",
  "rules": "20231005",
  "pass": 23,
  "warn": 2,
  "fail": 5,
  "durMs": 11450
}
```

---

end of document
```
