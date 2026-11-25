#!/usr/bin/env python3
"""
Moroccan Legal RAG — Knowledge Base Manager (TUI)

A Textual-based terminal UI for managing the legal knowledge base:
  - Browse PDF files in data/raw/
  - Process PDFs through the extraction → cleaning → normalization → structure pipeline
  - Auto-organize output by legal domain (or let the user choose)
  - View processing results with article counts

Usage:
    python -m tui.app
    python tui/app.py
"""

from __future__ import annotations
from src.core.structure import parse_normalized_text_to_json
from src.core.normalizing import ArabicNormalizer
from src.core.cleaning import LegalTextCleaner
from src.ingestion.extractors.pdf_text import PdfToTextExtractor

import json
import logging
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from textual import work
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical, ScrollableContainer
from textual.css.query import NoMatches
from textual.message import Message
from textual.reactive import reactive
from textual.screen import Screen, ModalScreen
from textual.widgets import (
    Button, Checkbox, DataTable, Footer, Header, Input, Label,
    ListItem, ListView, ProgressBar, RichLog, Select, Static,
)
from textual.worker import Worker, WorkerState

# ---------------------------------------------------------------------------
# Project imports — add project root to sys.path
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
RAW_DIR = PROJECT_ROOT / "data" / "raw"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
METADATA_DIR = PROJECT_ROOT / "data" / "metadata"

# Domain/theme colours
DOMAIN_COLORS = {
    "civil":       "bold cornflower_blue",
    "commercial":  "bold gold1",
    "criminal":    "bold orange3",
    "traffic":     "bold green",
    "tax":         "bold magenta",
    "judicial":    "bold purple",
    "violations":  "bold red",
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def infer_domain(filename: str) -> str:
    """Try to infer legal domain from the PDF filename."""
    name_lower = filename.lower()
    if "trade" in name_lower or "تجارة" in name_lower or "5.96" in name_lower:
        return "commercial"
    if "civil" in name_lower or "مدني" in name_lower:
        return "civil"
    if "penal" in name_lower or "جنائي" in name_lower:
        return "criminal"
    if "route" in name_lower or "سير" in name_lower:
        return "traffic"
    if "constitution" in name_lower or "دستور" in name_lower:
        return "civil"
    if "قضائي" in name_lower:
        return "judicial"
    if "ضري" in name_lower or "ضرا" in name_lower or "tax" in name_lower:
        return "tax"
    if "شغل" in name_lower:
        return "civil"
    if "sanction" in name_lower or "عقوب" in name_lower:
        return "violations"
    return "civil"


def infer_law_name(filename: str) -> str:
    """Try to infer a readable law name from filename."""
    stem = Path(filename).stem
    return stem.replace("-", " ").replace("_", " ").strip()


def human_size(size_bytes: int) -> str:
    for unit in ("B", "KB", "MB"):
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} GB"


def format_time(seconds: float) -> str:
    if seconds < 60:
        return f"{seconds:.1f}s"
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{minutes}m {secs}s"


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

class PdfFile:
    """Represents a single PDF file in the raw directory."""

    def __init__(self, path: Path):
        self.path = path
        self.filename = path.name
        self.size_bytes = path.stat().st_size
        self.domain = infer_domain(self.filename)

    @property
    def size_label(self) -> str:
        return human_size(self.size_bytes)

    @property
    def stem(self) -> str:
        return self.path.stem

    def has_output(self) -> bool:
        """Check if this PDF has already been processed."""
        domain_dir = PROCESSED_DIR / self.domain
        txt = domain_dir / f"{self.stem}.txt"
        jsn = domain_dir / f"{self.stem}.articles.json"
        return txt.exists() and jsn.exists()

    def get_article_count(self) -> int:
        """Return the number of articles in the processed JSON, or 0."""
        domain_dir = PROCESSED_DIR / self.domain
        jsn = domain_dir / f"{self.stem}.articles.json"
        if jsn.exists():
            try:
                with open(jsn) as f:
                    return len(json.load(f))
            except Exception:
                pass
        return 0


class ProcessingResult:
    """Result of processing a single PDF."""

    def __init__(self, pdf: PdfFile, success: bool,
                 method: str = "", chars: int = 0, articles: int = 0,
                 error: str = "", duration: float = 0):
        self.pdf = pdf
        self.success = success
        self.method = method
        self.chars = chars
        self.articles = articles
        self.error = error
        self.duration = duration


# ---------------------------------------------------------------------------
# Processing logic (runs in worker)
# ---------------------------------------------------------------------------

def process_single_pdf(pdf: PdfFile, domain: str | None = None,
                       progress_callback=None) -> ProcessingResult:
    """
    Run the full pipeline on one PDF:
      extract → clean → normalize → structure parse → save
    """
    start = time.time()
    target_domain = domain or pdf.domain

    try:
        if progress_callback:
            progress_callback(f"📄 Extracting text from {pdf.filename}...")

        # Step 1: Extract
        extractor = PdfToTextExtractor(use_ocr=False)
        extraction = extractor.extract(pdf.path)
        method = extraction.metadata.get("method", "unknown")
        total_raw_chars = sum(len(p.text) for p in extraction.pages)

        if progress_callback:
            progress_callback(
                f"✨ Extracted {total_raw_chars:,} chars via {method}")

        # Step 2: Clean
        if progress_callback:
            progress_callback(f"🧹 Cleaning text...")
        cleaner = LegalTextCleaner()
        cleaned = cleaner.clean_extraction_result(extraction)

        if progress_callback:
            progress_callback(f"🧼 Cleaned: {cleaned.stats['cleaned_chars']:,} chars "
                              f"(removed {cleaned.stats['chars_removed']:,})")

        # Step 3: Normalize
        if progress_callback:
            progress_callback(f"🔤 Normalizing Arabic text...")
        normalizer = ArabicNormalizer({
            "unify_alef": True,
            "remove_tatweel": True,
            "remove_diacritics": True,
            "preserve_shadda": False,
            "unify_digits": True,
        })
        normalized = normalizer.normalize(cleaned.full_text)

        # Step 4: Save output
        domain_dir = PROCESSED_DIR / target_domain
        domain_dir.mkdir(parents=True, exist_ok=True)
        txt_path = domain_dir / f"{pdf.stem}.txt"
        json_path = domain_dir / f"{pdf.stem}.articles.json"

        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(normalized)

        if progress_callback:
            progress_callback(
                f"💾 Saved normalized text ({len(normalized):,} chars)")

        # Step 5: Parse structure → JSON
        law_name = infer_law_name(pdf.filename)
        articles = parse_normalized_text_to_json(
            normalized,
            domain=target_domain,
            law_name=law_name,
            output_path=str(json_path),
        )

        duration = time.time() - start

        if progress_callback:
            progress_callback(
                f"✅ Done — {len(articles)} articles extracted "
                f"({format_time(duration)})")

        return ProcessingResult(
            pdf=pdf, success=True, method=method,
            chars=total_raw_chars, articles=len(articles),
            duration=duration,
        )

    except Exception as e:
        duration = time.time() - start
        error_msg = f"{type(e).__name__}: {e}"
        if progress_callback:
            progress_callback(f"❌ ERROR: {error_msg}")
        return ProcessingResult(
            pdf=pdf, success=False, error=error_msg, duration=duration,
        )


# ===================================================================
# SCREENS
# ===================================================================

# -------------------------------------------------------------------
# Domain Selection Modal
# -------------------------------------------------------------------

class DomainSelectModal(ModalScreen[str | None]):
    """Modal for choosing a target domain folder (manual organisation)."""

    def __init__(self, pdf_name: str, auto_domain: str):
        super().__init__()
        self.pdf_name = pdf_name
        self.auto_domain = auto_domain

    def compose(self) -> ComposeResult:
        domains = [
            "civil", "commercial", "criminal", "traffic",
            "tax", "judicial", "violations",
        ]
        yield Container(
            Label(f"📄 {self.pdf_name}", classes="modal-title"),
            Label(f"Inferred domain: [bold]{self.auto_domain}[/]",
                  classes="modal-subtitle"),
            Label("Choose target folder:", classes="modal-prompt"),
            Select(
                [(d.capitalize(), d) for d in domains],
                prompt="Select domain...",
                value=self.auto_domain,
                id="domain-select",
            ),
            Horizontal(
                Button("Cancel", variant="error", id="btn-cancel"),
                Button("Confirm", variant="primary", id="btn-confirm"),
                classes="modal-buttons",
            ),
            id="modal-content",
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-cancel":
            self.dismiss(None)
        elif event.button.id == "btn-confirm":
            try:
                select = self.query_one("#domain-select", Select)
                self.dismiss(str(select.value))
            except Exception:
                self.dismiss(None)


# -------------------------------------------------------------------
# Processing Progress Modal
# -------------------------------------------------------------------

class ProcessingModal(ModalScreen[list[ProcessingResult]]):
    """Full-screen modal showing real-time processing progress."""

    def __init__(self, pdfs: list[PdfFile], manual_domain: str | None = None):
        super().__init__()
        self.pdfs = pdfs
        self.manual_domain = manual_domain
        self.results: list[ProcessingResult] = []
        self._cancelled = False

    def compose(self) -> ComposeResult:
        yield Container(
            Label("⚙️  Processing PDFs...", id="proc-title"),
            ProgressBar(total=len(self.pdfs), show_eta=True, id="proc-bar"),
            Label("", id="proc-file-label"),
            ScrollableContainer(
                RichLog(highlight=True, markup=True, id="proc-log",
                        max_lines=500),
            ),
            Button("Cancel", variant="error", id="btn-cancel-proc"),
            id="proc-container",
        )

    def on_mount(self) -> None:
        self.run_processing()

    @work(thread=True)
    def run_processing(self) -> None:
        """Process PDFs in a background thread, updating UI via callbacks."""
        import time

        def progress(msg: str):
            # Post to the asyncio event loop
            self.app.call_from_thread(self._append_log, msg)

        for i, pdf in enumerate(self.pdfs):
            if self._cancelled:
                break

            self.app.call_from_thread(self._update_progress, i, pdf)

            result = process_single_pdf(pdf, domain=self.manual_domain,
                                        progress_callback=progress)
            self.results.append(result)

            # Brief pause so the UI can breathe
            time.sleep(0.05)

        self.app.call_from_thread(self._processing_done)

    def _update_progress(self, idx: int, pdf: PdfFile) -> None:
        self.query_one("#proc-bar", ProgressBar).update(progress=idx)
        self.query_one("#proc-file-label", Label).update(
            f"[bold]{idx + 1}[/] / {len(self.pdfs)} — {pdf.filename}"
        )

    def _append_log(self, msg: str) -> None:
        try:
            log = self.query_one("#proc-log", RichLog)
            log.write(msg)
            log.scroll_end()
        except NoMatches:
            pass

    def _processing_done(self) -> None:
        self.query_one("#proc-bar", ProgressBar).update(
            progress=len(self.pdfs))
        self.query_one("#proc-file-label", Label).update(
            "✅ Processing complete!" if not self._cancelled
            else "⛔ Processing cancelled.")
        self.query_one("#btn-cancel-proc", Button).label = "Close"
        self.query_one("#btn-cancel-proc", Button).variant = "primary"

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-cancel-proc":
            if event.button.label == "Close":
                self.dismiss(self.results)
            else:
                self._cancelled = True
                self._append_log("⛔ Cancelling... (finishing current PDF)")


# -------------------------------------------------------------------
# Results Summary Modal
# -------------------------------------------------------------------

class ResultsModal(ModalScreen[None]):
    """Show a summary table of processing results."""

    def __init__(self, results: list[ProcessingResult]):
        super().__init__()
        self.results = results

    def compose(self) -> ComposeResult:
        yield Container(
            Label("📊 Processing Results", id="results-title"),
            DataTable(id="results-table"),
            Label("", id="results-summary"),
            Button("OK", variant="primary", id="btn-ok-results"),
            id="results-container",
        )

    def on_mount(self) -> None:
        table = self.query_one("#results-table", DataTable)
        table.add_columns("File", "Domain", "Articles",
                          "Chars", "Method", "Status")

        success_count = 0
        total_articles = 0
        total_chars = 0
        total_time = 0.0

        for r in self.results:
            status = "✅" if r.success else "❌"
            color = DOMAIN_COLORS.get(r.pdf.domain, "")
            domain_tag = f"[{color}]{r.pdf.domain}[/]" if color else r.pdf.domain
            table.add_row(
                r.pdf.stem[:35],
                domain_tag,
                str(r.articles) if r.success else "—",
                f"{r.chars:,}" if r.success else "—",
                r.method if r.success else "—",
                status,
            )
            if r.success:
                success_count += 1
                total_articles += r.articles
                total_chars += r.chars
            total_time += r.duration

        summary = (
            f"[bold]Success:[/] {success_count}/{len(self.results)}  "
            f"[bold]Total Articles:[/] {total_articles:,}  "
            f"[bold]Total Chars:[/] {total_chars:,}  "
            f"[bold]Total Time:[/] {format_time(total_time)}"
        )
        self.query_one("#results-summary", Label).update(summary)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-ok-results":
            self.dismiss(None)


# -------------------------------------------------------------------
# Main Screen
# -------------------------------------------------------------------

class MainScreen(Screen):
    """Main screen with PDF file list and controls."""

    CSS = """
    #main-container {
        height: 100%;
    }

    #top-bar {
        height: 3;
        dock: top;
        background: $surface;
        padding: 0 1;
    }

    #top-bar > Label {
        width: 1fr;
        text-style: bold;
    }

    #top-bar > #status-label {
        width: auto;
        text-style: italic;
        color: $text-muted;
    }

    #body {
        height: 1fr;
    }

    #left-panel {
        width: 2fr;
        border: solid $primary;
        padding: 0 1;
        height: 100%;
    }

    #left-panel > Label {
        text-style: bold;
        padding: 0 0 0 0;
    }

    #pdf-list {
        height: 1fr;
        margin: 0 0 0 0;
    }

    #right-panel {
        width: 3fr;
        border: solid $secondary;
        padding: 1;
        height: 100%;
    }

    #right-panel > Label {
        text-style: bold;
        padding: 0 0 0 0;
    }

    #info-area {
        height: auto;
        max-height: 10;
        margin: 0 0 1 0;
    }

    #info-area > Static {
        margin: 0 0 0 0;
    }

    #controls {
        height: auto;
        margin: 0 0 0 0;
    }

    #controls > Label {
        text-style: bold;
        margin: 1 0 0 0;
    }

    #org-mode-select {
        width: 100%;
        margin: 0 0 1 0;
    }

    #domain-select-container {
        height: auto;
        margin: 0 0 1 0;
    }

    #button-row {
        height: auto;
        margin: 0 0 0 0;
    }

    Button {
        margin: 0 1 0 0;
    }

    #action-log {
        height: 8;
        border: solid $border;
        margin: 1 0 0 0;
    }

    #action-log > Label {
        text-style: bold;
        padding: 0 0 0 0;
    }

    #log-output {
        height: 1fr;
    }

    /* Modal styling */
    #modal-content {
        width: 50;
        height: auto;
        padding: 2;
        border: thick $primary;
        background: $surface;
        margin: 5 8;
    }

    .modal-title {
        text-style: bold;
        text-align: center;
        padding: 0 0 1 0;
    }

    .modal-subtitle {
        text-align: center;
        padding: 0 0 1 0;
    }

    .modal-prompt {
        padding: 0 0 0 0;
    }

    .modal-buttons {
        height: auto;
        align: center middle;
        padding: 1 0 0 0;
    }

    #proc-container {
        width: 80;
        height: 80%;
        padding: 1;
        border: thick $secondary;
        background: $surface;
        margin: 1 4;
    }

    #proc-title {
        text-style: bold;
        text-align: center;
        padding: 0 0 1 0;
    }

    #proc-file-label {
        text-align: center;
        padding: 0 0 0 0;
    }

    #proc-log {
        height: 1fr;
        border: solid $border;
        margin: 1 0;
    }

    #btn-cancel-proc {
        width: 20;
        align: center middle;
    }

    #results-container {
        width: 80;
        height: auto;
        padding: 1;
        border: thick $primary;
        background: $surface;
        margin: 2 4;
    }

    #results-title {
        text-style: bold;
        text-align: center;
        padding: 0 0 1 0;
    }

    #results-table {
        height: auto;
        max-height: 20;
    }

    #results-summary {
        text-align: center;
        padding: 1 0;
        text-style: bold;
    }

    #btn-ok-results {
        width: 16;
        align: center middle;
    }

    /* ListView item styling */
    .pdf-item {
        padding: 0 1;
        height: 3;
    }

    .pdf-item > Label {
        padding: 0 0 0 0;
    }

    .pdf-item.selected {
        background: $accent 20%;
    }

    .pdf-filename {
        text-style: bold;
    }

    .pdf-meta {
        color: $text-muted;
    }

    #sel-counter {
        text-style: bold;
        color: $accent;
        padding: 0 0 0 0;
        height: 1;
    }
    """

    def __init__(self):
        super().__init__()
        self.pdfs: list[PdfFile] = []
        self.selected: set[int] = set()
        self._log_lines: list[str] = []

    def compose(self) -> ComposeResult:
        yield Container(
            Horizontal(
                Label("📚 Moroccan Legal RAG — Knowledge Base Manager",
                      id="title-label"),
                Label("", id="status-label"),
                id="top-bar",
            ),
            Horizontal(
                # Left panel — PDF list
                Vertical(
                    Label("📄 PDF Files in data/raw/"),
                    ListView(id="pdf-list"),
                    id="left-panel",
                ),
                # Right panel — controls + info
                Vertical(
                    Label("⚙️  Controls"),
                    Label("", id="sel-counter"),
                    ScrollableContainer(
                        Static("", id="info-area"),
                        Container(
                            Label("Process Options"),
                            Select(
                                [
                                    ("Auto-organize by domain", "auto"),
                                    ("Manual — choose domain", "manual"),
                                ],
                                prompt="Organisation mode...",
                                value="auto",
                                id="org-mode-select",
                            ),
                            Container(id="domain-select-container"),
                            Horizontal(
                                Button("🔄 Refresh List", id="btn-refresh",
                                       variant="default"),
                                Button("▶ Process Selected", id="btn-process",
                                       variant="primary"),
                                Button("▶▶ Process All", id="btn-process-all",
                                       variant="success"),
                                id="button-row",
                            ),
                            id="controls",
                        ),
                    ),
                    Container(
                        Label("📋 Activity Log"),
                        RichLog(highlight=True, markup=True,
                                id="log-output", max_lines=200),
                        id="action-log",
                    ),
                    id="right-panel",
                ),
                id="body",
            ),
            id="main-container",
        )

    def on_mount(self) -> None:
        self._refresh_pdf_list()

    # ------------------------------------------------------------------
    # PDF list management
    # ------------------------------------------------------------------

    def _refresh_pdf_list(self) -> None:
        """Scan data/raw/ for PDF files and rebuild the list."""
        pdf_files = sorted(RAW_DIR.glob("*.pdf"))
        self.pdfs = [PdfFile(p) for p in pdf_files]
        self.selected = set()
        self._rebuild_list_view()
        self._update_status()
        self._update_info()
        self._log(f"Found {len(self.pdfs)} PDF files in data/raw/")

    def _rebuild_list_view(self) -> None:
        """Rebuild the ListView from self.pdfs."""
        lv = self.query_one("#pdf-list", ListView)
        lv.clear()

        for idx, pdf in enumerate(self.pdfs):
            is_sel = idx in self.selected
            processed = pdf.has_output()
            articles = pdf.get_article_count()
            status = f"✅ {articles} arts" if processed else "⏳ Not processed"
            domain_color = DOMAIN_COLORS.get(pdf.domain, "")
            domain_tag = f"[{domain_color}]{pdf.domain}[/]" if domain_color else pdf.domain

            if is_sel:
                check = "[bold $accent]● SELECTED[/]"
            else:
                check = "[dim]○[/]"

            lv.append(
                ListItem(
                    Label(
                        f"{check}  {pdf.filename}",
                        classes="pdf-filename",
                    ),
                    Label(
                        f"        {pdf.size_label}  |  {domain_tag}  |  {status}",
                        classes="pdf-meta",
                    ),
                    classes="pdf-item selected" if is_sel else "pdf-item",
                )
            )

    def _update_status(self) -> None:
        total = len(self.pdfs)
        processed = sum(1 for p in self.pdfs if p.has_output())
        label = self.query_one("#status-label", Label)
        label.update(f"{processed}/{total} processed")

    def _update_info(self) -> None:
        """Update the info area with aggregate stats."""
        total = len(self.pdfs)
        processed_count = sum(1 for p in self.pdfs if p.has_output())
        total_articles = sum(p.get_article_count() for p in self.pdfs)
        selected_count = len(self.selected)

        info = self.query_one("#info-area", Static)
        info.update(
            f"[bold]Total PDFs:[/] {total}\n"
            f"[bold]Processed:[/] {processed_count}  "
            f"[bold]Total Articles:[/] {total_articles:,}\n"
            f"[bold]Output Dir:[/] data/processed/{{domain}}/"
        )

        sel_label = self.query_one("#sel-counter", Label)
        if selected_count:
            sel_label.update(
                f"[bold $accent]● {selected_count} PDF[/] selected"
                + ("" if selected_count == 1 else "s")
            )
        else:
            sel_label.update("[dim]Click items in the list below to select[/]")

    def _log(self, msg: str) -> None:
        """Append a message to the activity log."""
        try:
            log = self.query_one("#log-output", RichLog)
            log.write(msg)
            log.scroll_end()
        except NoMatches:
            pass

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Toggle selection when an item is clicked."""
        lv = self.query_one("#pdf-list", ListView)
        idx = lv.index
        if idx is None or idx < 0 or idx >= len(self.pdfs):
            return
        if idx in self.selected:
            self.selected.remove(idx)
        else:
            self.selected.add(idx)
        self._rebuild_list_view()
        self._update_info()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id

        if btn_id == "btn-refresh":
            self._refresh_pdf_list()

        elif btn_id == "btn-process":
            if not self.selected:
                self._log("[bold red]No PDFs selected![/] "
                          "Click items in the list to select them.")
                return
            selected_pdfs = [self.pdfs[i] for i in sorted(self.selected)]
            self._run_processing(selected_pdfs)

        elif btn_id == "btn-process-all":
            if not self.pdfs:
                self._log("[bold red]No PDFs found in data/raw/[/]")
                return
            self._run_processing(self.pdfs)

    # ------------------------------------------------------------------
    # Processing orchestration
    # ------------------------------------------------------------------

    def _run_processing(self, pdfs: list[PdfFile]) -> None:
        """Start processing — check org-mode, possibly show domain selector first."""
        try:
            org_mode = self.query_one("#org-mode-select", Select).value
        except Exception:
            org_mode = "auto"

        if org_mode == "auto":
            self._start_processing(pdfs, manual_domain=None)
        else:
            # Manual mode: ask which domain for the first PDF
            self._show_domain_selector(pdfs)

    def _show_domain_selector(self, pdfs: list[PdfFile]) -> None:
        """Show a domain selector modal before processing."""
        first = pdfs[0]

        def on_domain_selected(domain: str | None) -> None:
            if domain is None:
                self._log("[yellow]Processing cancelled by user[/]")
                return
            self._log(f"[green]Manual domain: {domain}[/]")
            self._start_processing(pdfs, manual_domain=domain)

        self.app.push_screen(
            DomainSelectModal(first.filename, first.domain),
            on_domain_selected,
        )

    def _start_processing(self, pdfs: list[PdfFile],
                          manual_domain: str | None) -> None:
        """Launch the processing modal."""
        self._log(f"Starting processing of [bold]{len(pdfs)}[/] PDF(s)...")

        def on_results(results: list[ProcessingResult] | None) -> None:
            if results is None:
                self._log("[yellow]Processing cancelled[/]")
                return
            self._on_processing_done(results)

        self.app.push_screen(
            ProcessingModal(pdfs, manual_domain=manual_domain),
            on_results,
        )

    def _on_processing_done(self, results: list[ProcessingResult]) -> None:
        """Handle completed processing results."""
        success_count = sum(1 for r in results if r.success)
        total_articles = sum(r.articles for r in results if r.success)
        self._log(
            f"[bold green]Processing complete:[/] "
            f"{success_count}/{len(results)} succeeded, "
            f"{total_articles} total articles"
        )

        # Refresh the list to show updated status
        self._rebuild_list_view()
        self._update_status()
        self._update_info()

        # Show results modal
        self.app.push_screen(ResultsModal(results))

    # ------------------------------------------------------------------
    # Key bindings
    # ------------------------------------------------------------------

    def key_a(self) -> None:
        """A: Select / deselect all."""
        if len(self.selected) == len(self.pdfs):
            self.selected.clear()
        else:
            self.selected = set(range(len(self.pdfs)))
        self._rebuild_list_view()
        self._update_info()
        self._log(f"Selected {len(self.selected)}/{len(self.pdfs)} PDFs")

    def key_r(self) -> None:
        """R: Refresh file list."""
        self._refresh_pdf_list()
        self._log("File list refreshed")

    def key_p(self) -> None:
        """P: Process selected PDFs."""
        btn = self.query_one("#btn-process", Button)
        if not btn.disabled:
            btn.press()

    def key_q(self) -> None:
        """Q: Quit."""
        self.app.exit()


# ===================================================================
# Application
# ===================================================================

class LegalKbManager(App):
    """Moroccan Legal RAG — Knowledge Base Manager TUI."""

    TITLE = "Moroccan Legal RAG | KB Manager"
    SUB_TITLE = "data/raw/ → data/processed/{domain}/{file}.txt + .json"

    CSS = """
    Screen {
        background: $surface;
    }
    """

    SCREENS = {
        "main": MainScreen,
    }

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("a", "select_all", "Toggle select all"),
        ("r", "refresh", "Refresh list"),
        ("p", "process", "Process selected"),
    ]

    def on_mount(self) -> None:
        self.push_screen("main")

    def action_select_all(self) -> None:
        try:
            screen = self.get_screen("main")
            screen.key_a()
        except Exception:
            pass

    def action_refresh(self) -> None:
        try:
            screen = self.get_screen("main")
            screen.key_r()
        except Exception:
            pass

    def action_process(self) -> None:
        try:
            screen = self.get_screen("main")
            screen.key_p()
        except Exception:
            pass


# ===================================================================
# Entry point
# ===================================================================

def main():
    app = LegalKbManager()
    app.run()


if __name__ == "__main__":
    main()
