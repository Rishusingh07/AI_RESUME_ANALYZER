import re
import math
from collections import Counter


def _normalize(text):
    return re.sub(r"\s+", " ", text.lower()).strip()


def _tokenize(text):
    # tokenizes into words and common symbols, similar to previous behavior
    return re.findall(r"\b[a-zA-Z][a-zA-Z+#.\-]{1,}\b", text.lower())


def _tf(counter):
    total = sum(counter.values())
    if total == 0:
        return {}
    return {k: v / total for k, v in counter.items()}


def compute_match(resume_text, job_text):
    """Return match percentage (0-100) using a lightweight TF-IDF + cosine similarity implementation.
    This avoids scikit-learn to keep the project pure-Python on systems without compiled build tools.
    """
    docs = [_normalize(resume_text), _normalize(job_text)]
    token_lists = [_tokenize(d) for d in docs]
    counters = [Counter(toks) for toks in token_lists]

    # vocabulary
    vocab = set().union(*[set(c.keys()) for c in counters])
    if not vocab:
        return 0.0

    # document frequency
    df = {term: sum(1 for c in counters if term in c) for term in vocab}
    N = len(counters)
    idf = {term: math.log((1 + N) / (1 + df[term])) + 1 for term in vocab}

    tf_vectors = []
    for c in counters:
        tf = _tf(c)
        tfidf = {term: tf.get(term, 0.0) * idf[term] for term in vocab}
        tf_vectors.append(tfidf)

    # cosine similarity
    v1 = tf_vectors[0]
    v2 = tf_vectors[1]
    dot = sum(v1[t] * v2[t] for t in vocab)
    norm1 = math.sqrt(sum(v1[t] ** 2 for t in vocab))
    norm2 = math.sqrt(sum(v2[t] ** 2 for t in vocab))
    if norm1 == 0 or norm2 == 0:
        return 0.0
    sim = dot / (norm1 * norm2)
    return round(float(sim) * 100, 2)


def find_missing_skills(resume_text, job_text):
    """Return job tokens not present in the resume."""
    resume_tokens = set(_tokenize(resume_text))
    job_tokens = set(_tokenize(job_text))
    stop = {"and", "the", "with", "for", "you", "our", "are", "will", "have"}
    missing = sorted(t for t in job_tokens - resume_tokens if t not in stop and len(t) > 2)
    return missing
