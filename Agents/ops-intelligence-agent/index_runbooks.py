from runbook_rag import INDEX_PATH, build_runbook_index


index = build_runbook_index()

print(f"Embedded {index['chunk_count']} runbook chunks")
print(f"Embedding model: {index['embedding_model']}")
print(f"Saved index: {INDEX_PATH}")
