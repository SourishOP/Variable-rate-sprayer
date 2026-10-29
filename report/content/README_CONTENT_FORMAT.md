# Content file format (for build_report.py)

Each `chNN_*.md` file is one chapter. Convention used by the build script:

- Line `# <Title>` once at the top: the chapter title (no "CHAPTER n" prefix;
  the build script adds that on the chapter's first page).
- `## n.n TITLE` : a section heading (numbered manually here, matches what
  prints; build script just renders it, does not renumber).
- `### n.n.n Title` : a subsection heading (title case, build script bolds it).
- Plain paragraphs: normal running text, 1.5 line spacing, Times New Roman 12pt.
- Figure placement + caption + numbering:
  `{{FIG:short_id|relative/path/from/final_report.png|Caption sentence.}}`
  on its own line. Numbering is assigned by the build script in document
  order as "Figure <chapter>.<n>".
- Table placement + caption + numbering:
  `{{TABLE:short_id|Caption sentence.}}` on its own line, followed directly
  by a GitHub-flavoured markdown pipe table (header row, `---` divider row,
  data rows). Numbering is "Table <chapter>.<n>".
- Cross references inside prose: `{{REF:short_id}}` is replaced by
  "Figure 4.2" or "Table 5.1" (whichever short_id resolves to) in a second
  pass once every chapter file has been scanned.
- Citations: plain parenthetical text `(Tewari et al., 2020)` - matched
  against `content/references.json` by the build script for the reference
  list and the in-text citation check. Not a special tag.
- A line of exactly `---PAGEBREAK---` forces a new page (used sparingly,
  e.g. before a big table that should not split awkwardly).
