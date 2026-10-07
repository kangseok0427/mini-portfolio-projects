"""Intentionally flawed training example, not a production implementation."""

import csv


class LegacyFailure(Exception):
    def __init__(self, message, rows):
        super().__init__(message)
        self.rows = rows


def sync(fetch, folder, log):
    rows = []
    try:
        for page in range(1, 5):
            log(f"페이지 {page} 요청")
            data = fetch(page)  # no retry; one failed request ends the entire job
            if not data:
                break
            for item in data:
                rows.append(
                    {
                        "id": item["id"],
                        "name": item["name"],
                        "amount": float(item["amount"]),
                    }
                )
            # Rewrites output after each page, leaving an incomplete file on failure.
            with open(
                folder / "orders.csv", "w", newline="", encoding="utf-8-sig"
            ) as f:
                writer = csv.DictWriter(f, fieldnames=["id", "name", "amount"])
                writer.writeheader()
                writer.writerows(rows)
        return rows
    except Exception as error:
        raise LegacyFailure(f"{type(error).__name__}: {error}", rows) from error
