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

