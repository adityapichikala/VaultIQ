import pytest
import os
import tempfile
from src.ingest.pipeline import IngestionPipeline

def test_full_pipeline_dummy_data():
    """Integration test: test pipeline on a temporary dummy directory."""
    pipeline = IngestionPipeline()
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create dummy structure
        wiki_dir = os.path.join(temp_dir, "wiki")
        os.makedirs(wiki_dir)
        
        with open(os.path.join(wiki_dir, "dummy.md"), "w") as f:
            f.write("# Dummy Doc\n**ACL: engineering**\nHello world.")
            
        # Run pipeline
        docs = pipeline.ingest_directory(temp_dir)
        
        # Validate
        assert len(docs) == 1
        assert docs[0].source_type == "wiki"
        assert docs[0].title == "Dummy Doc"
        assert "engineering" in docs[0].acl_roles
        assert "Hello world" in docs[0].content
