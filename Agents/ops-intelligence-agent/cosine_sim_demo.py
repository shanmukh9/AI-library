import json
import math
import urllib.request


EMBEDDINGS_URL = "http://127.0.0.1:1234/v1/embeddings"
EMBEDDING_MODEL = "text-embedding-nomic-embed-text-v1.5"

BASE_ALERT = "CPU usage on prod-api-server-01 exceeded 95% for 10 consecutive minutes"
RELATED_ALERT = "High processor utilization detected on the production API node"
UNRELATED_ALERT = "SSL certificate for api.internal.company.com expires in 7 days"


def embed(text):
    payload = {
        "model": EMBEDDING_MODEL,
        "input": text,
    }
    request = urllib.request.Request(
        EMBEDDINGS_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        body = json.loads(response.read().decode("utf-8"))
    return [float(value) for value in body["data"][0]["embedding"]]


def cosine_similarity(left, right):
    dot_product = sum(a * b for a, b in zip(left, right))
    left_magnitude = math.sqrt(sum(value * value for value in left))
    right_magnitude = math.sqrt(sum(value * value for value in right))
    if left_magnitude == 0 or right_magnitude == 0:
        return 0.0
    return dot_product / (left_magnitude * right_magnitude)


base_embedding = embed(BASE_ALERT)
related_embedding = embed(RELATED_ALERT)
unrelated_embedding = embed(UNRELATED_ALERT)

related_score = cosine_similarity(base_embedding, related_embedding)
unrelated_score = cosine_similarity(base_embedding, unrelated_embedding)

print(f"Embedding model: {EMBEDDING_MODEL}")
print(f"Vector dimensions: {len(base_embedding)}")
print()
print(f"Base alert:      {BASE_ALERT}")
print(f"Related alert:   {RELATED_ALERT}")
print(f"Related score:   {related_score:.4f}")
print()
print(f"Unrelated alert: {UNRELATED_ALERT}")
print(f"Unrelated score: {unrelated_score:.4f}")
print()
print(f"Similarity gap:  {related_score - unrelated_score:.4f}")
print(f"Expected result: {'PASS' if related_score > unrelated_score else 'FAIL'}")
