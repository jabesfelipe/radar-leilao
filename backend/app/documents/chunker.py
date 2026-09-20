from dataclasses import dataclass

@dataclass
class Chunk:
    index: int
    content: str
    metadata: dict


def chunk_markdown(markdown: str, metadata: dict | None = None) -> list[Chunk]:
    base = metadata or {}
    try:
        from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter
        headers = MarkdownHeaderTextSplitter(headers_to_split_on=[("#", "section"), ("##", "subsection")])
        sections = headers.split_text(markdown)
        splitter = RecursiveCharacterTextSplitter(chunk_size=1200, chunk_overlap=160)
        docs = splitter.split_documents(sections)
        return [Chunk(i, doc.page_content, {**base, **doc.metadata}) for i, doc in enumerate(docs)]
    except ImportError:
        parts = [markdown[i:i + 1200] for i in range(0, len(markdown), 1040)]
        return [Chunk(i, part, base.copy()) for i, part in enumerate(parts)]
