# KB Pipeline Demo - cURL Commands

This document provides example cURL commands to test the new Knowledge Base pipeline.

## Prerequisites

1. Start the backend server (with Qdrant running):
   ```bash
   cd backend
   docker-compose up -d  # Starts PostgreSQL, Redis, Qdrant
   uvicorn app.main:app --reload
   ```

2. Ensure you have a valid authentication token from Auth0

## Environment Variables

Make sure these are set in your `.env` file:
```bash
OPENAI_API_KEY=sk-...
QDRANT_URL=http://localhost:6333
QDRANT_COLLECTION_NAME=reploom_documents
```

## Demo Workflow

### 1. Upload a Document to KB

**Upload a text file:**
```bash
curl -X POST "http://localhost:8000/api/kb/upload?workspace_id=demo-workspace&title=Product%20FAQ&tags=support,faq" \
  -H "Authorization: Bearer YOUR_AUTH_TOKEN" \
  -F "file=@sample_doc.txt"
```

**Expected Response:**
```json
{
  "message": "Document uploaded successfully",
  "file_name": "sample_doc.txt",
  "workspace_id": "demo-workspace",
  "stats": {
    "chunks_total": 15,
    "chunks_uploaded": 12,
    "duplicates_skipped": 3
  }
}
```

**Upload a PDF:**
```bash
curl -X POST "http://localhost:8000/api/kb/upload?workspace_id=demo-workspace&title=User%20Guide" \
  -H "Authorization: Bearer YOUR_AUTH_TOKEN" \
  -F "file=@guide.pdf"
```

### 2. Search the KB

**Basic search:**
```bash
curl -X GET "http://localhost:8000/api/kb/search?q=How%20do%20I%20reset%20my%20password&workspace_id=demo-workspace&k=5" \
  -H "Authorization: Bearer YOUR_AUTH_TOKEN"
```

**Expected Response:**
```json
{
  "results": [
    {
      "chunk_id": "uuid-here",
      "content": "To reset your password, click on 'Forgot Password' on the login page...",
      "score": 0.89,
      "workspace_id": "demo-workspace",
      "source": "upload",
      "title": "Product FAQ",
      "url": null,
      "tags": ["support", "faq"]
    },
    {
      "chunk_id": "uuid-here-2",
      "content": "Password requirements: minimum 8 characters...",
      "score": 0.76,
      "workspace_id": "demo-workspace",
      "source": "upload",
      "title": "Product FAQ",
      "url": null,
      "tags": ["support", "faq"]
    }
  ],
  "query": "How do I reset my password",
  "k": 5
}
```

**Search with debug vectors (slower):**
```bash
curl -X GET "http://localhost:8000/api/kb/search?q=billing%20question&workspace_id=demo-workspace&k=3&with_vectors=true" \
  -H "Authorization: Bearer YOUR_AUTH_TOKEN"
```

### 3. Test contextBuilder Integration

Generate a draft that uses KB context:

```bash
curl -X POST "http://localhost:8000/api/agents/reploom/run-draft" \
  -H "Authorization: Bearer YOUR_AUTH_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "original_message_summary": "Customer asking how to reset their password",
    "workspace_id": "demo-workspace"
  }'
```

The draft response should now include citations from the KB snippets retrieved by contextBuilder.

## Test Data

### Sample FAQ Document (sample_faq.txt)

Create a test file to upload:

```text
# Product FAQ

## Account Management

Q: How do I reset my password?
A: To reset your password, navigate to the login page and click "Forgot Password".
You'll receive an email with a reset link. Passwords must be at least 8 characters
long and include one uppercase letter, one number, and one special character.

Q: How do I update my billing information?
A: Go to Settings > Billing and click "Update Payment Method". You can add credit
cards, debit cards, or link your bank account.

## Support

Q: How do I contact support?
A: Email us at support@example.com or use the live chat feature in the bottom
right corner of the app. We're available 24/7.

Q: What are your response time SLAs?
A: Priority tickets: 4 hours, Standard tickets: 24 hours, Low priority: 72 hours.
```

### Upload the Sample

```bash
echo "# Product FAQ..." > sample_faq.txt  # (use content above)

curl -X POST "http://localhost:8000/api/kb/upload?workspace_id=demo-workspace&title=Product%20FAQ&tags=support,faq,billing" \
  -H "Authorization: Bearer YOUR_AUTH_TOKEN" \
  -F "file=@sample_faq.txt"
```

### Search Examples

```bash
# Search for password reset
curl -X GET "http://localhost:8000/api/kb/search?q=forgot%20password&workspace_id=demo-workspace&k=2" \
  -H "Authorization: Bearer YOUR_AUTH_TOKEN"

# Search for billing
curl -X GET "http://localhost:8000/api/kb/search?q=update%20payment%20method&workspace_id=demo-workspace&k=2" \
  -H "Authorization: Bearer YOUR_AUTH_TOKEN"

# Search for support contact
curl -X GET "http://localhost:8000/api/kb/search?q=contact%20support%20email&workspace_id=demo-workspace&k=2" \
  -H "Authorization: Bearer YOUR_AUTH_TOKEN"
```

## Verification

### Check Qdrant Collection

You can verify the collection was created:

```bash
curl http://localhost:6333/collections
```

Expected:
```json
{
  "result": {
    "collections": [
      {
        "name": "reploom_documents",
        "vector_size": 1536
      }
    ]
  }
}
```

### Count Points in Collection

```bash
curl http://localhost:6333/collections/reploom_documents
```

## Troubleshooting

### Qdrant Not Running
```bash
cd backend
docker-compose up -d qdrant
docker-compose logs qdrant
```

### Check Qdrant Health
```bash
curl http://localhost:6333/healthz
```

### View Logs
```bash
# Backend logs will show KB operations
tail -f backend/logs/app.log  # If logging to file

# Or check stdout
```

### Test Deduplication

Upload the same document twice:
```bash
curl -X POST "http://localhost:8000/api/kb/upload?workspace_id=test&title=Test" \
  -H "Authorization: Bearer YOUR_AUTH_TOKEN" \
  -F "file=@sample_faq.txt"

# Second upload
curl -X POST "http://localhost:8000/api/kb/upload?workspace_id=test&title=Test" \
  -H "Authorization: Bearer YOUR_AUTH_TOKEN" \
  -F "file=@sample_faq.txt"
```

The second upload should show high `duplicates_skipped` count because chunks are deduplicated by content hash.

## Performance Notes

- **Batch Size**: Embeddings are generated in batches of 100 texts
- **with_vectors=false**: Default setting skips returning vectors in search results (faster)
- **Token Counting**: Uses tiktoken for accurate token-based chunking (800 tokens/chunk, 200 overlap)
- **Stable IDs**: Points use UUID v5 based on content hash (same content = same ID)

## Next Steps

1. Monitor OpenAI API usage for embedding costs
2. Configure workspace-specific settings
3. Add more documents to build up the KB
4. Test draft generation with KB context
5. Implement feedback loop to improve relevance
