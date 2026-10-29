# Universal courseware plan schema

Create this plan **after reading the actual transcript**. Replace every example
title and cue range; never copy subject-specific figures into another lecture.

## Example (only for a transcript containing four cues)

```json
{
  "schema_version": 1,
  "slides": [
    {
      "cue_start": 1, "cue_end": 2,
      "title": "Main idea | 核心概念",
      "section": "Lesson overview / 课程概览",
      "layout": "bullets",
      "bullets": ["Claim / 核心观点", "Evidence / 证据"]
    },
    {
      "cue_start": 3, "cue_end": 4,
      "title": "Methods | 方法对比",
      "layout": "comparison",
      "table": {
        "columns": ["Criterion / 维度", "Method A", "Method B"],
        "rows": [
          ["Use case / 使用场景", "Example A", "Example B"],
          {"cells": ["Summary / 总结", "Result A", "Result B"], "emphasis": true}
        ],
        "footnote": "Illustrative example / 仅作示例"
      }
    }
  ]
}
```

## Required keys and timing

- `schema_version`: integer `1`.
- `slides`: 1–40 slide objects, count chosen from the content.
- Each slide: `cue_start` and `cue_end` (inclusive 1-based transcript IDs),
  `title` and `layout`.
- Cue ranges must cover every cue exactly once, in order, with no gaps.
  These boundaries determine source audio and subtitle timing.
- Optional `section` (navigation label), `notes` (source/uncertainty notes),
  and `bar_color` (six-digit background hex).

## Supported layouts

| Layout | Required data | Use when |
|---|---|---|
| `bullets` | `bullets` (1–7 strings) | Key ideas and explanations |
| `steps` | `bullets` (1–7 strings) | Procedures and demonstrations |
| `table` | `table` object | Actual structured records or exercises |
| `comparison` | `table` object | Comparing alternatives |
| `formula` | `formula` string, optional `bullets` (0–5) | Mathematical/scientific reasoning |
| `quote` | `quote` string, optional `attribution` | Source quotations or interviews |

A `table` object contains 2–6 `columns`, 1–8 `rows`, and optional
`footnote`. Rows are arrays of cells or
`{"cells":["..."],"emphasis":true}` objects. All row lengths equal the
number of columns. In default HTML, these are rasterized into the embedded
chapter image; only the opt-in `--format pptx --mode editable` output uses
**native PowerPoint tables**.

## Quality requirements

1. Design topic boundaries and visual layouts **from the current lecture**.
   Do not impose an accounting table, fixed cover/review checklist or any
   other domain structure on unrelated lessons.
2. Source-check terms, claims, numbers, formulas, quotations and chronology.
   Document uncertain ASR and any outside-source material in `notes`.
3. If a numerical answer is derived, show the derivation in a table
   `footnote` or slide note. If a figure is genuinely unknown, display
   `—`; never fabricate it. Do not demand arithmetic for a non-numeric lesson.
4. Plan for the reserved bottom subtitle strip, readable typography and
   short text. The renderer should fail on overflow instead of cropping.
5. Structural validation ensures layout and cue alignment; it does *not*
   automatically verify the truth of free-form slide statements.
6. Check `transcript-qa.md` for uncertain numbers, years and acronyms. A
   calculated total or a textbook example does not establish what the lecturer
   actually said. Document derived/external numerical values in `notes` or
   table `footnote`, and keep transcript/subtitle cue IDs unchanged unless
   source evidence genuinely supports a correction.
