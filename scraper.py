import re
from dataclasses import dataclass
import requests
from bs4 import BeautifulSoup
from typing import Optional, Any, List, Tuple
from datetime import datetime
import json

USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64; rv:147.0) Gecko/20100101 Firefox/147.0"

@dataclass
class article:
    url : str
    title : str
    byline : str
    published : str
    updated : str
    content : str

def _clean_whitespace(text: str) -> str:
    text = text.replace("\r\n","\n").replace("\r","\n")
    text = re.sub("[\t]+"," ",text)
    text = re.sub("\n{3,}", "\n\n",text)
    return text.strip()

def _format_iso_date(value: Optional[str]) -> str:
    if not value:
        return ""
    try:
        dt = datetime.fromisoformat(value.replace('Z','+00:00'))
        return dt.isoformat()
    except Exception:
        return value

def fetch_html(url: str, timeout: int = 20) -> str:
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
    }
    resp = requests.get(url, headers=headers, timeout=timeout)
    resp.raise_for_status()
    return resp.text

def parse_json_ld(soup: BeautifulSoup) -> Tuple[str, str, str, str]:

    scripts = soup.find_all("script", attrs={"type": "application/ld+json"})
    for script in scripts:
        raw = script.string or script.get_text(strip=True)
        if not raw:
            continue

        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            continue

        candidates: List[dict[str, Any]] = []
        if isinstance(data, dict):
            candidates = [data]
        elif isinstance(data, list):
            candidates = [x for x in data if isinstance(x, dict)]

        for obj in candidates:

            t = str(obj.get("@type", "")).lower()
            if "article" not in t:
                continue

            title = obj.get("headline") or obj.get("name") or ""
            content = obj.get("articleBody") or ""
            published = obj.get("datePublished") or ""
            byline = ""

            author = obj.get("author")
            if isinstance(author, dict):
                byline = author.get("name", "") or ""
            elif isinstance(author, list):
                names = []
                for a in author:
                    if isinstance(a, dict) and a.get("name"):
                        names.append(str(a["name"]))
                    elif isinstance(a, str):
                        names.append(a)
                byline= ", ".join(names)

            if title or content:
                return (
                    str(title).strip(),
                    str(byline).strip(),
                    _format_iso_date(str(published).strip()) if published else "",
                    _clean_whitespace(str(content)) if content else "",

                )
        
    return "", "", "", ""

def parse_next_data(soup: BeautifulSoup) -> Tuple[str,str,str,str]:
    """
    Fallback: parse __NEXT_DATA__ if json ld fails
    """
    node = soup.find('script',id='__NEXT_DATA__')
    if not node:
        return "","","",""
    raw = node.string or node.get_text(strip=True)
    if not raw:
        return "","","",""
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return "","","",""
    
    def walk(obj: Any):
        if isinstance(obj,dict):
            yield obj
            for v in obj.values():
                yield from walk(v)
        elif isinstance(obj,list):
            for item in obj:
                yield from walk(item)
        
    title = byline = published = content = ""
    for d in walk(data):
        if not title and isinstance(d.get('headline'),str):
            title = d["headline"]
        if not byline and isinstance(d.get('byline'),str):
            byline = d['byline']
        if not byline and isinstance(d.get('bylines'),str):
            parts = []
            for b in d['bylines']:
                if isinstance(b,dict) and isinstance(b.get('byline'),str):
                    parts.append(b['byline'])
            if parts:
                byline = " /".join(parts)
        
        if not published and isinstance(d.get('firstPublished'),str):
            published = d['firstPublished']
        if not published and isinstance(d.get('pubDate'),str):
            published = d['pubDate']
        if not content and isinstance(d.get('articleBody'),str):
            content = d['articleBody']
        if not content and isinstance(d.get('body'), str) and len(d['body'])>200:
            content = d['body']

        if title and published and content:
            break
    
    return (
        title.strip(),
        byline.strip(),
        _format_iso_date(published.strip()) if published else "",
        _clean_whitespace(content.strip()) if content else "",
    )

def parse_updated_date(soup: BeautifulSoup)->str:
    """
    NYT often includes updated time in meta tags or time elements.
    We'll try a few common options.
    """

    for key in ["article:modified_time", "nyt:ptime", "parsely-pub-date"]:
        tag = soup.find('meta', attrs={'property':key}) or soup.find('meta', attrs={'name':key})
        if tag and tag.get('content'):
            return _format_iso_date(tag['content'].strip())
    
    # fallback 1
    time_tag = soup.find('time', attrs={"datetime":True})
    if time_tag and time_tag.get('datetime'):
        return _format_iso_date(time_tag['datetime'].strip())
    
    # fallback 2
    return ""

def parse_html_article_body(soup: BeautifulSoup)->str:
    """
    Last resort: find paragraphs in the visible article body.
    NYT commonly uses section[name="articleBody"].    
    """
    body_section = soup.find('section', attrs={'name':'articleBody'})
    if not body_section:
        body_section = soup.find('article') or soup

    junk_phrases = [
    "We are having trouble retrieving the article content",
    "Please enable JavaScript in your browser settings",
    "Thank you for your patience while we verify access",
    "Already a subscriber? Log in",
    "Want all of The Times? Subscribe",
    ]

    paragraphs = []
    for p in body_section.find_all("p"):
        text = p.get_text(" ", strip=True)

        if not text:
            continue

        if any(phrase in text for phrase in junk_phrases):
            continue
        paragraphs.append(text)

    cleaned = []
    seen = set()
    for para in paragraphs:
        key = para.lower()
        if key in seen:
            continue
        seen.add(key)
        cleaned.append(para)

    return _clean_whitespace("\n\n".join(cleaned))
