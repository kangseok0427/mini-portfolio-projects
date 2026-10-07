from pathlib import Path
from .network import PublicFetcher
from .sources import parse_page
from .models import deduplicate
from .export import export_excel


def collect(query, source, max_pages, destination, update, fetcher=None):
    all_products, errors = [], []
    url = (
        query.strip()
        if query.strip().startswith(("https://", "http://"))
        else "https://books.toscrape.com/"
    )
    keyword = (
        ""
        if query.strip().startswith(("https://", "http://"))
        else query.strip().casefold()
    )
    fetcher = fetcher or PublicFetcher()
    for page in range(max_pages if source != "demo" else 1):
        update(int(page / max_pages * 85), f"{page + 1}번째 페이지 수집 중")
        try:
            if source == "demo":
                body = (Path(__file__).parent.parent / "demo/store.html").read_text(
                    encoding="utf-8"
                )
                current = "https://demo.example/products"
            else:
                body, current = fetcher.fetch(url)
            products, next_url, item_errors = parse_page(body, current)
            all_products.extend(
                p for p in products if not keyword or keyword in p.name.casefold()
            )
            errors.extend(item_errors)
            if not next_url:
                break
            url = next_url
        except Exception as error:
            errors.append(f"페이지 {page + 1}: {error}")
            # A predictable Books listing URL allows later pages to continue after a failure.
            if "books.toscrape.com" in url:
                url = f"https://books.toscrape.com/catalogue/page-{page + 2}.html"
            else:
                break
    products, duplicates = deduplicate(all_products)
    update(90, "중복 제거 및 Excel 생성 중")
    summary = {
        "수집 조건": query or "전체",
        "출처": source,
        "저장 건수": len(products),
        "중복 제거": duplicates,
        "오류 건수": len(errors),
        "오류 상세": " | ".join(errors) or "없음",
    }
    export_excel(products, destination, summary)
    return products, duplicates, errors
