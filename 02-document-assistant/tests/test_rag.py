import asyncio
import pytest
from rag.documents import extract, chunks
from rag.store import Store
from rag.search import search
from rag.providers import DemoProvider, CompatibleProvider
import httpx


def test_upload_delete_and_duplicate(tmp_path):
    store = Store(tmp_path / "db.sqlite")
    first = store.add(
        "contract.txt", "계약 기간은 2026년 11월 30일까지입니다.".encode()
    )
    assert store.add("copy.txt", "계약 기간은 2026년 11월 30일까지입니다.".encode())[
        "duplicate"
    ]
    assert len(store.documents()) == 1
    found = search(store.corpus(), "계약 기간")
    assert found[0]["name"] == "contract.txt" and found[0]["page"] == 1
    store.save_exchange("s", "기간?", "11월", found)
    store.remove(first["id"])
    assert not store.corpus() and not store.history("s")


def test_document_comparison_covers_both_sources(tmp_path):
    store = Store(tmp_path / "db.sqlite")
    store.add("a.txt", "기존 계약 비용 120만원".encode())
    store.add("b.txt", "변경 제안 비용 160만원".encode())
    assert (
        len({s["document_id"] for s in search(store.corpus(), "두 문서의 차이")}) == 2
    )


def test_chunk_overlap_and_pdf_metadata():
    pieces = chunks([(3, "가" * 1800)])
    assert len(pieces) == 3 and all(p[0] == 3 for p in pieces)
    assert extract(
        "sample.pdf",
        __import__("pathlib").Path("demo/documents/03_expense_policy.pdf").read_bytes(),
    )[0][1].strip()


def test_bad_file_and_empty_text_rejected():
    with pytest.raises(ValueError):
        extract("x.txt", b"")
    with pytest.raises(ValueError):
        extract("x.exe", b"abc")
    with pytest.raises(ValueError):
        extract("x.pdf", b"not a pdf")


def test_api_provider_payload_and_citations(monkeypatch):
    monkeypatch.setenv("LLM_API_KEY", "test-key")
    monkeypatch.setenv("LLM_MODEL", "test-model")

    async def post(self, url, **kwargs):
        assert kwargs["headers"]["Authorization"] == "Bearer test-key"
        assert kwargs["json"]["messages"][-1]["content"].find("120만원") >= 0
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": "비용은 120만원입니다. [S1]"}}]},
        )

    monkeypatch.setattr(httpx.AsyncClient, "post", post)
    result = asyncio.run(
        CompatibleProvider().answer(
            "비용?",
            [{"ref": "S1", "name": "contract", "page": 1, "text": "120만원"}],
            [],
        )
    )
    assert "[S1]" in result


def test_empty_search_does_not_invent_answer():
    result = asyncio.run(DemoProvider().answer("없는 질문", [], []))
    assert "찾지 못" in result
