"""Subject-agnostic, source-anchored plans for finished lecture courseware.

An assistant or user curates the plan after studying the actual transcript.
This module validates it deterministically and renders simple, reusable layouts.
No subject, terminology, numerical answer or slide count is hard-coded.
"""
from __future__ import annotations

from pathlib import Path

from pipeline_core import check_cues, palette, rgb

LAYOUTS = {"bullets", "steps", "table", "comparison", "formula", "quote"}


def _nonempty(value, label, maximum=240):
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise ValueError(f"{label}: expected nonempty text of at most {maximum} characters")
    return value.strip()


def _text_list(value, label, low=1, high=7):
    if not isinstance(value, list) or not low <= len(value) <= high:
        raise ValueError(f"{label}: expected {low}–{high} items")
    return [_nonempty(item, f"{label} item") for item in value]


def _optional_text(value, label, maximum=240):
    if value is None or value == "":
        return ""
    return _nonempty(value, label, maximum)


def validate_plan(plan, cues, duration):
    """Validate slide evidence, layouts and exact one-time cue coverage."""
    check_cues(cues)
    if not isinstance(plan, dict) or plan.get("schema_version") != 1:
        raise ValueError("Courseware plan requires schema_version: 1")
    slides = plan.get("slides")
    if not isinstance(slides, list) or not 1 <= len(slides) <= 40:
        raise ValueError("Courseware plan requires 1–40 slides")
    expected = 1
    validated = []
    for index, item in enumerate(slides, 1):
        if not isinstance(item, dict):
            raise ValueError(f"Slide {index}: expected object")
        start, end = item.get("cue_start"), item.get("cue_end")
        if (type(start) is not int or type(end) is not int or start != expected
                or end < start or end > len(cues)):
            raise ValueError(f"Slide {index}: cue ranges must be contiguous, ordered and non-overlapping")
        expected = end + 1
        title = _nonempty(item.get("title"), f"Slide {index} title", 110)
        layout = item.get("layout")
        if layout not in LAYOUTS:
            raise ValueError(f"Slide {index}: unknown layout {layout!r}")
        cleaned = dict(item, title=title, layout=layout)
        cleaned["section"] = _nonempty(item.get("section", "LECTURE"), f"Slide {index} section", 70)
        cleaned["notes"] = str(item.get("notes", "")).strip()
        if layout in {"table", "comparison"}:
            table = item.get("table")
            if not isinstance(table, dict):
                raise ValueError(f"Slide {index}: table is required")
            columns = _text_list(table.get("columns"), "table columns", 2, 6)
            rows = table.get("rows")
            if not isinstance(rows, list) or not 1 <= len(rows) <= 8:
                raise ValueError(f"Slide {index}: table requires 1–8 rows")
            parsed_rows = []
            for j, row in enumerate(rows, 1):
                cells = row.get("cells") if isinstance(row, dict) else row
                if not isinstance(cells, list) or len(cells) != len(columns):
                    raise ValueError(f"Slide {index} table row {j}: column count differs")
                cells = [_nonempty(x, f"Slide {index} table cell", 110) for x in cells]
                emphasis = row.get("emphasis", False) if isinstance(row, dict) else False
                if type(emphasis) is not bool:
                    raise ValueError(f"Slide {index} table row {j}: emphasis must be boolean")
                parsed_rows.append({"cells": cells, "emphasis": emphasis})
            cleaned["table"] = {
                "columns": columns, "rows": parsed_rows,
                "footnote": _optional_text(table.get("footnote"), f"Slide {index} footnote"),
            }
        elif layout in {"bullets", "steps"}:
            cleaned["bullets"] = _text_list(item.get("bullets"), f"Slide {index} bullets")
        elif layout == "formula":
            cleaned["formula"] = _nonempty(item.get("formula"), f"Slide {index} formula", 160)
            cleaned["bullets"] = _text_list(item.get("bullets", []), f"Slide {index} explanation", 0, 5)
        elif layout == "quote":
            cleaned["quote"] = _nonempty(item.get("quote"), f"Slide {index} quote", 500)
            cleaned["attribution"] = _optional_text(item.get("attribution"), f"Slide {index} attribution", 100)
        validated.append(cleaned)
    if expected != len(cues) + 1:
        raise ValueError(f"Courseware plan omitted cue IDs {expected}–{len(cues)}")
    if float(duration) < cues[-1]["end"]:
        raise ValueError("Audio duration ends before transcript")
    return validated


def specs_from_plan(slides, cues, duration):
    """A topic spans whole sentence cues; silent gaps remain in original audio."""
    result = []
    for i, item in enumerate(slides):
        first, last = item["cue_start"], item["cue_end"]
        start = 0.0 if i == 0 else cues[first - 1]["start"]
        end = float(duration) if i == len(slides) - 1 else cues[last]["start"]
        if end <= start:
            raise ValueError(f"Slide {i+1}: empty topic interval")
        result.append({"start": start, "end": end, "offset": start,
                       "cues": list(range(first, last + 1))})
    return result


def body_lines(item):
    """Non-table layouts share accessible, editable text content."""
    kind = item["layout"]
    if kind == "steps":
        return [f"{i}. {value}" for i, value in enumerate(item["bullets"], 1)]
    if kind == "formula":
        return [item["formula"]] + item["bullets"]
    if kind == "quote":
        return ["“" + item["quote"] + "”"] + ([item["attribution"]] if item.get("attribution") else [])
    return list(item.get("bullets", []))


def _wrapped(draw, value, font, max_width):
    """Wrap Chinese and English characters using measured visual width."""
    lines, line = [], ""
    for char in value:
        if char == "\n":
            lines.append(line)
            line = ""
            continue
        test = line + char
        if line and draw.textlength(test, font=font) > max_width:
            lines.append(line.rstrip())
            line = char.lstrip()
        else:
            line = test
    if line:
        lines.append(line.rstrip())
    return lines


def render_image(path, item, background, font_file):
    """Render bilingual layout inside the slide area above the subtitle video."""
    from PIL import Image, ImageDraw, ImageFont
    img = Image.new("RGB", (1600, 684), rgb(background))
    draw = ImageDraw.Draw(img)
    ink = rgb(palette(background)["text_color"])
    accent = ink
    font = lambda size: ImageFont.truetype(str(font_file), size)
    draw.rounded_rectangle((85, 35, 96, 178), radius=5, fill=accent)
    draw.text((115, 34), item["section"].upper(), font=font(20), fill=accent)
    title_font = font(38)
    title_lines = _wrapped(draw, item["title"], title_font, 1390)
    if len(title_lines) > 2:
        raise ValueError(f"Slide title overflows: {item['title'][:60]!r}")
    for line_no, line in enumerate(title_lines):
        draw.text((115, 86+line_no*42), line, font=title_font, fill=ink)
    draw.line((85, 180, 1515, 180), fill=ink, width=2)
    if item["layout"] in {"table", "comparison"}:
        table = item["table"]
        cols, rows = table["columns"], table["rows"]
        left, top, right = 85, 205, 1515
        bottom = 595 if table["footnote"] else 650
        rowheight = (bottom - top) / (len(rows) + 1)
        colwidth = (right - left) / len(cols)
        header_font, row_font = font(25), font(22)
        for ri, row in enumerate([{"cells": cols, "emphasis": True}]+rows):
            y0, y1 = top+ri*rowheight, top+(ri+1)*rowheight
            fill = (220, 234, 237) if ri == 0 else ((236, 244, 246) if row["emphasis"] else (255, 255, 255))
            for ci, cell in enumerate(row["cells"]):
                x0, x1 = left+ci*colwidth, left+(ci+1)*colwidth
                draw.rectangle((x0, y0, x1, y1), fill=fill, outline=(183, 199, 204), width=2)
                current_font = header_font if ri == 0 else row_font
                lines = _wrapped(draw, cell, current_font, colwidth-24)
                if len(lines) > 2 or len(lines)*27 > rowheight-7:
                    raise ValueError(f"Slide table cell overflows: {cell[:45]!r}")
                y = y0+(rowheight-len(lines)*27)/2
                for line in lines:
                    draw.text((x0+12, y), line, font=current_font, fill=ink)
                    y += 27
        if table["footnote"]:
            notes = _wrapped(draw, "Note / 注：" + table["footnote"], font(19), right-left)
            if len(notes) > 2:
                raise ValueError("Table footnote is too long for slide")
            for line_no, line in enumerate(notes):
                draw.text((left, 608+line_no*27), line, font=font(19), fill=ink)
    else:
        lines = body_lines(item)
        rowheight = min(82, int(430/max(1, len(lines))) )
        body_font = font(28 if len(lines) <= 5 else 25)
        y = 210
        for content in lines:
            draw.rounded_rectangle((85, y, 1515, y+rowheight-8), radius=12,
                                   fill=(255,255,255), outline=(201,211,217), width=2)
            wrapped = _wrapped(draw, content, body_font, 1365)
            if len(wrapped) > 2 or len(wrapped)*33 > rowheight-12:
                raise ValueError(f"Slide body overflows: {content[:45]!r}")
            text_y = y + (rowheight-8-len(wrapped)*33)/2
            for line in wrapped:
                draw.text((113, text_y), line, font=body_font, fill=ink)
                text_y += 33
            y += rowheight
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    img.save(path)
