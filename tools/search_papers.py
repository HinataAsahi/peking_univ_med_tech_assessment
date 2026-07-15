"""Tool: 搜索并下载 ECS 领域论文"""

import os
import time
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
from pathlib import Path
from pydantic import BaseModel, Field


# ── Data Models ────────────────────────────────────────────────

class PaperSearchResult(BaseModel):
    pmid: str = ""
    title: str = ""
    authors: list[str] = []
    journal: str = ""
    year: int = 0
    doi: str = ""
    abstract: str = ""
    has_pdf: bool = False
    pdf_url: str = ""
    is_open_access: bool = False


class SearchResults(BaseModel):
    query: str
    total_hits: int = 0
    papers: list[PaperSearchResult] = []
    downloaded: list[str] = []  # 已下载的文件路径


# ── PubMed E-utilities ─────────────────────────────────────────

PUBMED_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
EUROPEPMC_BASE = "https://www.ebi.ac.uk/europepmc/webservices/rest"


def search_pubmed(
    query: str,
    max_results: int = 10,
    email: str = "student@example.com",
    years: str = "2023:2026",
) -> SearchResults:
    """搜索 PubMed 并返回论文元数据。

    Args:
        query: PubMed 查询表达式
        max_results: 最大返回数（默认 10）
        email: NCBI 要求的标识邮箱
        years: 年份范围 "2023:2026"

    Returns:
        SearchResults: 包含论文元数据列表
    """
    # 添加年份过滤
    full_query = f"({query}) AND ({years}[dp])"

    results = SearchResults(query=full_query)

    # Step 1: ESearch — 获取 PMID 列表
    try:
        search_url = (
            f"{PUBMED_BASE}/esearch.fcgi"
            f"?db=pubmed&term={urllib.request.quote(full_query)}"
            f"&retmax={max_results}&retmode=xml"
            f"&sort=relevance&email={email}"
        )
        resp = urllib.request.urlopen(search_url, timeout=10)
        search_xml = resp.read().decode()
        root = ET.fromstring(search_xml)
        pmids = [e.text for e in root.findall(".//Id") if e.text]
        results.total_hits = int(root.findtext(".//Count", "0"))
    except Exception as e:
        results.papers = []
        return results

    if not pmids:
        return results

    # Step 2: EFetch — 获取论文详情
    try:
        fetch_url = (
            f"{PUBMED_BASE}/efetch.fcgi"
            f"?db=pubmed&id={','.join(pmids)}"
            f"&retmode=xml&email={email}"
        )
        resp = urllib.request.urlopen(fetch_url, timeout=15)
        fetch_xml = resp.read().decode()
        root = ET.fromstring(fetch_xml)
    except Exception:
        return results

    # Step 3: 解析论文信息
    for article in root.findall(".//PubmedArticle"):
        paper = _parse_pubmed_article(article)
        results.papers.append(paper)

    return results


def _parse_pubmed_article(article: ET.Element) -> PaperSearchResult:
    """解析单个 PubMed Article XML 元素"""
    medline = article.find(".//MedlineCitation")
    article_elem = medline.find(".//Article") if medline is not None else None

    title = ""
    if article_elem is not None:
        title_el = article_elem.find(".//ArticleTitle")
        if title_el is not None and title_el.text:
            title = title_el.text

    authors = []
    if article_elem is not None:
        for author in article_elem.findall(".//Author"):
            last = author.findtext("LastName", "")
            fore = author.findtext("ForeName", "")
            if last:
                authors.append(f"{last} {fore}".strip())

    journal = ""
    if article_elem is not None:
        journal_el = article_elem.find(".//Journal/Title")
        if journal_el is not None and journal_el.text:
            journal = journal_el.text

    year = 0
    if article_elem is not None:
        year_el = article_elem.find(".//PubDate/Year")
        if year_el is not None and year_el.text:
            try:
                year = int(year_el.text)
            except ValueError:
                pass

    # DOI
    doi = ""
    for eid in article.findall(".//ArticleId"):
        if eid.get("IdType") == "doi" and eid.text:
            doi = eid.text

    # Abstract
    abstract = ""
    if article_elem is not None:
        for ab in article_elem.findall(".//Abstract/AbstractText"):
            label = ab.get("Label", "")
            text = ab.text or ""
            abstract += f"{label}: {text}\n" if label else f"{text}\n"

    pmid_el = medline.find(".//PMID") if medline is not None else None
    pmid = pmid_el.text if pmid_el is not None and pmid_el.text else ""

    return PaperSearchResult(
        pmid=pmid,
        title=title,
        authors=authors,
        journal=journal,
        year=year,
        doi=doi,
        abstract=abstract.strip(),
    )


def check_open_access(doi: str) -> dict:
    """检查论文是否可开放获取（通过 Unpaywall API）。

    Returns:
        dict with keys: is_oa, pdf_url, oa_status
    """
    if not doi:
        return {"is_oa": False, "pdf_url": "", "oa_status": "unknown"}

    try:
        url = f"https://api.unpaywall.org/v2/{doi}?email=student@example.com"
        import json
        resp = urllib.request.urlopen(url, timeout=10)
        data = json.loads(resp.read().decode())

        best = data.get("best_oa_location") or {}
        return {
            "is_oa": data.get("is_oa", False),
            "pdf_url": best.get("url_for_pdf", ""),
            "oa_status": data.get("oa_status", "closed"),
        }
    except Exception:
        return {"is_oa": False, "pdf_url": "", "oa_status": "error"}


def download_pdf(pdf_url: str, output_dir: str, filename: str) -> str:
    """下载 PDF 文件到指定目录。

    Returns:
        下载后的文件路径，失败返回空字符串
    """
    if not pdf_url:
        return ""

    out_path = Path(output_dir) / filename
    out_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        req = urllib.request.Request(
            pdf_url,
            headers={"User-Agent": "ECS-Paper-to-ARM/1.0 (mailto:student@example.com)"}
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = resp.read()
        with open(out_path, "wb") as f:
            f.write(data)
        return str(out_path)
    except Exception:
        return ""


# ── 预置 ECS 搜索查询 ──────────────────────────────────────────

ECS_QUERIES = {
    "review": (
        '"extracellular space"[Title/Abstract] AND "brain"[Title/Abstract] '
        'AND ("volume fraction" OR "tortuosity" OR "diffusion")'
    ),
    "method_iontophoresis": (
        '"extracellular space"[Title/Abstract] AND "brain"[Title/Abstract] '
        'AND ("iontophoresis" OR "TMA" OR "diffusion measurement" OR '
        '"integrative optical imaging")'
    ),
    "method_imaging": (
        '"brain extracellular space"[Title/Abstract] AND '
        '("imaging" OR "microscopy" OR "super-resolution" OR "tracer")'
    ),
    "disease_ischemia": (
        '"extracellular space"[Title/Abstract] AND "brain"[Title/Abstract] '
        'AND ("ischemia" OR "edema" OR "stroke" OR "spreading depression")'
    ),
    "clearance_glymphatic": (
        '("glymphatic"[Title/Abstract] OR "perivascular transport"[Title/Abstract] '
        'OR "brain clearance"[Title/Abstract])'
    ),
}


def search_and_download_ecs_papers(
    output_dir: str = "papers",
    max_per_query: int = 3,
    email: str = "student@example.com",
    auto_download: bool = True,
) -> SearchResults:
    """搜索并下载 ECS 领域 5 类论文（每个类别 max_per_query 篇）。

    这是面向 Agent 的整合工具——一次调用完成搜索 + OA 检查 + 下载。

    Args:
        output_dir: PDF 下载目录
        max_per_query: 每个搜索类别的最大论文数
        email: NCBI 要求的联系邮箱
        auto_download: 是否自动下载 OA PDF

    Returns:
        SearchResults: 包含所有论文和下载路径
    """
    all_papers: list[PaperSearchResult] = []
    downloaded: list[str] = []

    for category, query in ECS_QUERIES.items():
        # 搜索
        results = search_pubmed(query, max_results=max_per_query, email=email)
        time.sleep(0.5)  # NCBI rate limit

        for paper in results.papers:
            if not paper.doi:
                continue

            # 检查 OA
            oa = check_open_access(paper.doi)
            paper.is_open_access = oa["is_oa"]
            paper.has_pdf = bool(oa.get("pdf_url"))
            paper.pdf_url = oa.get("pdf_url", "")
            all_papers.append(paper)

            # 下载
            if auto_download and paper.pdf_url:
                safe_title = paper.title[:80].replace("/", "_").replace(":", "_")
                fname = f"{category}_{paper.doi.replace('/', '_')}_{safe_title}.pdf"
                path = download_pdf(paper.pdf_url, output_dir, fname)
                if path:
                    downloaded.append(path)
                time.sleep(0.3)

    return SearchResults(
        query="ECS 5-category automated search",
        total_hits=len(all_papers),
        papers=all_papers,
        downloaded=downloaded,
    )
