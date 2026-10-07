from io import BytesIO
from pypdf import PdfReader


def extract(name, content):
    if len(content) > 10_000_000:
        raise ValueError("파일은 10MB 이하만 업로드할 수 있습니다")
    if name.lower().endswith(".txt"):
        try:
            text = content.decode("utf-8-sig")
        except UnicodeDecodeError:
            raise ValueError("TXT 파일은 UTF-8로 저장해주세요")
        pages = [(1, text)]
    elif name.lower().endswith(".pdf"):
        try:
            reader = PdfReader(BytesIO(content))
            if reader.is_encrypted:
                raise ValueError("암호화된 PDF는 지원하지 않습니다")
            if len(reader.pages) > 200:
                raise ValueError("PDF는 200페이지 이하만 지원합니다")
            pages = [
                (i + 1, page.extract_text() or "")
                for i, page in enumerate(reader.pages)
            ]
        except ValueError:
            raise
        except Exception:
            raise ValueError("PDF를 읽을 수 없습니다")
    else:
        raise ValueError("PDF 또는 TXT만 지원합니다")
    if sum(len(text) for _, text in pages) > 200_000:
        raise ValueError("추출된 텍스트가 너무 깁니다")
    if not any(text.strip() for _, text in pages):
        raise ValueError("텍스트가 없습니다. 스캔 PDF에는 OCR이 필요합니다")
    return pages


def chunks(pages, size=800, overlap=120):
    result = []
    for page, text in pages:
        text = text.replace("\x00", "").strip()
        start = 0
        while start < len(text):
            end = min(start + size, len(text))
            if end < len(text):
                boundary = text.rfind("\n", start + size // 2, end)
                if boundary > start:
                    end = boundary
            piece = text[start:end].strip()
            if piece:
                result.append((page, piece))
            if end == len(text):
                break
            start = max(start + 1, end - overlap)
    return result
