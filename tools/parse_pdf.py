"""Tool 1: PDF → 结构化文本（PyMuPDF）"""

import fitz
from schemas.pipeline import ParsedPaper, Page, TextBlock


def parse_pdf(file_path: str) -> ParsedPaper:
    """解析 PDF 论文，提取带页码标注的结构化文本。

    Args:
        file_path: PDF 文件的绝对路径

    Returns:
        ParsedPaper: 包含 pages（文本 + 页码）和 metadata

    Raises:
        ValueError: PDF 损坏或无文本层
    """
    try:
        doc = fitz.open(file_path)
    except Exception as e:
        raise ValueError(f"PDF 无法打开 (corrupted_pdf): {e}")

    pages = []
    total_text = ""

    for i, page in enumerate(doc):
        blocks_raw = page.get_text("blocks")
        blocks = []
        page_text = ""

        for b in blocks_raw:
            block_type = "text"
            if b[6] == 1:
                block_type = "image"
            elif b[6] == 2:
                block_type = "table"

            text = b[4] if len(b) > 4 else ""

            if block_type == "text" and text.strip():
                page_text += text + "\n"

            blocks.append(TextBlock(
                text=text.strip(),
                bbox=(b[0], b[1], b[2], b[3]),
                block_type=block_type
            ))

        total_text += page_text
        pages.append(Page(number=i + 1, text=page_text.strip(), blocks=blocks))

    if not total_text.strip():
        raise ValueError("PDF 无文本层 (no_text_layer)，可能是扫描版。请提供含文字层的 PDF。")

    if len(pages) > 50:
        pages = pages[:50]

    metadata = doc.metadata or {}
    title = metadata.get("title", "")

    return ParsedPaper(
        title=title,
        pages=pages,
        metadata={
            "title": title,
            "author": metadata.get("author", ""),
            "subject": metadata.get("subject", ""),
            "page_count": len(pages),
        },
        raw_text="\n\n".join(f"[Page {p.number}]\n{p.text}" for p in pages)
    )
