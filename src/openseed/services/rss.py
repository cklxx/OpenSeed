"""RSS feed discovery — fetch papers from RSS/Atom feeds."""

from __future__ import annotations

import logging
import re
import xml.etree.ElementTree as ET

import httpx

from openseed.models.paper import Author, Paper

_log = logging.getLogger(__name__)
_ATOM_NS = "{http://www.w3.org/2005/Atom}"
_ARXIV_ID_RE = re.compile(r"(\d{4}\.\d{4,5})")


def _parse_atom_entry(entry: ET.Element, ns: str) -> Paper | None:
    """Parse an Atom feed entry into a Paper."""
    title = (entry.findtext(f"{ns}title") or "").strip().replace("\n", " ")
    if not title:
        return None
    abstract = (entry.findtext(f"{ns}summary") or "").strip()
    link = ""
    for link_el in entry.findall(f"{ns}link"):
        href = link_el.get("href", "")
        if "abs" in href or link_el.get("rel") == "alternate":
            link = href
            break
    arxiv_id = None
    entry_id = entry.findtext(f"{ns}id") or link
    match = _ARXIV_ID_RE.search(entry_id)
    if match:
        arxiv_id = match.group(1)
    authors = []
    for author_el in entry.findall(f"{ns}author"):
        name = (author_el.findtext(f"{ns}name") or "").strip()
        if name:
            authors.append(Author(name=name))
    return Paper(
        title=title,
        authors=authors,
        abstract=abstract,
        arxiv_id=arxiv_id,
        url=link or None,
    )


def _parse_rss_item(item: ET.Element) -> Paper | None:
    """Parse an RSS 2.0 item into a Paper."""
    title = (item.findtext("title") or "").strip()
    if not title:
        return None
    abstract = (item.findtext("description") or "").strip()
    link = (item.findtext("link") or "").strip()
    arxiv_id = None
    if match := _ARXIV_ID_RE.search(link):
        arxiv_id = match.group(1)
    return Paper(title=title, abstract=abstract, arxiv_id=arxiv_id, url=link or None)


def fetch_feed(url: str, max_items: int = 50) -> list[Paper]:
    """Fetch and parse an RSS or Atom feed, returning Paper objects."""
    try:
        with httpx.Client(timeout=30, follow_redirects=True) as client:
            resp = client.get(url)
            resp.raise_for_status()
    except (httpx.HTTPError, httpx.TimeoutException) as exc:
        _log.warning("Feed fetch failed for %s: %s", url, exc)
        return []
    try:
        root = ET.fromstring(resp.text)
    except ET.ParseError:
        _log.warning("Failed to parse feed XML from %s", url)
        return []
    papers: list[Paper] = []
    if root.tag == f"{_ATOM_NS}feed" or root.find(f"{_ATOM_NS}entry") is not None:
        for entry in root.findall(f"{_ATOM_NS}entry")[:max_items]:
            if p := _parse_atom_entry(entry, _ATOM_NS):
                papers.append(p)
    else:
        for item in root.iter("item"):
            if len(papers) >= max_items:
                break
            if p := _parse_rss_item(item):
                papers.append(p)
    return papers
