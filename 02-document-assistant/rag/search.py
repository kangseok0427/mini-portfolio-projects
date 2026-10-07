from sklearn.feature_extraction.text import TfidfVectorizer
import numpy as np


def search(corpus, query, limit=6):
    if not corpus:
        return []
    vectorizer = TfidfVectorizer(
        analyzer="char", ngram_range=(2, 4), max_features=30000
    )
    try:
        matrix = vectorizer.fit_transform([row["text"] for row in corpus])
    except ValueError:
        return []
    scores = (matrix @ vectorizer.transform([query]).T).toarray().ravel()
    ranked = list(np.argsort(-scores))
    selected = []
    broad = any(word in query for word in ("요약", "차이", "비교", "summar", "compare"))
    if broad:
        seen = set()
        for i in ranked:
            if corpus[i]["document_id"] not in seen:
                seen.add(corpus[i]["document_id"])
                selected.append(int(i))
                if len(selected) >= limit:
                    break
    for i in ranked:
        if scores[i] <= 0 or len(selected) >= limit:
            break
        if int(i) not in selected:
            selected.append(int(i))
    return [
        dict(corpus[i], ref=f"S{n + 1}", score=round(float(scores[i]), 4))
        for n, i in enumerate(selected)
    ]
