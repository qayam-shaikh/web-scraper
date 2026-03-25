import re
from dataclasses import dataclass
import requests
from bs4 import BeautifulSoup

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
