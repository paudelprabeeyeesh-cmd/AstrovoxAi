# Tutorial: Building a RAG Pipeline

## Overview
Learn how to ingest documents and query them using AstrovoxAI's RAG engine.

## Step 1: Ingest a Document
```bash
curl -X POST http://localhost:8000/rag/ingest \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@document.pdf"
```

## Step 2: Search Documents
```bash
curl -X GET "http://localhost:8000/rag/search?q=What+is+GraphRAG?" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## Step 3: Programmatic Usage
```python
from app.rag_engine import RAGEngine

engine = RAGEngine()

# Ingest
result = engine.ingest_pdf("document.pdf", user_id="user-123")

# Search
results = engine.search("What is GraphRAG?", user_id="user-123")

for chunk in results:
    print(f"Score: {chunk['score']}")
    print(f"Text: {chunk['text'][:200]}")
```

## Advanced: GraphRAG
```python
from app.knowledge_graph import KnowledgeGraph

kg = KnowledgeGraph()

# Extract entities
entities = kg.extract_entities("AstrovoxAI is built with FastAPI")

# Build graph
kg.add_entities(entities)
kg.build_relationships()

# Query
results = kg.query("What frameworks does AstrovoxAI use?")
```

## Next Steps
- [Multi-Modal RAG](./multimodal-rag.md)
- [Evaluation Guide](./evaluation.md)
- [Production Deployment](./production.md)
