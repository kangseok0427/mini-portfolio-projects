from dataclasses import dataclass, asdict
from decimal import Decimal, InvalidOperation
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode
import re


@dataclass
class Product:
    name: str
    price: float
    currency: str
    url: str
    availability: str = ""
    rating: str = ""
    source: str = ""

    def to_dict(self):
        return asdict(self)


def price_number(value):
    cleaned = re.sub(r"[^0-9.,-]", "", str(value)).replace(",", "")
    try:
        number = Decimal(cleaned)
    except InvalidOperation:
        raise ValueError("가격을 숫자로 변환할 수 없습니다")
    if not number.is_finite() or number < 0:
        raise ValueError("유효하지 않은 가격")
    return float(number)


def canonical_url(url):
    parts = urlsplit(url)
    query = [
        (k, v) for k, v in parse_qsl(parts.query) if not k.lower().startswith("utm_")
    ]
    return urlunsplit(
        (parts.scheme.lower(), parts.netloc.lower(), parts.path, urlencode(query), "")
    )


def deduplicate(products):
    seen, unique = set(), []
    for product in products:
        key = canonical_url(product.url)
        if key not in seen:
            seen.add(key)
            product.url = key
            unique.append(product)
    return unique, len(products) - len(unique)
