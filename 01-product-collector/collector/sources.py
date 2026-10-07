import json
from urllib.parse import urljoin, urlsplit
from bs4 import BeautifulSoup
from .models import Product, price_number


def parse_books(html, url):
    soup = BeautifulSoup(html, "html.parser")
    products, errors = [], []
    for card in soup.select("article.product_pod"):
        try:
            link = card.select_one("h3 a")
            products.append(
                Product(
                    name=link.get("title") or link.get_text(strip=True),
                    price=price_number(card.select_one(".price_color").get_text()),
                    currency="GBP",
                    url=urljoin(url, link["href"]),
                    availability=card.select_one(".availability").get_text(
                        " ", strip=True
                    ),
                    rating=" ".join(
                        card.select_one(".star-rating").get("class", [])[1:]
                    ),
                    source="Books to Scrape",
                )
            )
        except (AttributeError, KeyError, ValueError, TypeError) as error:
            errors.append(str(error))
    next_link = soup.select_one("li.next a")
    return products, urljoin(url, next_link["href"]) if next_link else None, errors


def parse_jsonld(html, url):
    """Separate adapter for public schema.org Product / ItemList pages."""
    products, errors = [], []

    def walk(obj):
        if isinstance(obj, list):
            for item in obj:
                walk(item)
        elif isinstance(obj, dict):
            kinds = obj.get("@type", [])
            if isinstance(kinds, str):
                kinds = [kinds]
            if "Product" in kinds:
                try:
                    offers = obj.get("offers", {})
                    if isinstance(offers, list):
                        offers = offers[0] if offers else {}
                    rating = obj.get("aggregateRating", {})
                    products.append(
                        Product(
                            str(obj["name"]),
                            price_number(offers.get("price", offers.get("lowPrice"))),
                            str(offers.get("priceCurrency", "")),
                            urljoin(url, str(obj.get("url", offers.get("url", url)))),
                            str(offers.get("availability", "")).split("/")[-1],
                            str(rating.get("ratingValue", "")),
                            urlsplit(url).hostname or "",
                        )
                    )
                except (KeyError, ValueError, TypeError, AttributeError) as error:
                    errors.append(str(error))
            for value in obj.values():
                if isinstance(value, (list, dict)):
                    walk(value)

    for script in BeautifulSoup(html, "html.parser").select(
        'script[type="application/ld+json"]'
    ):
        try:
            walk(json.loads(script.get_text()))
        except json.JSONDecodeError:
            errors.append("잘못된 JSON-LD 블록")
    return products, None, errors


def parse_page(html, url):
    return (
        parse_books(html, url)
        if urlsplit(url).hostname == "books.toscrape.com"
        else parse_jsonld(html, url)
    )
