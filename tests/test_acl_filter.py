import pytest
from src.retrieval import acl_filter

def test_acl_filter_all_employees():
    """Test that 'all-employees' docs are always returned."""
    results = [
        {"id": 1, "acl_roles": ["all-employees"]},
        {"id": 2, "acl_roles": ["engineering"]},
    ]
    
    # A user with NO special roles
    filtered = acl_filter(results, user_roles=[])
    
    assert len(filtered) == 1
    assert filtered[0]["id"] == 1

def test_acl_filter_specific_roles():
    """Test that specific roles match correctly."""
    results = [
        {"id": 1, "acl_roles": ["engineering"]},
        {"id": 2, "acl_roles": ["hr", "leadership"]},
        {"id": 3, "acl_roles": ["all-employees"]},
    ]
    
    # User with engineering role
    filtered_eng = acl_filter(results, user_roles=["engineering"])
    assert len(filtered_eng) == 2
    ids = [r["id"] for r in filtered_eng]
    assert 1 in ids
    assert 3 in ids
    assert 2 not in ids
    
    # User with hr role
    filtered_hr = acl_filter(results, user_roles=["hr"])
    assert len(filtered_hr) == 2
    ids = [r["id"] for r in filtered_hr]
    assert 2 in ids
    assert 3 in ids
    assert 1 not in ids
