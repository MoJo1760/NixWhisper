"""Basic tests for NixWhisper."""

def test_import():
    """Test that the package can be imported."""
    import nixwhisper
    assert nixwhisper.__version__ is not None
