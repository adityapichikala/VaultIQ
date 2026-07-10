import pytest
from src.chunking import DocumentChunker, Chunk
from src.ingest import Document

def test_document_chunker_small_text():
    """Test that a small document is not split."""
    chunker = DocumentChunker(chunk_size=100, chunk_overlap=10)
    doc = Document(
        doc_id="test_doc_1",
        content="This is a small text.",
        source_type="wiki",
        source_file="test.md",
        title="Test Doc"
    )
    chunks = chunker.chunk_documents([doc])
    
    assert len(chunks) == 1
    assert chunks[0].content == "This is a small text."
    assert chunks[0].metadata["total_chunks"] == 1
    assert chunks[0].doc_id == "test_doc_1"

def test_document_chunker_large_text():
    """Test that a large document is split into overlapping chunks."""
    chunker = DocumentChunker(chunk_size=50, chunk_overlap=10, min_chunk_size=10)
    
    text = (
        "Paragraph 1 is here. It has some words.\n\n"
        "Paragraph 2 is here. It is also long enough to split.\n\n"
        "Paragraph 3 is the final one."
    )
    
    doc = Document(
        doc_id="test_doc_2",
        content=text,
        source_type="wiki",
        source_file="test.md",
        title="Test Doc"
    )
    chunks = chunker.chunk_documents([doc])
    
    # Should be split into multiple chunks
    assert len(chunks) > 1
    
    # Check that metadata is preserved
    for i, chunk in enumerate(chunks):
        assert chunk.metadata["chunk_index"] == i
        assert chunk.source_type == "wiki"
        assert chunk.doc_id == "test_doc_2"
