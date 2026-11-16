"""FastAPI endpoints and production static-file serving for the React UI."""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

REPO_ROOT = Path(__file__).resolve().parents[1]
DOCS_ROOT = (REPO_ROOT / "docs").resolve()
FRONTEND_DIST = REPO_ROOT / "frontend" / "dist"
INDEX_FILE = FRONTEND_DIST / "index.html"

app = FastAPI(
    title="Fun Embedded Systems Docs API",
    docs_url=None,
    redoc_url=None,
    openapi_url="/api/openapi.json",
)


def _document_files() -> list[Path]:
    paths = []
    for path in DOCS_ROOT.rglob("*.md"):
        relative = path.relative_to(DOCS_ROOT)
        if any(part.startswith(".") for part in relative.parts):
            continue
        resolved = path.resolve()
        if resolved.is_file() and resolved.is_relative_to(DOCS_ROOT):
            paths.append(resolved)
    return sorted(paths, key=lambda item: item.relative_to(DOCS_ROOT).as_posix().casefold())


def _title_for(path: Path) -> str:
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        heading = line.strip()
        if heading.startswith("# "):
            return heading[2:].strip()
    return path.stem.replace("_", " ").replace("-", " ").title()


def _frontend_index() -> FileResponse:
    if not INDEX_FILE.is_file():
        raise HTTPException(
            status_code=503,
            detail="Frontend build is missing. From the repository root, run ./install.sh.",
        )
    return FileResponse(INDEX_FILE)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/documents")
def list_documents() -> list[dict[str, str]]:
    return [
        {
            "path": path.relative_to(DOCS_ROOT).as_posix(),
            "title": _title_for(path),
        }
        for path in _document_files()
    ]


@app.get("/api/documents/{document_path:path}")
def get_document(document_path: str) -> dict[str, str]:
    requested = (DOCS_ROOT / document_path).resolve()
    if (
        not requested.is_relative_to(DOCS_ROOT)
        or requested.suffix.lower() != ".md"
        or not requested.is_file()
        or any(part.startswith(".") for part in requested.relative_to(DOCS_ROOT).parts)
    ):
        raise HTTPException(status_code=404, detail="Markdown document not found")
    return {
        "path": requested.relative_to(DOCS_ROOT).as_posix(),
        "title": _title_for(requested),
        "content": requested.read_text(encoding="utf-8", errors="replace"),
    }


if (FRONTEND_DIST / "assets").is_dir():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")


@app.get("/{requested_path:path}", include_in_schema=False)
def frontend(requested_path: str) -> FileResponse:
    return _frontend_index()
