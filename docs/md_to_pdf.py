#!/usr/bin/env python3
"""Convert demo-script.md to a styled PDF using fpdf2 + markdown."""

import re
import os
from fpdf import FPDF
from markdown import markdown
from html.parser import HTMLParser


class MDContent:
    """Parse markdown into structured blocks for PDF rendering."""

    def __init__(self, md_text):
        self.blocks = []
        self._parse(md_text)

    def _parse(self, text):
        lines = text.split("\n")
        i = 0
        while i < len(lines):
            line = lines[i]

            # Blank line
            if not line.strip():
                i += 1
                continue

            # Horizontal rule
            if line.strip() in ("---", "***", "___"):
                self.blocks.append(("hr", None))
                i += 1
                continue

            # Headers
            if line.startswith("# "):
                self.blocks.append(("h1", line[2:].strip()))
                i += 1
                continue
            if line.startswith("## "):
                self.blocks.append(("h2", line[3:].strip()))
                i += 1
                continue
            if line.startswith("### "):
                self.blocks.append(("h3", line[4:].strip()))
                i += 1
                continue

            # Table
            if "|" in line and i + 1 < len(lines) and re.match(r"^\|[\s\-|]+\|$", lines[i + 1].strip()):
                rows = []
                while i < len(lines) and "|" in lines[i]:
                    cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                    # Skip separator row
                    if not re.match(r"^[\s\-|]+$", lines[i].strip().strip("|")):
                        rows.append(cells)
                    i += 1
                self.blocks.append(("table", rows))
                continue

            # Bullet list
            if line.startswith("- "):
                items = []
                while i < len(lines) and lines[i].startswith("- "):
                    items.append(lines[i][2:].strip())
                    i += 1
                self.blocks.append(("bullets", items))
                continue

            # Regular paragraph (collect consecutive lines)
            para_lines = []
            while i < len(lines) and lines[i].strip() and not lines[i].startswith("#") and not lines[i].startswith("---") and not lines[i].startswith("- ") and "|" not in lines[i]:
                para_lines.append(lines[i])
                i += 1
            if para_lines:
                self.blocks.append(("para", " ".join(para_lines)))


class DemoPDF(FPDF):
    MARGIN = 15
    PAGE_W = 210 - 30  # A4 width minus margins

    def __init__(self):
        super().__init__()
        self.set_auto_page_break(auto=True, margin=20)
        self.set_margins(self.MARGIN, self.MARGIN, self.MARGIN)

        # Register DejaVu for Unicode support if available, else use Helvetica
        self.use_builtin = True
        self.add_page()

    def _set_font(self, style="", size=10):
        self.set_font("Helvetica", style, size)

    def _strip_md_formatting(self, text):
        """Remove markdown bold/italic/code markers and return plain text."""
        text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
        text = re.sub(r"\*(.+?)\*", r"\1", text)
        text = re.sub(r"`(.+?)`", r"\1", text)
        return self._sanitize(text)

    def _sanitize(self, text):
        """Replace Unicode chars that Helvetica can't render."""
        text = text.replace("\u2014", "--")   # em dash
        text = text.replace("\u2013", "-")    # en dash
        text = text.replace("\u2018", "'")    # left single quote
        text = text.replace("\u2019", "'")    # right single quote
        text = text.replace("\u201c", '"')    # left double quote
        text = text.replace("\u201d", '"')    # right double quote
        text = text.replace("\u2022", "-")    # bullet
        text = text.replace("\u2026", "...")  # ellipsis
        text = text.replace("\u2192", "->")   # arrow
        return text

    def _write_rich_text(self, text, base_size=10):
        """Write text with bold/code inline formatting."""
        # Split on **bold** and `code` patterns
        parts = re.split(r"(\*\*.*?\*\*|`.*?`)", text)
        for part in parts:
            if part.startswith("**") and part.endswith("**"):
                self._set_font("B", base_size)
                self.write(5, self._sanitize(part[2:-2]))
            elif part.startswith("`") and part.endswith("`"):
                self._set_font("B", base_size - 1)
                self.set_text_color(80, 80, 80)
                self.write(5, self._sanitize(part[1:-1]))
                self.set_text_color(0, 0, 0)
            else:
                self._set_font("", base_size)
                self.write(5, self._sanitize(part))
        self.ln(6)

    def render_h1(self, text):
        self._set_font("B", 18)
        self.set_text_color(30, 30, 30)
        self.cell(0, 12, self._strip_md_formatting(text), new_x="LMARGIN", new_y="NEXT")
        # Underline
        self.set_draw_color(60, 60, 60)
        self.set_line_width(0.5)
        y = self.get_y()
        self.line(self.MARGIN, y, self.MARGIN + self.PAGE_W, y)
        self.ln(6)
        self.set_text_color(0, 0, 0)

    def render_h2(self, text):
        self.ln(2)
        self._set_font("B", 13)
        self.set_text_color(40, 40, 120)
        self.cell(0, 9, self._strip_md_formatting(text), new_x="LMARGIN", new_y="NEXT")
        self.ln(2)
        self.set_text_color(0, 0, 0)

    def render_h3(self, text):
        self.ln(1)
        self._set_font("B", 11)
        self.set_text_color(60, 60, 60)
        self.cell(0, 8, self._strip_md_formatting(text), new_x="LMARGIN", new_y="NEXT")
        self.ln(2)
        self.set_text_color(0, 0, 0)

    def render_hr(self):
        self.ln(3)
        self.set_draw_color(180, 180, 180)
        self.set_line_width(0.3)
        y = self.get_y()
        self.line(self.MARGIN, y, self.MARGIN + self.PAGE_W, y)
        self.ln(5)

    def render_bullets(self, items):
        self._set_font("", 10)
        for item in items:
            x = self.get_x()
            self.cell(6, 5, "-")
            self._write_rich_text(item, 10)
        self.ln(2)

    def render_para(self, text):
        self._set_font("", 10)
        self._write_rich_text(text, 10)
        self.ln(2)

    def _measure_cell_height(self, width, line_height, text):
        """Use dry_run multi_cell to measure the actual height a cell needs."""
        # Save state
        x, y = self.get_x(), self.get_y()
        # dry_run returns the number of lines/height used
        self.multi_cell(width, line_height, text, dry_run=True, output="LINES")
        lines = self.multi_cell(width, line_height, text, dry_run=True, output="LINES")
        height = len(lines) * line_height
        # Restore position
        self.set_xy(x, y)
        return max(line_height, height)

    def _draw_row(self, row_cells, col_widths, line_height, is_header=False, fill_color=None):
        """Draw a table row with uniform height across all cells."""
        x_start = self.get_x()
        y_start = self.get_y()

        # Step 1: Measure the height each cell needs
        cell_heights = []
        for j, cell_text in enumerate(row_cells):
            if is_header:
                self._set_font("B", 9)
            else:
                self._set_font("", 8)
            h = self._measure_cell_height(col_widths[j], line_height, cell_text)
            cell_heights.append(h)

        row_height = max(cell_heights)

        # Step 2: Page break check
        if y_start + row_height > 280:
            self.add_page()
            y_start = self.get_y()

        # Step 3: Draw filled/bordered rectangles first (uniform height)
        for j in range(len(row_cells)):
            x = x_start + sum(col_widths[:j])
            if is_header:
                self.set_fill_color(60, 60, 120)
            elif fill_color:
                self.set_fill_color(*fill_color)
            self.rect(x, y_start, col_widths[j], row_height, style="DF")

        # Step 4: Draw text inside each cell
        for j, cell_text in enumerate(row_cells):
            x = x_start + sum(col_widths[:j])
            if is_header:
                self._set_font("B", 9)
                self.set_text_color(255, 255, 255)
            else:
                self._set_font("", 8)
                self.set_text_color(0, 0, 0)
            # Small padding inside cell
            self.set_xy(x + 1, y_start + 1)
            self.multi_cell(col_widths[j] - 2, line_height, cell_text, border=0, new_x="RIGHT", new_y="TOP")

        # Reset text color
        self.set_text_color(0, 0, 0)

        # Move below the row
        self.set_xy(x_start, y_start + row_height)

    def render_table(self, rows):
        if not rows:
            return

        num_cols = len(rows[0])
        # Calculate column widths proportionally
        if num_cols == 2:
            col_widths = [self.PAGE_W * 0.35, self.PAGE_W * 0.65]
        elif num_cols == 3:
            col_widths = [self.PAGE_W * 0.18, self.PAGE_W * 0.30, self.PAGE_W * 0.52]
        else:
            w = self.PAGE_W / num_cols
            col_widths = [w] * num_cols

        line_height = 5
        self.set_draw_color(160, 160, 180)
        self.set_line_width(0.3)

        # Header row
        if rows:
            header_cells = [self._strip_md_formatting(c) for c in rows[0]]
            self._draw_row(header_cells, col_widths, line_height, is_header=True)

        # Data rows
        for i, row in enumerate(rows[1:]):
            fill = (240, 240, 250) if i % 2 == 0 else (255, 255, 255)
            data_cells = [self._strip_md_formatting(c) for c in row]
            self._draw_row(data_cells, col_widths, line_height, is_header=False, fill_color=fill)

        self.ln(4)

    def build(self, blocks):
        for btype, data in blocks:
            # Check if we need a new page (leave room)
            if self.get_y() > 270 and btype in ("h2", "h3", "table"):
                self.add_page()

            if btype == "h1":
                self.render_h1(data)
            elif btype == "h2":
                self.render_h2(data)
            elif btype == "h3":
                self.render_h3(data)
            elif btype == "hr":
                self.render_hr()
            elif btype == "bullets":
                self.render_bullets(data)
            elif btype == "para":
                self.render_para(data)
            elif btype == "table":
                self.render_table(data)


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    md_path = os.path.join(script_dir, "demo-script.md")
    pdf_path = os.path.join(script_dir, "demo-script.pdf")

    with open(md_path, "r") as f:
        md_text = f.read()

    content = MDContent(md_text)
    pdf = DemoPDF()
    pdf.build(content.blocks)
    pdf.output(pdf_path)
    print(f"PDF saved to: {pdf_path}")


if __name__ == "__main__":
    main()
