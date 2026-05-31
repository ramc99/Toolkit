# Change Log

All notable changes to this project will be documented in this file.

## [2026-05-27] Bug-fix & UI overhaul

### Fixed
- `merge_csv_route` never returned the merged file to the client (missing `return send_file()`).
- `edit_pdf_text` in `tasks/editor.py` was a plain function; route called `.apply()` on it → `AttributeError`.
- All task functions used `@shared_task(bind=True)` / `self.retry()` but Celery is not in `requirements.txt` — fallback decorator was broken for direct calls. Tasks are now plain Python functions.
- Dead code after `return diff` in `pdf_toolkit/compare()` route removed.
- `/pdf/` index route was missing — navigation link returned 404.
- Unimplemented conversion targets (`pptx`, `word_to_pdf`, etc.) now return 501 Not Implemented instead of 400.
- `compare()` now renders a template with the result instead of returning raw text.

### Changed
- Full frontend redesign: Tailwind CSS Play CDN added to `base.html`; all page templates rebuilt with consistent card layout, breadcrumb nav, dark-mode support.
- `pdf_home.html` converted from standalone HTML to a `base.html` child template.
- `index.html` restructured: PDF tool cards now in a proper responsive grid; orphaned `</div>` removed; card-icon CSS classes defined.
- `base.html` header/nav rebuilt — logo, nav links, and theme toggle properly spaced.
- `coming_soon.html` now has a centred illustration and a Back button.

### Added
- `AGENTS.md` — architecture reference and runbook.
- `CLAUDE.md` — pointer to `AGENTS.md` per engineering standards.

## [2026-05-26] Feature expansion

- Added `pdf_toolkit` blueprint with conversion, editor, OCR, security, AI, compare and organisation routes.
- Added Celery infrastructure (`celery_app.py`, Celery config in `config.py`) for future async task support.
- Added conversion tasks: `pdf_to_excel`, `pdf_to_csv`, `pdf_to_image`, `image_to_pdf`.
- Added OCR tasks using pytesseract and ocrmypdf.
- Added PDF security tasks using PyPDF2.
- Added Ollama AI chat task.

## [2026-05-26] Initial release

- Core CSV split and merge features.
- Basic UI with cards for each tool.
- Blueprint registration for PDF toolkit modules.
