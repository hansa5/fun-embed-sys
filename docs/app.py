"""Browse Markdown documentation under this directory with Streamlit."""
from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import quote, unquote, urlsplit

import streamlit as st

DOCS_ROOT = Path(__file__).resolve().parent


def discover_documents() -> dict[str, Path]:
    """Return Markdown files beneath docs, keyed by their relative POSIX path."""
    root = DOCS_ROOT.resolve()
    documents: dict[str, Path] = {}
    for path in root.rglob("*.md"):
        relative = path.relative_to(root)
        if any(part.startswith(".") for part in relative.parts):
            continue
        resolved = path.resolve()
        if not resolved.is_file() or not resolved.is_relative_to(root):
            continue
        documents[relative.as_posix()] = resolved
    return dict(sorted(documents.items(), key=lambda item: item[0].casefold()))


def rewrite_markdown_links(markdown: str, current_file: Path) -> str:
    """Route relative links to other Markdown docs back through this app."""
    root = DOCS_ROOT.resolve()

    def replace_link(match: re.Match[str]) -> str:
        label, destination = match.group(1), match.group(2).strip()
        parts = urlsplit(destination)
        if parts.scheme or parts.netloc or not parts.path.lower().endswith(".md"):
            return match.group(0)
        target = (current_file.parent / unquote(parts.path)).resolve()
        if not target.is_relative_to(root) or not target.is_file():
            return match.group(0)
        relative = target.relative_to(root).as_posix()
        query = quote(relative, safe="/")
        anchor = f"#{quote(unquote(parts.fragment), safe='-._~')}" if parts.fragment else ""
        return f"[{label}](?doc={query}{anchor})"

    # Images use ![...](...), so skip a match immediately preceded by '!'.
    return re.sub(r"(?<!!)\[([^\]]+)\]\(([^)]+)\)", replace_link, markdown)


def sync_query_from_selection() -> None:
    selected = st.session_state["selected_document"]
    st.query_params["doc"] = selected
    st.session_state["last_query_document"] = selected


st.set_page_config(page_title="Project Documentation", page_icon="📚", layout="wide")
st.title("Project Documentation")

documents = discover_documents()
if not documents:
    st.info("No Markdown files found under the docs directory yet.")
    st.stop()

requested = st.query_params.get("doc", "")
if requested in documents and requested != st.session_state.get("last_query_document"):
    st.session_state["selected_document"] = requested
    st.session_state["last_query_document"] = requested
if st.session_state.get("selected_document") not in documents:
    st.session_state["selected_document"] = next(iter(documents))

st.sidebar.header("Documentation")
filter_text = st.sidebar.text_input("Filter files", placeholder="e.g. media or setup")
options = [name for name in documents if filter_text.casefold() in name.casefold()]
if not options:
    st.sidebar.info("No matching Markdown files.")
    options = list(documents)
if st.session_state["selected_document"] not in options:
    st.session_state["selected_document"] = options[0]
st.sidebar.selectbox(
    "Choose a file",
    options,
    key="selected_document",
    on_change=sync_query_from_selection,
)

selected_path = documents[st.session_state["selected_document"]]
markdown = selected_path.read_text(encoding="utf-8", errors="replace")
st.caption(f"docs/{st.session_state['selected_document']}")
st.markdown(rewrite_markdown_links(markdown, selected_path), unsafe_allow_html=False)
