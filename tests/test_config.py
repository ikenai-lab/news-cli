import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
import json
from src.config import Config

@pytest.fixture
def mock_config_path(tmp_path):
    config_file = tmp_path / "config.json"
    with patch('src.config.Config._get_config_path', return_value=config_file):
        yield config_file

def test_load_defaults(mock_config_path):
    """Test loading when file doesn't exist returns defaults."""
    cfg = Config.load()
    assert cfg.default_model == "llama3.2:3b"
    assert cfg.default_limit == 5

def test_save_and_load(mock_config_path):
    """Test saving changes and reloading them."""
    cfg = Config(default_model="test-model", default_limit=10)
    cfg.save()
    
    assert mock_config_path.exists()
    
    loaded_cfg = Config.load()
    assert loaded_cfg.default_model == "test-model"
    assert loaded_cfg.default_limit == 10

def test_set_value(mock_config_path):
    """Test setting specific values updates file."""
    cfg = Config.load()
    cfg.set("default_model", "new-model")
    
    with open(mock_config_path) as f:
        data = json.load(f)
        assert data["default_model"] == "new-model"

def test_unknown_key(mock_config_path):
    """Test setting unknown key raises error."""
    cfg = Config.load()
    with pytest.raises(KeyError):
        cfg.set("unknown_key", "value")
