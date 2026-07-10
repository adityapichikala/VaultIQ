import pytest
import os
import tempfile
from src.ingest.markdown_parser import MarkdownParser

def test_markdown_parser_heading_extraction():
    """Test that markdown parser correctly extracts headings as metadata."""
    parser = MarkdownParser()
    
    content = (
        "# Main Title\n"
        "Some intro text.\n"
        "## Subtitle 1\n"
        "Section 1 details.\n"
        "## Subtitle 2\n"
        "Section 2 details.\n"
    )
    
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix=".md") as f:
        f.write(content)
        temp_path = f.name
        
    try:
        docs = parser.parse(temp_path)
        
        assert len(docs) == 3
        
        # Check first section (Main Title)
        assert docs[0].title == "Main Title"
        assert docs[0].metadata["heading_level"] == 1
        assert "Some intro text." in docs[0].content
        
        # Check second section (Subtitle 1)
        assert docs[1].title == "Main Title"
        assert docs[1].metadata["heading_level"] == 2
        assert "Section 1 details." in docs[1].content
        
    finally:
        os.unlink(temp_path)
