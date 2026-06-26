# Explore: cross-project-federation

> Mirror of Engram #156 (`sdd/cross-project-federation/explore`). Kept on disk
> so `sdd-design` can read the prior phase's findings without an extra Engram
> hop. The canonical source is Engram #156 — if this file drifts, Engram wins.

## Problem (sharp)

`flow-engineering` is one of 7 sibling sub-projects under `C:\dev\proyects\`
(`flow-engineering`, `flow-image-generator-main`, `mockup`, `mockup-2-blog`,
`tecnodespegue-landing`, `tecnosquire-infra`, `Gestor-de-Contrase-as`). The
user's "Agentic & Context-Driven" methodology requires cross-project knowledge
transfer: an explore agent in `flow-engineering` should know about related
decisions in `mockup-2-blog` (Astro 5) or `tecnodespegue-landing`. The
"Penpax" label (user's term) signals: lightweight, peer-to-peer, on-demand —
**not** a central hub, **not** real-time sync.

### CRITICAL CORRECTION to the user's premise

The user states *"each sub-project has its own Engram memory (SQLite-backed
observation store)"*. **Factually incorrect.** Direct inspection of
`~/.engram/engram.db` (3.4 MB, `journal_mode=wal`) shows **one shared SQLite
file**, not seven. The 155 observations span 9 `project` column values
(`insyd`=95, `es`=27, `mockup-2-blog`=16, `gentle-ai`=7, `reels`=4,
`flow-engineering`=3, `flow-image-generator-v2`=1, `ecommerce-picomar`=1,
`revisa-porque-obsidian-no-me-marca`=1). The schema already has
`idx_obs_project` and `idx_obs_topic`.

So the **silos are logical (project column), not physical (separate DB files)**.
This collapses option A from "build cross-DB federation" to "add a federated
query method + fix tagging discipline". The user's mental model was
over-engineered; the minimum viable federation is much smaller.

### Real pain points

1. **Tagging discipline is broken**: 5 of 7 sub-projects have **zero**
   observations tagged with their project key. Most work lands in
   `project=insyd` by default.
2. **No federated query surface**: `mem_search(project=...)` exists in MCP,
   but no tool says "search across these N projects".
3. **Project key drift**: `flow-image-generator-v2` (1 obs) vs current
   `flow-image-generator-main`. Rename absorption is absent.
4. **Inconsistent tagging within one change**: vector-semantic-search
   artifacts #139/140/141 (`insyd`) vs #142/143 (`flow-engineering`). Same
   change, different tags — pure happenstance.

## Sub-project map

| Project | Stack | Engram obs | Git? |
|---|---|---|---|
| flow-engineering | Python / pytest-bdd | 3 (under-tagged) | yes |
| flow-image-generator-main | WXT + React 19 | 0 (1 in `-v2`) | no |
| mockup | Next.js 16 + Vite + Bun | 0 | no |
| mockup-2-blog | Astro 5.18 | 16 (highest) | no |
| tecnodespegue-landing | **Astro 6.4.4** (NOT Next.js) | 0 | yes |
| tecnosquire-infra | NixOS + flake-parts + SOPS | 0 | yes |
| Gestor-de-Contrase-as | Flutter + supabase_flutter + biometrics | 0 | yes |

**Coupling risk**: tecnosquire-infra holds SOPS-encrypted `secrets.yaml`;
Gestor-de-Contrase-as is an encrypted Flutter vault. Federation must NEVER
expose file contents — only Engram observations.

## Options evaluated (8)

| Option | Verdict |
|---|---|
| **A. Penpax on-demand logical pull (shared DB)** | **RECOMMENDED** |
| B. FTS5 HTTP endpoint (`flow serve --peer`) | viable escape hatch, NOT v1 |
| C. Federated semantic search | v2 (depends on vector-semantic-search) |
| D. Periodic sync to local mirror | rejected — violates "no sync" + drift |
| E. Git-based federation | rejected — 3 of 7 sub-projects lack `.git` |
| F. MCP server per peer | rejected — over-engineered |
| G. Central hub with publication | rejected — contradicts Penpax |
| H. Status quo | baseline — cost = 10–20% SDD time re-discovers known patterns |

## Recommendation

**Option A** — add `mem_search_federated(query, projects, limit, since,
type_filter)` to `EngramBackend`, opt-in `project_detector` for auto-tagging,
CLI flag on `flow search`, 3 observability counters, and an aliases config for
rename absorption. Single PR. ~400-600 production + ~1.5k test LOC. ~2-2.5h
end-to-end wall time.

## Source

- Engram #156 (`sdd/cross-project-federation/explore`, captured 2026-06-26)
- Direct sqlite3 inspection of `~/.engram/engram.db`