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


# ── Europe PMC REST API ────────────────────────────────────────

def search_europepmc(
    query: str,
    max_results: int = 10,
    years: str = "2023:2025",
) -> SearchResults:
    """通过 Europe PMC REST API 搜索论文。

    Europe PMC 聚合 PubMed 摘要和全文，直接返回 OA PDF 链接，
    无需额外调用 Unpaywall。

    Args:
        query: 查询表达式
        max_results: 最大返回数
        years: 年份范围 "2023:2026"

    Returns:
        SearchResults: 含论文元数据和 PDF 链接
    """
    import json

    full_query = f"({query}) AND (FIRST_PDATE:[{years[:4]}-01-01 TO {years[5:]}-12-31]) AND (OPEN_ACCESS:Y)"
    results = SearchResults(query=full_query)

    try:
        url = (
            f"{EUROPEPMC_BASE}/search"
            f"?query={urllib.request.quote(full_query)}"
            f"&format=json&resultType=core"
            f"&pageSize={max_results}"
        )
        resp = urllib.request.urlopen(url, timeout=15)
        data = json.loads(resp.read().decode())
    except Exception:
        return results

    hits = data.get("resultList", {}).get("result", [])
    results.total_hits = data.get("hitCount", 0)

    for item in hits:
        doi = item.get("doi", "")
        pmid = item.get("pmid", "") or item.get("id", "")

        # Europe PMC 直接提供 OA PDF 链接（在 fullTextUrlList 中）
        pdf_url = ""
        has_pdf_val = item.get("hasPDF", "N")
        has_pdf = has_pdf_val == "Y" if isinstance(has_pdf_val, str) else bool(has_pdf_val)

        # fullTextUrlList 是 dict: {"fullTextUrl": [{...}, {...}]}
        full_text_wrapper = item.get("fullTextUrlList", {})
        if isinstance(full_text_wrapper, dict):
            full_text_list = full_text_wrapper.get("fullTextUrl", [])
        else:
            full_text_list = full_text_list if isinstance(full_text_list, list) else []

        # 从 fullTextUrlList 中找 PDF：site=Europe_PMC, style=pdf, avail=Open access
        for ft in full_text_list:
            if not isinstance(ft, dict):
                continue
            avail = ft.get("availability", "")
            if "open" not in avail.lower():
                continue
            if ft.get("documentStyle") == "pdf":
                pdf_url = ft.get("url", "")
                if pdf_url:
                    break
            # Fallback: HTML URL for PMC papers
            if ft.get("documentStyle") == "html" and "europepmc.org" in ft.get("url", ""):
                # 将 HTML URL 转为 PDF URL
                pdf_url = ft.get("url", "").replace("?page=1", "?pdf=render")
                if "pdf=render" not in pdf_url:
                    pdf_url = pdf_url.rstrip("/") + "?pdf=render"
                break

        abstract = item.get("abstractText", "")
        # 去掉 HTML 标签
        if abstract:
            import re
            abstract = re.sub(r"<[^>]+>", "", abstract)

        results.papers.append(PaperSearchResult(
            pmid=pmid,
            title=item.get("title", ""),
            authors=[s.strip() for s in item.get("authorString", "").split(",") if s.strip()],
            journal=item.get("journalTitle", ""),
            year=item.get("pubYear", 0),
            doi=doi,
            abstract=abstract,
            has_pdf=has_pdf,
            pdf_url=pdf_url,
            is_open_access=(item.get("isOpenAccess", "N") == "Y"),
        ))

    return results


# ── PubMed XML 解析 ────────────────────────────────────────────
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
    """直接下载 PDF（URL 来自 Europe PMC 元数据的 fullTextUrlList）。

    不转换 URL——直接用元数据提供的链接下载。
    失败返回空字符串。
    """
    if not pdf_url:
        return ""

    out_path = Path(output_dir) / filename
    out_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        req = urllib.request.Request(
            pdf_url,
            headers={"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"}
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = resp.read()

        # 验证是 PDF 而非 HTML
        if data[:4] != b"%PDF":
            return ""

        with open(out_path, "wb") as f:
            f.write(data)
        return str(out_path)
    except Exception:
        return ""


def download_pdf_from_doi(doi: str, output_dir: str, filename: str) -> str:
    """通过 DOI 从出版商网站查找并下载 PDF。

    流程：DOI → 出版商页面 → 提取 PDF 链接或尝试常见 PDF URL 模式。

    Returns:
        下载后的文件路径，失败返回空字符串
    """
    if not doi:
        return ""

    out_path = Path(output_dir) / filename
    out_path.parent.mkdir(parents=True, exist_ok=True)
    headers = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"}

    # 策略 A：尝试常见出版商 PDF URL 模式
    pdf_patterns = [
        f"https://doi.org/{doi}",
        f"https://doi.org/{doi}?pdf=render",
        # Science Partner Journal / AAAS
        f"https://spj.science.org/doi/pdf/{doi}",
        # Nature / Springer
        f"https://www.nature.com/articles/{doi.split('/')[-1]}.pdf",
        # Frontiers
        f"https://www.frontiersin.org/articles/{doi}/pdf",
        # MDPI
        f"https://www.mdpi.com/*/*/{doi.split('/')[-1]}/pdf",
        # eLife
        f"https://elifesciences.org/articles/{doi.split('/')[-1]}.pdf",
        # PLOS
        f"https://journals.plos.org/plosone/article/file?id={doi}&type=printable",
        # BioMed Central / SpringerOpen
        f"https://link.springer.com/content/pdf/{doi}.pdf",
    ]

    for url in pdf_patterns:
        if "*" in url:
            continue  # 跳过含通配符的模式
        try:
            req = urllib.request.Request(url, headers=headers)
            resp = urllib.request.urlopen(req, timeout=15)
            data = resp.read()
            if data[:4] == b"%PDF":
                with open(out_path, "wb") as f:
                    f.write(data)
                return str(out_path)
        except Exception:
            continue

    # 策略 B：解析 DOI 重定向页面，提取 PDF 链接
    try:
        doi_url = f"https://doi.org/{doi}"
        req = urllib.request.Request(doi_url, headers=headers)
        resp = urllib.request.urlopen(req, timeout=15)
        page_html = resp.read().decode("utf-8", errors="ignore")

        # 在 HTML 中搜索 PDF 链接
        import re
        pdf_matches = re.findall(
            r'https?://[^\s"\'<>]+\.pdf[^\s"\'<>]*',
            page_html,
            re.IGNORECASE,
        )
        seen = set()
        for pdf_url in pdf_matches:
            if pdf_url in seen:
                continue
            seen.add(pdf_url)
            try:
                req2 = urllib.request.Request(pdf_url, headers=headers)
                resp2 = urllib.request.urlopen(req2, timeout=30)
                data2 = resp2.read()
                if data2[:4] == b"%PDF" and len(data2) > 10000:
                    with open(out_path, "wb") as f:
                        f.write(data2)
                    return str(out_path)
            except Exception:
                continue

        # 在 HTML 中搜索 meta citation_pdf_url
        meta_match = re.search(
            r'<meta[^>]+name="citation_pdf_url"[^>]+content="([^"]+)"',
            page_html,
        )
        if meta_match:
            pdf_url = meta_match.group(1)
            try:
                req3 = urllib.request.Request(pdf_url, headers=headers)
                resp3 = urllib.request.urlopen(req3, timeout=30)
                data3 = resp3.read()
                if data3[:4] == b"%PDF":
                    with open(out_path, "wb") as f:
                        f.write(data3)
                    return str(out_path)
            except Exception:
                pass

    except Exception:
        pass

    return ""


# ── 预置 ECS 搜索查询 ──────────────────────────────────────────

ECS_QUERIES = {
    "review": (
        'TITLE_ABS:"extracellular space" AND TITLE_ABS:"brain"'
        ' AND ("volume fraction" OR tortuosity OR diffusion)'
    ),
    "method_iontophoresis": (
        'TITLE_ABS:"extracellular space" AND ("iontophoresis" OR "TMA"'
        ' OR "diffusion measurement" OR "integrative optical imaging")'
    ),
    "method_imaging": (
        'TITLE_ABS:"brain extracellular space"'
        ' AND (imaging OR microscopy OR "super-resolution" OR tracer)'
    ),
    "disease_ischemia": (
        'TITLE_ABS:"extracellular space" AND "brain"'
        ' AND (ischemia OR edema OR stroke OR "spreading depression")'
    ),
    "clearance_glymphatic": (
        '(TITLE_ABS:glymphatic OR TITLE_ABS:"perivascular transport"'
        ' OR TITLE_ABS:"brain clearance")'
    ),
}


def search_and_download_ecs_papers(
    output_dir: str = "papers",
    max_per_query: int = 3,
    email: str = "student@example.com",
    auto_download: bool = True,
    backend: str = "europepmc",
) -> SearchResults:
    """搜索并下载 ECS 领域 5 类论文。

    这是面向 Agent 的整合工具——一次调用完成搜索 + OA 检查 + 下载。

    Args:
        output_dir: PDF 下载目录
        max_per_query: 每个搜索类别的最大论文数
        email: PubMed API 要求的联系邮箱（仅 pubmed backend）
        auto_download: 是否自动下载 OA PDF
        backend: "europepmc"（默认，推荐）或 "pubmed"

    Returns:
        SearchResults: 包含所有论文和下载路径
    """
    all_papers: list[PaperSearchResult] = []
    downloaded: list[str] = []

    for category, query in ECS_QUERIES.items():
        if backend == "europepmc":
            # Europe PMC：一步获取元数据 + OA PDF 链接
            results = search_europepmc(query, max_results=max_per_query)
        else:
            # PubMed + Unpaywall：两步
            results = search_pubmed(query, max_results=max_per_query, email=email)
            time.sleep(0.5)

        for paper in results.papers:
            if not paper.doi:
                continue

            if backend == "pubmed":
                oa = check_open_access(paper.doi)
                paper.is_open_access = oa["is_oa"]
                paper.has_pdf = bool(oa.get("pdf_url"))
                paper.pdf_url = oa.get("pdf_url", "")
                time.sleep(0.3)

            all_papers.append(paper)

            # 下载：先试 Europe PMC PDF 链接，再试 DOI → 出版商
            safe_title = paper.title[:80].replace("/", "_").replace(":", "_").replace("'", "")
            safe_doi = paper.doi.replace("/", "_").replace(".", "_") if paper.doi else "no_doi"
            fname = f"{category}_{safe_doi}_{safe_title}.pdf"

            if auto_download and paper.pdf_url:
                path = download_pdf(paper.pdf_url, output_dir, fname)
                if path:
                    downloaded.append(path)
                    time.sleep(0.3)
                    continue

            # Fallback: DOI → 出版商 PDF
            if auto_download and paper.doi:
                time.sleep(0.3)
                path = download_pdf_from_doi(paper.doi, output_dir, fname)
                if path:
                    downloaded.append(path)

        if backend == "pubmed":
            time.sleep(0.5)  # NCBI rate limit

    return SearchResults(
        query=f"ECS 5-category automated search (backend={backend})",
        total_hits=len(all_papers),
        papers=all_papers,
        downloaded=downloaded,
    )
