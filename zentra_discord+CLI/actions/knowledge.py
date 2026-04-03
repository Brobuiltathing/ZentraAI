import json
import os
import re
from pathlib import Path
from datetime import datetime

from config import BASE_FOLDER
from logger import log
from ollama import ollama_raw_sync

KB_FOLDER = os.path.join(BASE_FOLDER, "_knowledge_base")
KB_INDEX_FILE = os.path.join(KB_FOLDER, "_index.json")

SUPPORTED_EXTENSIONS = {".txt", ".md", ".py", ".js", ".ts", ".json", ".yaml", ".yml",
                        ".toml", ".cfg", ".ini", ".html", ".css", ".csv", ".log",
                        ".sh", ".bat", ".ps1", ".env", ".xml", ".rst", ".tex"}


def _ensure_kb():
    Path(KB_FOLDER).mkdir(parents=True, exist_ok=True)


def _load_index() -> dict:
    _ensure_kb()
    if not os.path.exists(KB_INDEX_FILE):
        return {"documents": {}, "updated": ""}
    try:
        with open(KB_INDEX_FILE, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return {"documents": {}, "updated": ""}


def _save_index(index: dict):
    index["updated"] = datetime.now().isoformat()
    with open(KB_INDEX_FILE, "w", encoding="utf-8") as fh:
        json.dump(index, fh, indent=2, ensure_ascii=False)


def _extract_text(file_path: Path) -> str:
    try:
        return file_path.read_text(encoding="utf-8", errors="replace")[:10000]
    except Exception:
        return ""


def _summarize_document(content: str, filename: str) -> str:
    return ollama_raw_sync(
        "Summarize this document in 2-3 sentences. Include key topics, names, and important details. No preamble.",
        f"Filename: {filename}\n\n{content[:3000]}",
        max_tokens=100,
    )


def handle_kb_add(data: dict) -> str:
    source = (data.get("filename") or data.get("app") or "").strip()
    if not source:
        return "kb_add: provide a file or folder path."

    _ensure_kb()
    source_path = Path(source).expanduser()

    if not source_path.exists():
        from utils import resolve_any_path
        source_path = resolve_any_path(source)
        if not source_path.exists():
            return f"Path not found: `{source}`"

    index = _load_index()
    added = []

    files_to_index = []
    if source_path.is_file():
        files_to_index = [source_path]
    elif source_path.is_dir():
        for f in source_path.rglob("*"):
            if f.is_file() and f.suffix.lower() in SUPPORTED_EXTENSIONS:
                files_to_index.append(f)
        if not files_to_index:
            return f"No supported text files found in `{source_path}`"

    for fp in files_to_index[:50]:
        content = _extract_text(fp)
        if not content.strip():
            continue

        summary = _summarize_document(content, fp.name)
        key = str(fp.resolve())

        index["documents"][key] = {
            "name": fp.name,
            "path": key,
            "size": len(content),
            "summary": summary,
            "added": datetime.now().isoformat(),
        }
        added.append(fp.name)
        log.info(f"KB indexed: {fp.name}")

    _save_index(index)

    if not added:
        return "No files could be indexed."

    return f"Added {len(added)} document(s) to knowledge base:\n" + "\n".join(f"  {n}" for n in added)


def handle_kb_search(data: dict) -> str:
    query = (data.get("app") or data.get("reply") or "").strip()
    if not query:
        return "kb_search: provide a search query."

    index = _load_index()
    if not index["documents"]:
        return "Knowledge base is empty. Add documents with kb_add first."

    query_lower = query.lower()
    scored = []

    for key, doc in index["documents"].items():
        score = 0
        searchable = f"{doc['name']} {doc['summary']}".lower()

        for word in query_lower.split():
            if word in searchable:
                score += 1
            if word in doc["name"].lower():
                score += 2

        if score > 0:
            scored.append((score, doc))

    scored.sort(key=lambda x: x[0], reverse=True)
    top = scored[:5]

    if not top:
        relevant_docs = list(index["documents"].values())[:3]
        context = "\n\n".join(f"[{d['name']}]: {d['summary']}" for d in relevant_docs)
        answer = ollama_raw_sync(
            "Search the following document summaries for information relevant to the query. "
            "If nothing is relevant, say so.",
            f"Query: {query}\n\nDocuments:\n{context}",
            max_tokens=200,
        )
        return f"**KB Search:** {query}\n\n{answer}"

    lines = [f"**KB Search:** {query}\n"]
    context_parts = []

    for score, doc in top:
        lines.append(f"  **{doc['name']}** (relevance: {score})")
        lines.append(f"    {doc['summary'][:120]}")

        try:
            content = Path(doc["path"]).read_text(encoding="utf-8", errors="replace")[:2000]
            context_parts.append(f"[{doc['name']}]:\n{content}")
        except Exception:
            context_parts.append(f"[{doc['name']}]: {doc['summary']}")

    full_context = "\n\n".join(context_parts)
    answer = ollama_raw_sync(
        "Answer the user's question using ONLY the provided documents. Be concise and cite which document the info came from.",
        f"Question: {query}\n\nDocuments:\n{full_context}",
        max_tokens=300,
    )

    lines.append(f"\n**Answer:** {answer}")
    return "\n".join(lines)


def handle_kb_list(data: dict) -> str:
    index = _load_index()
    if not index["documents"]:
        return "Knowledge base is empty."

    lines = [f"**Knowledge Base** ({len(index['documents'])} documents)\n"]
    for key, doc in index["documents"].items():
        lines.append(f"  **{doc['name']}** ({doc['size']:,} chars)")
        lines.append(f"    {doc['summary'][:100]}")
    return "\n".join(lines)


def handle_kb_clear(data: dict) -> str:
    _ensure_kb()
    _save_index({"documents": {}, "updated": ""})
    return "Knowledge base cleared."
