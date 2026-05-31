# Knowledge Notes

Place your private Markdown notes in this folder, then build the local RAG index:

```powershell
python .\scripts\index_knowledge.py
python .\scripts\index_knowledge_vectors.py
```

Start from the sanitized public example if useful:

```powershell
Copy-Item .\examples\sample_growth_profile.md .\knowledge\personal_growth_notes.md
```

Personal notes are ignored by Git by default. Keep real reflection data private. Public demo content belongs under `examples/`.
