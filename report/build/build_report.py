"""Assemble the two final BCE497J report DOCX files from the content/*.md
chapters, references.json and facts.json, following the template rules in
the BCE497J report template rules.

Run with the doc-building venv:
  %LOCALAPPDATA%/final_report_work/venv/Scripts/python.exe build_report.py

Produces:
  report/output/BCE497J_Final_Report_23BCE1179_SourishDas.docx
  report/output/BCE497J_Final_Report_23BCE1293_AdityaSingh.docx
"""
import json
import os
import re
import sys

from PIL import Image

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.shared import Cm, Pt, RGBColor
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from docx.enum.text import WD_COLOR_INDEX

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from docx_helpers import (  # noqa: E402
    add_field, add_toc_field, set_footer_page_number, clear_footer,
    clear_page_number_restart,
)

ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
FR = os.path.join(ROOT, "report")
CONTENT = os.path.join(FR, "content")
FIGDIR = FR  # fig paths in md are "figures/xxx.png", relative to FR
OUTDIR = os.path.join(FR, "output")
os.makedirs(OUTDIR, exist_ok=True)

TNR = "Times New Roman"
COURIER = "Courier New"
TEXT_WIDTH_CM = 14.65
MAX_FIG_HEIGHT_CM = 19.5

TEAM = [
    {"name": "Sourish Das", "reg": "23BCE1179", "file_slug": "23BCE1179_SourishDas"},
    {"name": "Aditya Singh", "reg": "23BCE1293", "file_slug": "23BCE1293_AdityaSingh"},
]
GUIDE_NAME = "Dr. Vergin Raja Sarobin M."
GUIDE_DESIGNATION = "[[ENTER GUIDE DESIGNATION, e.g. Associate Professor]]"
GUIDE_AREA = "[[ENTER GUIDE'S AREA OF EXPERTISE]]"
HOD_NAME = "[[ENTER HOD NAME]]"
PROGRAMME = "Computer Science and Engineering"
PROGRAMME_FULL = "Bachelor of Technology in Computer Science and Engineering"
SCHOOL = "School of Computer Science and Engineering"
PLACE = "Chennai"
MONTH_YEAR = "November, 2026"
TITLE = ("Deep Learning and IoT-Based Real-Time Variable-Rate Chemical "
         "Spraying System for Disease Control in Paddy Crop")
LOGO = os.path.join(FR, "figures", "vit_logo.jpg")

CHAPTERS = [
    ("ch01_introduction.md", 1),
    ("ch02_literature_survey.md", 2),
    ("ch03_technical_specification.md", 3),
    ("ch04_system_design.md", 4),
    ("ch05_hardware_implementation.md", 5),
    ("ch06_software_implementation.md", 6),
    ("ch07_schedule.md", 7),
    ("ch08_testing.md", 8),
    ("ch09_results_discussion.md", 9),
    ("ch10_conclusion.md", 10),
]

APPENDIX_SOURCES = [
    ("Appendix 1", "Severity and Dosing Logic (model/severity.py)", os.path.join(ROOT, "model", "severity.py")),
    ("Appendix 2", "Single Image Command Line Prediction (model/predict.py)", os.path.join(ROOT, "model", "predict.py")),
    ("Appendix 3", "Flask Inference API (app/server.py)", os.path.join(ROOT, "app", "server.py")),
    ("Appendix 4", "ESP32-CAM Firmware (firmware/esp32cam_sprayer/esp32cam_sprayer.ino)",
     os.path.join(ROOT, "firmware", "esp32cam_sprayer", "esp32cam_sprayer.ino")),
    ("Appendix 5", "Arduino Nano Firmware (firmware/valve_controller/valve_controller.ino)",
     os.path.join(ROOT, "firmware", "valve_controller", "valve_controller.ino")),
]

ABSTRACT_TEXT = """Farmers usually spray the same amount of chemical on every plant in a
field, no matter how healthy or how diseased that plant is. This wastes
chemical, raises cost and pollutes the soil and nearby water. We built a
variable rate spraying system for paddy that decides how much chemical to
spray for each plant based on what disease it has and how much of the leaf
is affected. A camera image of a leaf is classified into one of six
classes, a healthy leaf and five diseases, using a trained convolutional
neural network. For a diseased leaf, a separate segmentation model finds
the diseased pixels and reports the diseased area as a percentage of the
leaf area. This severity percentage is mapped to a category and a base
dosing coefficient, which is then scaled by a factor that depends on the
diagnosed disease, since some diseases need a relatively higher dose at the
same severity level. The resulting coefficient sets the chemical volume per
plant and the time the spray valve should stay open. A compact hardware
design built around an ESP32-CAM and an Arduino Nano is specified to carry
out this decision in the field, with a Blynk dashboard for remote
monitoring and a web demonstration interface for showing the full decision
process on one uploaded photograph. The classifier reached 91.5 percent
accuracy on an initial three class test set and 83.80 to 87.08 percent on
the harder six class merged dataset. A full software simulation on 49 real
test images showed a 40 to 43 percent reduction in chemical use against a
constant full rate baseline, ahead of the 33.88 percent minimum saving
reported by the base paper this project builds on. The physical hardware
prototype's bench, integration and field test results depend on evidence
the team supplies separately and are reported in this document exactly as
available at the time of writing."""

ACK_TEXT_PARA1 = ("It is my pleasure to express my deep gratitude to {guide}, "
                   "{designation}, {school}, Vellore Institute of Technology, "
                   "Chennai, for the constant guidance, the patience and the "
                   "steady encouragement given throughout this project. Working "
                   "under this guidance gave me the chance to learn from someone "
                   "with real expertise in {area}, and that experience went well "
                   "beyond the academic requirements of this course.")
ACK_TEXT_PARA2 = ("It is with gratitude that I would like to extend my thanks to "
                   "the visionary leader Dr. G. Viswanathan our Honorable "
                   "Chancellor, Mr. Sankar Viswanathan, Dr. Sekar Viswanathan, "
                   "Dr. G V Selvam Vice Presidents, Dr. Sandhya Pentareddy, "
                   "Executive Director, Ms. Kadhambari S. Viswanathan, Assistant "
                   "Vice-President, Dr. V. S. Kanchana Bhaaskaran Vice-Chancellor, "
                   "Dr. T. Thyagarajan Pro-Vice Chancellor, VIT Chennai and "
                   "Dr. P. K. Manoharan, Additional Registrar for providing an "
                   "exceptional working environment and for inspiring all of us "
                   "during the course of this programme.")
ACK_TEXT_PARA3 = ("Special mention to Dr. Viswanathan V, Dean, Dr. Nithyanandam P, "
                   "Associate Dean, Dr. Suganya G, Associate Dean, Dr. Sweetlin "
                   "Hemalatha C, Associate Dean, School of Computer Science and "
                   "Engineering, Vellore Institute of Technology, Chennai, for "
                   "sharing their time and their knowledge and for helping us at "
                   "every stage of this project.")
ACK_TEXT_PARA4 = ("I sincerely thank {hod}, Head of the Department, B.Tech. "
                   "{programme}, and the Project Coordinators for their support "
                   "and encouragement in taking up and completing this project.")
ACK_TEXT_PARA5 = ("My sincere thanks also go to all the faculty and staff at "
                   "Vellore Institute of Technology, Chennai, who helped me "
                   "learn what this project needed. I thank my parents for "
                   "their support, and my friends who encouraged me to take up "
                   "and finish this work. This report was written with the "
                   "help of AI based writing and drafting tools, used under my "
                   "own direction and checked by me; the system design, the "
                   "code and the results described in it are the team's own "
                   "work.")

DECLARATION_TEXT_1 = ('I hereby declare that the thesis entitled "{title}" '
                       "submitted by me ({name}, {reg}), for the award of the "
                       "degree of Bachelor of Technology in Computer Science "
                       "and Engineering, Vellore Institute of Technology, "
                       "Chennai, is a record of bonafide work carried out by "
                       "me under the supervision of {guide}.")
DECLARATION_TEXT_2 = ("I further declare that the work reported in this thesis "
                       "has not been submitted and will not be submitted, "
                       "either in part or in full, for the award of any other "
                       "degree or diploma in this institute or any other "
                       "institute or university.")

CERTIFICATE_TEXT = ('This is to certify that the report entitled "{title}" is '
                     "prepared and submitted by {name} ({reg}) to Vellore "
                     "Institute of Technology, Chennai, in partial fulfilment "
                     "of the requirement for the award of the degree of "
                     "Bachelor of Technology in {programme}, and is a bonafide "
                     "record of work carried out under my guidance. The "
                     "project fulfils the requirements as per the regulations "
                     "of this University, and in my opinion meets the "
                     "necessary standards for submission. The contents of "
                     "this report have not been submitted and will not be "
                     "submitted, either in part or in full, for the award of "
                     "any other degree or diploma, and the same is certified.")

ABBREVIATIONS = [
    ("VRA", "Variable Rate Application"),
    ("CRA", "Constant Rate Application"),
    ("CNN", "Convolutional Neural Network"),
    ("CA", "Chromatic Aberration"),
    ("IoT", "Internet of Things"),
    ("API", "Application Programming Interface"),
    ("UI", "User Interface"),
    ("HTTP", "Hypertext Transfer Protocol"),
    ("JPEG", "Joint Photographic Experts Group (image format)"),
    ("JSON", "JavaScript Object Notation"),
    ("WiFi", "Wireless Fidelity"),
    ("GPIO", "General Purpose Input Output"),
    ("DFD", "Data Flow Diagram"),
    ("UML", "Unified Modeling Language"),
    ("IoU", "Intersection over Union"),
    ("F1", "F1 score (harmonic mean of precision and recall)"),
    ("SVM", "Support Vector Machine"),
    ("GPU", "Graphics Processing Unit"),
    ("TFLite", "TensorFlow Lite"),
    ("PWM", "Pulse Width Modulation"),
    ("NC", "Normally Closed"),
    ("NO", "Normally Open"),
    ("DC", "Direct Current"),
    ("mL", "Millilitre"),
    ("mA", "Milliampere"),
    ("mAh", "Milliampere hour"),
    ("RD", "Reduction, percent chemical reduction"),
    ("RSD", "Relative Standard Deviation"),
    ("mIoU", "Mean Intersection over Union"),
    ("mAcc", "Mean Pixel Accuracy"),
    ("UCI", "University of California, Irvine (dataset repository)"),
    ("API", "Application Programming Interface"),
]
# de-duplicate (API appears twice above by accident of drafting)
seen_ab = set()
_ab2 = []
for a, b in ABBREVIATIONS:
    if a not in seen_ab:
        _ab2.append((a, b))
        seen_ab.add(a)
ABBREVIATIONS = _ab2


# --------------------------------------------------------------------------- #
# facts / references
# --------------------------------------------------------------------------- #

def load_json(name):
    with open(os.path.join(CONTENT, name), encoding="utf-8") as f:
        return json.load(f)


def load_chapters():
    chs = []
    for fname, num in CHAPTERS:
        with open(os.path.join(CONTENT, fname), encoding="utf-8") as f:
            text = f.read()
        chs.append({"num": num, "fname": fname, "text": text})
    return chs


def filter_cited_references(chapters, refs):
    """A reference counts as cited if it appears either in parenthetical form
    ("... (Oberti et al., 2016) ...") or in narrative form
    ("Oberti et al. (2016) built ..."), since both are valid APA in-text
    citation styles and the chapters use both."""
    all_text = "\n".join(c["text"] for c in chapters)
    cited = []
    for r in refs:
        parenthetical = r["intext"]
        narrative = parenthetical.replace(" al., ", " al. (") + ")"
        if parenthetical in all_text or narrative in all_text:
            cited.append(r)
    cited.sort(key=lambda r: r["apa"].lower())
    return cited


# --------------------------------------------------------------------------- #
# markdown -> block parser
# --------------------------------------------------------------------------- #

def parse_markdown(text):
    """Return a list of block dicts from one chapter's markdown text."""
    lines = text.split("\n")
    blocks = []
    buf = []
    i = 0
    n = len(lines)

    def flush():
        if buf:
            joined = " ".join(s.strip() for s in buf if s.strip())
            if joined:
                blocks.append({"type": "para", "text": joined})
            buf.clear()

    while i < n:
        line = lines[i]
        stripped = line.strip()

        if stripped == "":
            flush()
            i += 1
            continue

        if stripped.startswith("# ") and not stripped.startswith("##"):
            flush()
            blocks.append({"type": "title", "text": stripped[2:].strip()})
            i += 1
            continue

        if stripped.startswith("## "):
            flush()
            blocks.append({"type": "h2", "text": stripped[3:].strip()})
            i += 1
            continue

        if stripped.startswith("### "):
            flush()
            blocks.append({"type": "h3", "text": stripped[4:].strip()})
            i += 1
            continue

        if stripped == "---PAGEBREAK---":
            flush()
            blocks.append({"type": "pagebreak"})
            i += 1
            continue

        if stripped.startswith("```"):
            flush()
            code_lines = []
            i += 1
            while i < n and not lines[i].strip().startswith("```"):
                code_lines.append(lines[i])
                i += 1
            i += 1  # skip closing fence
            blocks.append({"type": "code", "lines": code_lines})
            continue

        m = re.match(r"^\{\{FIG:([a-zA-Z0-9_]+)\|([^|]+)\|(.+)\}\}$", stripped)
        if m:
            flush()
            blocks.append({"type": "fig", "id": m.group(1), "path": m.group(2),
                            "caption": m.group(3)})
            i += 1
            continue

        m = re.match(r"^\{\{TABLE:([a-zA-Z0-9_]+)\|(.+)\}\}$", stripped)
        if m:
            flush()
            tid, caption = m.group(1), m.group(2)
            i += 1
            rows = []
            while i < n and lines[i].strip().startswith("|"):
                rows.append(lines[i].strip())
                i += 1
            # first row header, second row divider, rest data
            header = _split_row(rows[0]) if rows else []
            data_rows = [_split_row(r) for r in rows[2:]] if len(rows) > 2 else []
            blocks.append({"type": "table", "id": tid, "caption": caption,
                            "header": header, "rows": data_rows})
            continue

        m = re.match(r"^(\d+)\.\s+(.*)$", stripped)
        if m:
            flush()
            item_lines = [m.group(2)]
            i += 1
            while i < n:
                nxt = lines[i]
                nxt_stripped = nxt.strip()
                if nxt_stripped == "":
                    break
                if re.match(r"^\d+\.\s+", nxt_stripped):
                    break
                if nxt_stripped.startswith(("#", "{{", "```")):
                    break
                item_lines.append(nxt_stripped)
                i += 1
            blocks.append({"type": "listitem", "text": " ".join(item_lines), "num": m.group(1)})
            continue

        buf.append(line)
        i += 1

    flush()
    return blocks


def _split_row(row):
    cells = row.strip().strip("|").split("|")
    return [c.strip() for c in cells]


def _is_divider(cells):
    return all(re.match(r"^:?-+:?$", c) for c in cells)


# --------------------------------------------------------------------------- #
# inline markup -> runs
# --------------------------------------------------------------------------- #

_TOKEN_RE = re.compile(r"(\*\*.+?\*\*|`[^`]+?`|\[\[[^\]]+?\]\])")


def add_runs_with_markup(paragraph, text, size=12, base_bold=False):
    tokens = _TOKEN_RE.split(text)
    for tok in tokens:
        if not tok:
            continue
        if tok.startswith("**") and tok.endswith("**"):
            r = paragraph.add_run(tok[2:-2])
            r.bold = True
            r.font.name = TNR
            r.font.size = Pt(size)
        elif tok.startswith("`") and tok.endswith("`"):
            r = paragraph.add_run(tok[1:-1])
            r.font.name = COURIER
            r.font.size = Pt(size - 1)
        elif tok.startswith("[[") and tok.endswith("]]"):
            r = paragraph.add_run(tok)
            r.font.name = TNR
            r.font.size = Pt(size)
            r.font.highlight_color = WD_COLOR_INDEX.YELLOW
        else:
            r = paragraph.add_run(tok)
            r.font.name = TNR
            r.font.size = Pt(size)
            r.bold = base_bold


# --------------------------------------------------------------------------- #
# style setup
# --------------------------------------------------------------------------- #

def setup_styles(doc):
    styles = doc.styles

    normal = styles["Normal"]
    normal.font.name = TNR
    normal.font.size = Pt(12)
    pf = normal.paragraph_format
    pf.line_spacing_rule = WD_LINE_SPACING.ONE_POINT_FIVE
    pf.space_after = Pt(6)
    pf.space_before = Pt(0)
    pf.widow_control = True

    def mk(name, base, size, bold=True, caps=False, color=None, align=None,
           keep_next=True, line_single=True, space_before=12, space_after=6):
        try:
            st = styles[name]
        except KeyError:
            from docx.enum.style import WD_STYLE_TYPE
            st = styles.add_style(name, WD_STYLE_TYPE.PARAGRAPH)
            st.base_style = styles[base]
        st.font.name = TNR
        st.font.size = Pt(size)
        st.font.bold = bold
        if color:
            st.font.color.rgb = color
        pf = st.paragraph_format
        if line_single:
            pf.line_spacing_rule = WD_LINE_SPACING.SINGLE
        pf.keep_with_next = keep_next
        pf.space_before = Pt(space_before)
        pf.space_after = Pt(space_after)
        if align:
            pf.alignment = align
        return st

    mk("Heading 1", "Normal", 16, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER,
       space_before=0, space_after=18)
    mk("Heading 2", "Normal", 14, bold=True, space_before=18, space_after=6)
    mk("Heading 3", "Normal", 12, bold=True, space_before=12, space_after=6)
    mk("FigCaption", "Normal", 11, bold=False, align=WD_ALIGN_PARAGRAPH.CENTER,
       keep_next=False, space_before=6, space_after=12)
    mk("TableCaption", "Normal", 11, bold=True, keep_next=True,
       space_before=12, space_after=4)
    mk("CodeStyle", "Normal", 10, bold=False, keep_next=False,
       space_before=0, space_after=0)
    mk("FrontHeading", "Normal", 13, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER,
       space_before=0, space_after=18)
    mk("TOCHeading", "Normal", 12, bold=True, align=WD_ALIGN_PARAGRAPH.LEFT,
       space_before=0, space_after=12)


def set_page_setup(section, left=3.81, right=2.54, top=2.54, bottom=2.54):
    section.page_width = Cm(21.0)
    section.page_height = Cm(29.7)
    section.left_margin = Cm(left)
    section.right_margin = Cm(right)
    section.top_margin = Cm(top)
    section.bottom_margin = Cm(bottom)
    section.gutter = Cm(0)


def set_columns(section, num=1, space_cm=0.6):
    """Set the number of text columns for a section (used to keep the long
    code listing appendices within the page budget)."""
    sectPr = section._sectPr
    existing = sectPr.find(qn("w:cols"))
    if existing is not None:
        sectPr.remove(existing)
    cols = OxmlElement("w:cols")
    cols.set(qn("w:num"), str(num))
    if num > 1:
        cols.set(qn("w:space"), str(int(space_cm * 567)))  # cm -> twentieths of a point
    sectPr.append(cols)


# --------------------------------------------------------------------------- #
# generic content writers
# --------------------------------------------------------------------------- #

def set_table_borders(table):
    tbl = table._tbl
    tblPr = tbl.tblPr
    borders = OxmlElement("w:tblBorders")
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        el = OxmlElement(f"w:{edge}")
        el.set(qn("w:val"), "single")
        el.set(qn("w:sz"), "4")
        el.set(qn("w:space"), "0")
        el.set(qn("w:color"), "444444")
        borders.append(el)
    tblPr.append(borders)


def add_md_table(doc, header, rows, size=11):
    ncols = len(header)
    table = doc.add_table(rows=1, cols=ncols)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    set_table_borders(table)
    hdr_cells = table.rows[0].cells
    for j, text in enumerate(header):
        hdr_cells[j].text = ""
        p = hdr_cells[j].paragraphs[0]
        p.paragraph_format.line_spacing_rule = WD_LINE_SPACING.SINGLE
        add_runs_with_markup(p, text, size=size, base_bold=True)
    for row in rows:
        cells = table.add_row().cells
        for j in range(ncols):
            val = row[j] if j < len(row) else ""
            cells[j].text = ""
            p = cells[j].paragraphs[0]
            p.paragraph_format.line_spacing_rule = WD_LINE_SPACING.SINGLE
            add_runs_with_markup(p, val, size=size)
    return table


def fit_image(path, max_w_cm=TEXT_WIDTH_CM, max_h_cm=MAX_FIG_HEIGHT_CM):
    try:
        with Image.open(path) as im:
            w_px, h_px = im.size
    except Exception:
        return Cm(max_w_cm), None
    aspect = h_px / float(w_px)
    w_cm = max_w_cm
    h_cm = w_cm * aspect
    if h_cm > max_h_cm:
        h_cm = max_h_cm
        w_cm = h_cm / aspect
    return Cm(w_cm), Cm(h_cm)


def render_blocks(doc, blocks, chapter_num, counters, open_items):
    """counters: dict with 'fig' and 'table' ints (mutated), running per chapter."""
    for b in blocks:
        t = b["type"]
        if t == "title":
            continue
        elif t == "h2":
            p = doc.add_paragraph(style="Heading 2")
            add_runs_with_markup(p, b["text"], size=14, base_bold=True)
        elif t == "h3":
            p = doc.add_paragraph(style="Heading 3")
            add_runs_with_markup(p, b["text"], size=12, base_bold=True)
        elif t == "para":
            p = doc.add_paragraph()
            add_runs_with_markup(p, b["text"], size=12)
            if "[[" in b["text"]:
                open_items.append(b["text"])
        elif t == "listitem":
            p = doc.add_paragraph()
            p.paragraph_format.line_spacing_rule = WD_LINE_SPACING.ONE_POINT_FIVE
            p.paragraph_format.space_after = Pt(6)
            p.paragraph_format.left_indent = Cm(0.9)
            num_text = f"{b.get('num', '')}. " if b.get("num") else ""
            add_runs_with_markup(p, num_text + b["text"], size=12)
            if "[[" in b["text"]:
                open_items.append(b["text"])
        elif t == "code":
            for line in b["lines"]:
                p = doc.add_paragraph(style="CodeStyle")
                r = p.add_run(line if line.strip() else " ")
                r.font.name = COURIER
                r.font.size = Pt(10)
        elif t == "pagebreak":
            doc.add_page_break()
        elif t == "fig":
            counters["fig"] += 1
            label = f"{chapter_num}.{counters['fig']}"
            img_path = os.path.join(FR, b["path"])
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.keep_with_next = True
            if os.path.exists(img_path):
                w, h = fit_image(img_path)
                run = p.add_run()
                run.add_picture(img_path, width=w, height=h) if h else run.add_picture(img_path, width=w)
            else:
                add_runs_with_markup(p, f"[[MISSING FIGURE: {b['path']}]]", size=12)
                open_items.append(f"Missing figure file: {b['path']} (id {b['id']})")
            cap = doc.add_paragraph(style="FigCaption")
            add_runs_with_markup(cap, f"Figure {label}: {b['caption']}", size=11)
        elif t == "table":
            counters["table"] += 1
            label = f"{chapter_num}.{counters['table']}"
            cap = doc.add_paragraph(style="TableCaption")
            add_runs_with_markup(cap, f"Table {label}: {b['caption']}", size=11, base_bold=True)
            if b["header"]:
                add_md_table(doc, b["header"], b["rows"])
            doc.add_paragraph().paragraph_format.space_after = Pt(6)


# --------------------------------------------------------------------------- #
# front matter pages
# --------------------------------------------------------------------------- #

def add_logo(doc, width_cm=5.2):
    if os.path.exists(LOGO):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run()
        run.add_picture(LOGO, width=Cm(width_cm))
    else:
        p = doc.add_paragraph("[[VIT LOGO MISSING]]")
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER


def _centered(doc, text, size, bold=False, italic=False, caps=False, space_before=0, space_after=0):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(space_before)
    p.paragraph_format.space_after = Pt(space_after)
    p.paragraph_format.line_spacing_rule = WD_LINE_SPACING.SINGLE
    r = p.add_run(text.upper() if caps else text)
    r.font.name = TNR
    r.font.size = Pt(size)
    r.bold = bold
    r.italic = italic
    return p


def add_cover_or_title_page(doc, with_prefix, team):
    for _ in range(3):
        doc.add_paragraph()
    if with_prefix:
        _centered(doc, "A project report on", 12, italic=True, space_after=18)
    _centered(doc, TITLE, 20, bold=True, caps=True, space_after=18)
    _centered(doc, "Submitted in partial fulfillment for the award of the degree of",
               14, italic=True, space_after=10)
    _centered(doc, PROGRAMME_FULL, 22, bold=True, space_after=18)
    _centered(doc, "by", 14, italic=True, space_after=10)
    for m in team:
        _centered(doc, f"{m['name'].upper()} ({m['reg']})", 16, bold=True, space_after=4)
    for _ in range(2):
        doc.add_paragraph()
    add_logo(doc)
    _centered(doc, SCHOOL, 16, bold=True, space_before=12, space_after=4)
    _centered(doc, MONTH_YEAR, 16, bold=True, caps=True, space_after=0)


def add_declaration_page(doc, member):
    add_logo(doc, width_cm=3.5)
    _centered(doc, "DECLARATION", 13, bold=True, space_before=12, space_after=18)
    p = doc.add_paragraph()
    p.paragraph_format.first_line_indent = Cm(1.27)
    add_runs_with_markup(p, DECLARATION_TEXT_1.format(
        title=TITLE, name=member["name"], reg=member["reg"], guide=GUIDE_NAME), size=12)
    p2 = doc.add_paragraph()
    p2.paragraph_format.first_line_indent = Cm(1.27)
    add_runs_with_markup(p2, DECLARATION_TEXT_2, size=12)
    for _ in range(3):
        doc.add_paragraph()
    pl = doc.add_paragraph(f"Place: {PLACE}")
    pl.runs[0].font.name = TNR
    pl.runs[0].font.size = Pt(12)
    dt = doc.add_paragraph()
    r1 = dt.add_run("Date:")
    r1.font.name = TNR
    r1.font.size = Pt(12)
    dt.paragraph_format.tab_stops.add_tab_stop(Cm(10))
    r2 = dt.add_run("\tSignature of the Candidate")
    r2.font.name = TNR
    r2.font.size = Pt(12)


def add_certificate_page(doc, member):
    add_logo(doc, width_cm=3.5)
    _centered(doc, SCHOOL, 13, bold=True, space_after=6)
    _centered(doc, "CERTIFICATE", 16, bold=True, space_before=12, space_after=18)
    p = doc.add_paragraph()
    p.paragraph_format.first_line_indent = Cm(1.27)
    add_runs_with_markup(p, CERTIFICATE_TEXT.format(
        title=TITLE, name=member["name"], reg=member["reg"], programme=PROGRAMME), size=12)
    for _ in range(2):
        doc.add_paragraph()
    pg = doc.add_paragraph("Signature of the Guide:")
    pg.runs[0].font.name = TNR
    pg.runs[0].font.size = Pt(12)
    pn = doc.add_paragraph(f"Name: {GUIDE_NAME}")
    pn.runs[0].font.name = TNR
    pn.runs[0].font.size = Pt(12)
    pd = doc.add_paragraph("Date:")
    pd.runs[0].font.name = TNR
    pd.runs[0].font.size = Pt(12)
    for _ in range(2):
        doc.add_paragraph()
    pe = doc.add_paragraph("Signature of the Examiner 1" + " " * 20 + "Signature of the Examiner 2")
    pe.runs[0].font.name = TNR
    pe.runs[0].font.size = Pt(12)
    pe2 = doc.add_paragraph("Name:" + " " * 42 + "Name:")
    pe2.runs[0].font.name = TNR
    pe2.runs[0].font.size = Pt(12)
    pe3 = doc.add_paragraph("Date:" + " " * 42 + "Date:")
    pe3.runs[0].font.name = TNR
    pe3.runs[0].font.size = Pt(12)
    for _ in range(2):
        doc.add_paragraph()
    _centered(doc, "Approved by the Head of the Department,", 12, space_after=0)
    _centered(doc, f"B.Tech. {PROGRAMME}", 12, bold=True, space_after=12)
    pn2 = doc.add_paragraph()
    add_runs_with_markup(pn2, f"Name: {HOD_NAME}", size=12)
    pd2 = doc.add_paragraph("Date:")
    pd2.runs[0].font.name = TNR
    pd2.runs[0].font.size = Pt(12)
    for _ in range(2):
        doc.add_paragraph()
    _centered(doc, "(Seal of the School of Computer Science and Engineering)", 9.5)


def add_abstract_page(doc):
    _centered(doc, "ABSTRACT", 14, bold=True, space_before=0, space_after=18)
    p = doc.add_paragraph()
    p.paragraph_format.line_spacing_rule = WD_LINE_SPACING.ONE_POINT_FIVE
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    add_runs_with_markup(p, ABSTRACT_TEXT.replace("\n", " "), size=12)


def add_acknowledgement_page(doc, member):
    _centered(doc, "ACKNOWLEDGEMENT", 13, bold=True, space_before=0, space_after=18)
    for txt in (ACK_TEXT_PARA1.format(guide=GUIDE_NAME, designation=GUIDE_DESIGNATION,
                                        school=SCHOOL, area=GUIDE_AREA),
                ACK_TEXT_PARA2, ACK_TEXT_PARA3,
                ACK_TEXT_PARA4.format(hod=HOD_NAME, programme=PROGRAMME),
                ACK_TEXT_PARA5):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        p.paragraph_format.line_spacing_rule = WD_LINE_SPACING.ONE_POINT_FIVE
        add_runs_with_markup(p, txt, size=12)
    doc.add_paragraph()
    pl = doc.add_paragraph(f"Place: {PLACE}")
    pl.runs[0].font.name = TNR
    pl.runs[0].font.size = Pt(12)
    dt = doc.add_paragraph()
    r1 = dt.add_run("Date:")
    r1.font.name = TNR
    r1.font.size = Pt(12)
    dt.paragraph_format.tab_stops.add_tab_stop(Cm(10))
    r2 = dt.add_run(f"\t{member['name']}")
    r2.font.name = TNR
    r2.font.size = Pt(12)


def add_contents_page(doc):
    _centered(doc, "CONTENTS", 13, bold=True, space_before=0, space_after=18)
    p = doc.add_paragraph()
    p.paragraph_format.line_spacing_rule = WD_LINE_SPACING.SINGLE
    add_toc_field(p, 'TOC \\o "1-3" \\h \\z \\u')


def add_list_of_tables_page(doc):
    _centered(doc, "LIST OF TABLES", 13, bold=True, space_before=0, space_after=18)
    p = doc.add_paragraph()
    p.paragraph_format.line_spacing_rule = WD_LINE_SPACING.SINGLE
    add_toc_field(p, 'TOC \\h \\z \\t "TableCaption,1"')


def add_list_of_figures_page(doc):
    _centered(doc, "LIST OF FIGURES", 13, bold=True, space_before=0, space_after=18)
    p = doc.add_paragraph()
    p.paragraph_format.line_spacing_rule = WD_LINE_SPACING.SINGLE
    add_toc_field(p, 'TOC \\h \\z \\t "FigCaption,1"')


def add_abbreviations_page(doc):
    _centered(doc, "LIST OF SYMBOLS, ABBREVIATIONS AND NOMENCLATURE", 13, bold=True,
               space_before=0, space_after=18)
    table = doc.add_table(rows=1, cols=2)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    set_table_borders(table)
    hdr = table.rows[0].cells
    for j, text in enumerate(["Abbreviation", "Expansion"]):
        p = hdr[j].paragraphs[0]
        add_runs_with_markup(p, text, size=11, base_bold=True)
    for abbr, full in ABBREVIATIONS:
        cells = table.add_row().cells
        p0 = cells[0].paragraphs[0]
        add_runs_with_markup(p0, abbr, size=11)
        p1 = cells[1].paragraphs[0]
        add_runs_with_markup(p1, full, size=11)


# --------------------------------------------------------------------------- #
# references and appendices
# --------------------------------------------------------------------------- #

def add_references(doc, refs):
    p = doc.add_paragraph(style="Heading 1")
    add_runs_with_markup(p, "REFERENCES", size=16, base_bold=True)
    for idx, r in enumerate(refs, start=1):
        para = doc.add_paragraph()
        para.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        para.paragraph_format.line_spacing_rule = WD_LINE_SPACING.SINGLE
        para.paragraph_format.space_after = Pt(8)
        add_runs_with_markup(para, f"[{idx}]. {r['apa']}", size=12)


def add_appendices(doc, open_items):
    p = doc.add_paragraph(style="Heading 1")
    add_runs_with_markup(p, "APPENDICES", size=16, base_bold=True)
    intro = doc.add_paragraph()
    intro.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    add_runs_with_markup(intro, (
        "Appendices are provided to give supplementary information, which is "
        "not included in the main text, and which serves as a separate part "
        "contributing to the main theme. Each appendix carries the title of "
        "the work reported in it, and tables and figures inside an appendix "
        "are numbered and referred to just as in the case of chapters."), size=12)

    for title, subtitle, path in APPENDIX_SOURCES:
        doc.add_page_break()
        hp = doc.add_paragraph(style="Heading 2")
        add_runs_with_markup(hp, f"{title}: {subtitle}", size=14, base_bold=True)
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                code = f.read()
            # Two columns keep these long code listings within the report's
            # overall page budget while staying easily readable (8.5pt mono).
            code_sec = doc.add_section(WD_SECTION.CONTINUOUS)
            set_page_setup(code_sec)
            set_columns(code_sec, num=3, space_cm=0.5)
            # add_section() clones the previous sectPr, including its
            # pgNumType w:start restart. This section must continue the
            # running arabic page count, not restart it at 1.
            clear_page_number_restart(code_sec)
            for line in code.split("\n"):
                cp = doc.add_paragraph(style="CodeStyle")
                cp.paragraph_format.space_after = Pt(0)
                r = cp.add_run(line if line.strip() else " ")
                r.font.name = COURIER
                r.font.size = Pt(8)
            back_sec = doc.add_section(WD_SECTION.CONTINUOUS)
            set_page_setup(back_sec)
            set_columns(back_sec, num=1)
            clear_page_number_restart(back_sec)
        else:
            mp = doc.add_paragraph()
            add_runs_with_markup(mp, f"[[SOURCE FILE MISSING: {path}]]", size=12)
            open_items.append(f"Appendix source missing: {path}")




# --------------------------------------------------------------------------- #
# main build
# --------------------------------------------------------------------------- #

def build_one(member, chapters, refs, facts):
    open_items = []
    doc = Document()
    setup_styles(doc)

    core = doc.core_properties
    core.title = TITLE
    core.author = member["name"]
    core.last_modified_by = member["name"]
    core.subject = "BCE497J Final Review Project Report"
    core.comments = ""

    sec0 = doc.sections[0]
    set_page_setup(sec0)
    clear_footer(sec0)
    add_cover_or_title_page(doc, with_prefix=True, team=TEAM)

    sec1 = doc.add_section(WD_SECTION.NEW_PAGE)
    set_page_setup(sec1)
    clear_footer(sec1)
    add_cover_or_title_page(doc, with_prefix=False, team=TEAM)

    sec2 = doc.add_section(WD_SECTION.NEW_PAGE)
    set_page_setup(sec2)
    clear_footer(sec2)
    add_declaration_page(doc, member)

    sec3 = doc.add_section(WD_SECTION.NEW_PAGE)
    set_page_setup(sec3)
    clear_footer(sec3)
    add_certificate_page(doc, member)

    sec4 = doc.add_section(WD_SECTION.NEW_PAGE)
    set_page_setup(sec4)
    set_footer_page_number(sec4, fmt="lowerRoman", start=1)
    add_abstract_page(doc)
    doc.add_page_break()
    add_acknowledgement_page(doc, member)
    doc.add_page_break()
    add_contents_page(doc)
    doc.add_page_break()
    add_list_of_tables_page(doc)
    doc.add_page_break()
    add_list_of_figures_page(doc)
    doc.add_page_break()
    add_abbreviations_page(doc)

    sec5 = doc.add_section(WD_SECTION.NEW_PAGE)
    set_page_setup(sec5)
    set_footer_page_number(sec5, fmt="decimal", start=1)

    for ch_idx, ch in enumerate(chapters):
        blocks = parse_markdown(ch["text"])
        title_block = next((b for b in blocks if b["type"] == "title"), None)
        chap_title = title_block["text"] if title_block else ch["fname"]
        if ch_idx > 0:
            # sec5 already starts chapter 1 on a fresh page; later chapters
            # need their own explicit page break.
            doc.add_page_break()
        hp = doc.add_paragraph(style="Heading 1")
        add_runs_with_markup(hp, f"CHAPTER {ch['num']}", size=12, base_bold=True)
        hp.paragraph_format.space_after = Pt(6)
        hp2 = doc.add_paragraph(style="Heading 1")
        add_runs_with_markup(hp2, chap_title, size=16, base_bold=True)
        counters = {"fig": 0, "table": 0}
        render_blocks(doc, blocks, ch["num"], counters, open_items)

    doc.add_page_break()
    add_references(doc, refs)

    add_appendices(doc, open_items)

    out_path = os.path.join(OUTDIR, f"BCE497J_Final_Report_{member['file_slug']}.docx")
    doc.save(out_path)
    return out_path, open_items


def main():
    chapters = load_chapters()
    refs_all = load_json("references.json")
    refs = filter_cited_references(chapters, refs_all)
    uncited = [r["key"] for r in refs_all if r not in refs]
    facts = load_json("facts.json")

    results = []
    for member in TEAM:
        path, open_items = build_one(member, chapters, refs, facts)
        results.append((member, path, open_items))
        print("built:", path)

    all_open_items = set()
    for _, _, items in results:
        for it in items:
            all_open_items.add(it)

    report = {
        "uncited_references_dropped": uncited,
        "cited_reference_count": len(refs),
        "open_items_from_build": sorted(all_open_items),
    }
    with open(os.path.join(FR, "build", "build_report_meta.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
