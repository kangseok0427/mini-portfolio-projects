from decimal import Decimal, InvalidOperation
import sqlite3
import time
import httpx


def normalize(item):
    identifier = str(item.get("id", "")).strip()
    name = str(item.get("name", "")).strip()
    if not identifier or not name:
        raise ValueError("주문번호 또는 상품명 누락")
    try:
        amount = Decimal(str(item["amount"]))
    except (KeyError, InvalidOperation):
        raise ValueError("금액 형식 오류")
    if not amount.is_finite() or amount < 0:
        raise ValueError("금액 범위 오류")
    return {
        "id": identifier,
        "name": name,
        "amount": str(amount.quantize(Decimal("0.01"))),
    }


def sync(fetch, folder, log, retries=2, delay=0.1):
    unique = {}
    duplicates = 0
    errors = []
    retry_count = 0
    for page in range(1, 5):
        data = None
        for attempt in range(retries + 1):
            try:
                log(f"페이지 {page} 요청 (시도 {attempt + 1})")
                data = fetch(page)
                break
            except ValueError:
                errors.append(f"페이지 {page}: JSON 응답 형식 오류")
                log(f"페이지 {page} 건너뜀")
                break
            except (httpx.HTTPError, TimeoutError, ConnectionError) as error:
                retryable = not isinstance(
                    error, httpx.HTTPStatusError
                ) or error.response.status_code in {429, 500, 502, 503, 504}
                if not retryable or attempt == retries:
                    errors.append(f"페이지 {page}: {type(error).__name__}")
                    log(f"페이지 {page} 건너뜀")
                    break
                retry_count += 1
                log("일시적인 API 오류 → 재시도")
                time.sleep(delay * (attempt + 1))
        if data is None:
            continue
        if not isinstance(data, list):
            errors.append(f"페이지 {page}: 목록 형식 오류")
            continue
        if not data:
            break
        for item in data:
            try:
                row = normalize(item)
                if row["id"] in unique:
                    duplicates += 1
                unique[row["id"]] = row
            except (ValueError, TypeError, AttributeError, InvalidOperation) as error:
                errors.append(f"상품 오류: {error}")
                log(f"잘못된 상품 제외: {error}")
    rows = list(unique.values())
    # One transaction: failures cannot leave half of this batch committed.
    with sqlite3.connect(folder / "orders.sqlite3") as db:
        db.execute(
            "CREATE TABLE IF NOT EXISTS orders(id TEXT PRIMARY KEY,name TEXT,amount TEXT)"
        )
        db.executemany(
            "INSERT INTO orders VALUES(:id,:name,:amount) ON CONFLICT(id) DO UPDATE SET name=excluded.name,amount=excluded.amount",
            rows,
        )
    log(f"{len(rows)}건을 SQLite 트랜잭션으로 저장")
    return rows, duplicates, errors, retry_count
