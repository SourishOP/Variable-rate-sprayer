"""Low level OOXML helpers that python-docx does not expose directly:
real page-number fields with roman/arabic restart, TOC/PAGEREF fields,
bookmarks, highlighting, and section page-number formatting.
"""
from docx.oxml.ns import qn
from docx.oxml import OxmlElement


def _new(tag, **attrs):
    el = OxmlElement(tag)
    for k, v in attrs.items():
        el.set(qn(k), str(v))
    return el


_bookmark_id = [0]


def add_bookmark(paragraph, name):
    """Wrap a bookmark start/end around the paragraph's existing runs so the
    whole caption/heading can be targeted by a PAGEREF field."""
    _bookmark_id[0] += 1
    bid = str(_bookmark_id[0])
    start = _new("w:bookmarkStart", **{"w:id": bid, "w:name": name})
    end = _new("w:bookmarkEnd", **{"w:id": bid})
    paragraph._p.insert(0, start)
    paragraph._p.append(end)


def add_field(paragraph, field_code, result_text="1", bold=False):
    """Insert a simple Word field (fldSimple is adequate for PAGE/PAGEREF/TOC
    display text before the first 'update fields' pass)."""
    run = paragraph.add_run()
    fld = _new("w:fldSimple", **{"w:instr": field_code})
    r = _new("w:r")
    rpr = _new("w:rPr")
    if bold:
        rpr.append(_new("w:b"))
    rpr.append(_new("w:rFonts", **{"w:ascii": "Times New Roman", "w:hAnsi": "Times New Roman"}))
    r.append(rpr)
    t = _new("w:t")
    t.text = result_text
    r.append(t)
    fld.append(r)
    run._r.addnext(fld)
    run._r.getparent().remove(run._r)
    return paragraph


def add_toc_field(paragraph, instr):
    run = paragraph.add_run()
    fld = _new("w:fldSimple", **{"w:instr": instr})
    r = _new("w:r")
    t = _new("w:t")
    t.text = "Right-click and choose Update Field after opening in Word."
    r.append(t)
    fld.append(r)
    run._r.addnext(fld)
    run._r.getparent().remove(run._r)


def set_page_number_format(section, fmt="decimal", start=None):
    """fmt: 'decimal' or 'lowerRoman'. start: integer restart value or None."""
    sectPr = section._sectPr
    existing = sectPr.find(qn("w:pgNumType"))
    if existing is not None:
        sectPr.remove(existing)
    el = _new("w:pgNumType", **{"w:fmt": fmt})
    if start is not None:
        el.set(qn("w:start"), str(start))
    sectPr.append(el)


def set_footer_page_number(section, fmt="decimal", start=None, centered=True):
    """Give this section its own (unlinked) footer with a centred PAGE field,
    and set this section's page-number format/restart."""
    set_page_number_format(section, fmt=fmt, start=start)
    footer = section.footer
    footer.is_linked_to_previous = False
    for p in list(footer.paragraphs):
        p._p.getparent().remove(p._p)
    p = footer.add_paragraph()
    if centered:
        from docx.enum.text import WD_ALIGN_PARAGRAPH
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    for run in list(p.runs):
        run._r.getparent().remove(run._r)
    add_field(p, "PAGE", "1")
    for run in p.runs:
        run.font.name = "Times New Roman"
        run.font.size = None


def clear_page_number_restart(section):
    """Remove any inherited w:start restart from this section's pgNumType.

    python-docx clones the previous section's sectPr (pgNumType included)
    whenever doc.add_section() is called. If the previous section had an
    explicit restart (w:start="1", as the roman and arabic front/body
    sections do), every later CONTINUOUS section silently inherits that
    same restart and Word repaginates each one back to page 1. Call this on
    every section added after the two intentional restarts (front matter
    roman numerals, chapter 1 arabic numerals) so later sections (the
    appendix code-listing columns) simply continue the running page count.
    """
    sectPr = section._sectPr
    pgnum = sectPr.find(qn("w:pgNumType"))
    if pgnum is None:
        return
    start_attr = qn("w:start")
    if pgnum.get(start_attr) is not None:
        del pgnum.attrib[start_attr]
    if not pgnum.attrib:
        sectPr.remove(pgnum)


def clear_footer(section):
    footer = section.footer
    footer.is_linked_to_previous = False
    for p in list(footer.paragraphs):
        p._p.getparent().remove(p._p)
    footer.add_paragraph()


def set_no_header_footer_diff(section):
    section.different_first_page_header_footer = False
