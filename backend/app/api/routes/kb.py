"""Knowledge Base API routes for upload and search."""
import logging
from fastapi import APIRouter, Depends, File, UploadFile, HTTPException, Query
from fastapi.responses import JSONResponse
import PyPDF2
from io import BytesIO

from app.core.auth import auth_client
from app.kb.retrieval import upsert_document, search_kb
from app.kb.models import KBSearchRequest, KBSearchResponse

logger = logging.getLogger(__name__)

kb_router = APIRouter(prefix="/kb", tags=["knowledge-base"])

ALLOWED_FILE_TYPES = ["text/plain", "application/pdf", "text/markdown"]
MAX_FILE_SIZE_MB = 10
MAX_FILE_SIZE = MAX_FILE_SIZE_MB * 1024 * 1024


@kb_router.post("/upload")
async def upload_kb_document(
    file: UploadFile = File(...),
    workspace_id: str = Query(...),
    title: str | None = Query(None),
    url: str | None = Query(None),
    tags: str | None = Query(None),  # Comma-separated tags
    auth_session=Depends(auth_client.require_session),
) -> JSONResponse:
    """
    Upload a document to the KB.

    Supports PDF and TXT files. Chunks the content, generates embeddings,
    and stores in Qdrant with deduplication.

    Args:
        file: File to upload (PDF or TXT)
        workspace_id: Workspace identifier
        title: Document title (defaults to filename)
        url: Source URL if applicable
        tags: Comma-separated tags (e.g., "support,faq,billing")

    Returns:
        Upload statistics (chunks uploaded, duplicates skipped)
    """
    user = auth_session.get("user")
    user_email = user.get("email", "unknown")

    # Read file
    binary_content = await file.read()
    file_name = file.filename or "untitled"
    file_type = file.content_type

    # Validate file type
    if file_type not in ALLOWED_FILE_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed: {', '.join(ALLOWED_FILE_TYPES)}",
        )

    # Validate file size
    if len(binary_content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File size exceeds {MAX_FILE_SIZE_MB} MB limit",
        )

    # Extract text content
    logger.info(f"Processing KB upload: file={file_name}, type={file_type}, user={user_email}")

    try:
        if file_type == "application/pdf":
            pdf_stream = BytesIO(binary_content)
            pdf_reader = PyPDF2.PdfReader(pdf_stream)
            file_text = ""
            for page in pdf_reader.pages:
                file_text += page.extract_text()
        else:
            file_text = binary_content.decode("utf-8")

    except Exception as e:
        logger.error(f"Failed to extract text from file: {e}")
        raise HTTPException(status_code=400, detail=f"Failed to extract text: {str(e)}")

    if not file_text.strip():
        raise HTTPException(status_code=400, detail="File contains no readable text")

    # Parse tags
    tag_list = []
    if tags:
        tag_list = [t.strip() for t in tags.split(",") if t.strip()]

    # Upload to Qdrant
    try:
        stats = upsert_document(
            file_content=file_text,
            workspace_id=workspace_id,
            source="upload",
            title=title or file_name,
            url=url,
            tags=tag_list,
        )

        logger.info(f"KB upload complete: {stats}")

        return JSONResponse(
            status_code=200,
            content={
                "message": "Document uploaded successfully",
                "file_name": file_name,
                "workspace_id": workspace_id,
                "stats": stats,
            }
        )

    except Exception as e:
        logger.error(f"Failed to upload document to KB: {e}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@kb_router.get("/search")
async def search_kb_endpoint(
    q: str = Query(..., description="Search query"),
    workspace_id: str = Query(...),
    k: int = Query(5, ge=1, le=50, description="Number of results"),
    with_vectors: bool = Query(False, description="Include vectors (debug)"),
    auth_session=Depends(auth_client.require_session),
) -> KBSearchResponse:
    """
    Search the KB for relevant chunks.

    Args:
        q: Search query text
        workspace_id: Workspace to search within
        k: Number of results to return (1-50)
        with_vectors: Include embedding vectors in response (for debugging)

    Returns:
        Search results with relevance scores
    """
    user = auth_session.get("user")
    user_email = user.get("email", "unknown")

    logger.info(f"KB search: query='{q[:50]}...', workspace={workspace_id}, k={k}, user={user_email}")

    try:
        results = search_kb(
            query=q,
            workspace_id=workspace_id,
            k=k,
            with_vectors=with_vectors,
        )

        return KBSearchResponse(
            results=results,
            query=q,
            k=k,
        )

    except Exception as e:
        logger.error(f"KB search failed: {e}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")
