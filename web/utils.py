import requests
from bs4 import BeautifulSoup
import json


def get_ld_json(url: str) -> dict:
    parser = "html.parser"
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:107.0) Gecko/20100101 Firefox/107.0"
    }
    req = requests.get(url, headers=headers)
    soup = BeautifulSoup(req.text, parser)
    return json.loads(
        "".join(soup.find("script", {"type": "application/ld+json"}).contents)
    )
