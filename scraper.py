from __future__ import annotations

import sys
import argparse
import re
from dataclasses import dataclass
import requests
from datetime import datetime
import json

from bs4 import BeautifulSoup
from typing import Optional, Any, List, Tuple
from playwright.sync_api import sync_playwright

# USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64; rv:147.0) Gecko/20100101 Firefox/147.0"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

@dataclass
class Article:
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

def fetch_html_playwright(url:str)->str:
    with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()

            page.goto(url, timeout=30000)
            page.wait_for_load_state('networkidle')

            html = page.content()

            browser.close()
            return html

def fetch_html(url: str, timeout:int=20)-> str:
    try:
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
    except requests.RequestException:
        print(f"Fallback to browser for url: {url}")
        return fetch_html_playwright(url)

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

def scrape_nyt(url: str)->Article:
    html = fetch_html(url)
    soup = BeautifulSoup(html,'html.parser')

    updated = parse_updated_date(soup)

    title, byline, published, content = parse_json_ld(soup)

    if not (title and content):
        t2, b2, p2, c2 = parse_next_data(soup)
        title = title or t2
        byline = byline or b2
        published = published or p2
        content = content or c2

    if not content:
        content = parse_html_article_body(soup)
    
    if not title:
        og = soup.find('meta', attrs={'property': 'og:title'})
        if og and og.get('content'):
            title = og['content'].strip()
        else:
            title = (soup.title.get_text(strip=True) if soup.title else "").strip()

    if not byline:
        byl = soup.find('meta', attrs={'name':'byl'})
        if byl and byl.get('content'):
            byline = byl['content'].strip()

    return Article(
        url=url,
        title=title or "(title not found)",
        byline=byline,
        published=published,
        updated=updated,
        content=content or "(content not found - possible paywall or page change structure)",
    )

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Scrape a New York Times article URL and print title + content."
    )
    parser.add_argument("url", help="NYT article URL to scrape")
    args = parser.parse_args()

    if "nytimes.com" not in args.url:
        print("Error: Please provide new york times url.", file=sys.stderr)
        return 1
    
    try:
        article = scrape_nyt(args.url)
    except requests.HTTPError as e:
        print(f"HTTP Error: {e}", file=sys.stderr)
        return 2
    except requests.RequestException as e:
        print(f"Request Failed: {e}", file=sys.stderr)
        return 2
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        return 3
    
    print(f"Title: {article.title}")
    if article.byline:
        print(f"Byline: {article.byline}")
    if article.published:
        print(f"Published: {article.published}")
    if article.updated:
        print(f"Updated: {article.updated}")
        print("\n"+"-"*80+"\n")
        print(article.content)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())