from tac import TAC, TACConfig, __version__


def test_version():
    """Test that version is available and follows PEP 440 format."""
    assert isinstance(__version__, str)
    # Version should be non-empty and look like a valid version (e.g., "0.1.0", "0.1.0a1")
    assert len(__version__) > 0
    assert __version__[0].isdigit()


def test_imports():
    """Test that all main classes can be imported."""
    assert TAC is not None
    assert TACConfig is not None


def test_basic_tac_functionality():
    """Test basic TAC functionality works."""
    config = {
        "account_sid": "ACtest123",
        "auth_token": "test_token_123",
        "api_key": "SK123",
        "api_secret": "test_api_token",
        "conversation_configuration_id": "conv_configuration_test123",
        "phone_number": "+15551234567",
    }
    tac = TAC(config)
    assert tac.config.auth_token == "test_token_123"
    assert tac.config.api_key == "SK123"
    assert tac.config.api_secret == "test_api_token"
