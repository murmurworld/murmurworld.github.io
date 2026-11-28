"""Check the public dependencies of the stock atlas, without credentials or stored map data."""
import argparse
import gzip
import json
import math
import time
from html.parser import HTMLParser
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from mapbox_vector_tile import decode


SITE = "https://murmurworld.github.io"
TILEJSON = "https://tiles.openfreemap.org/planet"
CITIES = {"Austin": (30.269, -97.741), "Anchorage": (61.218, -149.895), "Honolulu": (21.307, -157.863)}


def fetch(url, *, cors=False):
    headers = {"User-Agent": "Murmurworld-Atlas-Check/1.0", "Accept-Encoding": "gzip"}
    if cors:
        headers["Origin"] = SITE
    for attempt in range(3):
        try:
            with urlopen(Request(url, headers=headers), timeout=20) as response:
                if cors and response.headers.get("Access-Control-Allow-Origin") not in ("*", SITE):
                    raise ValueError(f"Browser access from {SITE} is not allowed at {url}")
                body = response.read()
                return gzip.decompress(body) if body.startswith(b"\x1f\x8b") else body
        except (HTTPError, URLError, TimeoutError) as error:
            if isinstance(error, HTTPError) and error.code < 500 and error.code not in (408, 429):
                raise
            if attempt == 2:
                raise
            time.sleep(2 ** attempt)


def contains_line(geometry):
    coordinates = geometry["coordinates"]
    paths = coordinates if geometry["type"] == "MultiLineString" else [coordinates]
    return geometry["type"] in ("LineString", "MultiLineString") and any(
        len(path) >= 2 and any(point != path[0] for point in path[1:]) for path in paths
    )


def check_provider():
    metadata = json.loads(fetch(TILEJSON, cors=True))
    z = 14
    if metadata["maxzoom"] < z:
        raise ValueError(f"Street-scale tiles unavailable; maxzoom={metadata['maxzoom']}")
    template = metadata["tiles"][0]
    if urlsplit(template).scheme != "https" or urlsplit(template).hostname != "tiles.openfreemap.org":
        raise ValueError(f"Unrecognized tile provider in {TILEJSON}")
    for city, (lat, lon) in CITIES.items():
        n = 2 ** z
        x = math.floor((lon + 180) / 360 * n)
        y = math.floor((1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * n)
        layers = decode(fetch(template.format(z=z, x=x, y=y), cors=True))
        roads = [f for f in layers["transportation"]["features"] if contains_line(f["geometry"])]
        names = set()
        for feature in layers["transportation_name"]["features"]:
            name = feature["properties"].get("name", "")
            if any(char.isalpha() for char in name) and contains_line(feature["geometry"]):
                names.add(name)
        if len(roads) < 8 or len(names) < 3:
            raise ValueError(f"{city}: expected street geometry and names, found {len(roads)} lines and {len(names)} names")
        print(f"{city}: {len(roads)} transport lines, {len(names)} names. {', '.join(sorted(names)[:4])}")


class MapMarkup(HTMLParser):
    def __init__(self):
        super().__init__()
        self.has_layer = False
        self.credits = set()
        self.language = ""

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "g" and "data-street-layer" in attrs:
            self.has_layer = True
        if tag == "html":
            self.language = attrs.get("lang", "")
        if tag == "a":
            url = urlsplit(attrs.get("href", ""))
            host = (url.hostname or "").removeprefix("www.")
            if host in ("openfreemap.org", "openmaptiles.org") or (host == "openstreetmap.org" and url.path.rstrip("/") == "/copyright"):
                self.credits.add(host)


def check_pages():
    for language, path in (("ko", "/stocks/"), ("en", "/en/stocks/")):
        page = MapMarkup()
        page.feed(fetch(SITE + path).decode("utf-8"))
        if not (page.has_layer and len(page.credits) == 3 and page.language.split("-")[0] == language):
            raise ValueError(f"{path}: missing vector layer, map attribution, or the expected language; credits found: {page.credits}")
        print(f"{path}: public stock atlas and map attribution found ({page.language})")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--site-only", action="store_true", help="Check both deployed language pages")
    if parser.parse_args().site_only:
        check_pages()
    else:
        check_provider()
