"""
Unit tests for pygit.core.config module.

Tests for Config class including reading, writing, and
configuration inheritance.
"""

import tempfile
from pathlib import Path

import pytest

from pygit.core.config import Config


class TestConfigBasic:
    """Basic configuration tests."""

    @pytest.mark.unit
    def test_config_creation(self, empty_repo):
        """Test creating a config object."""
        config = Config(empty_repo.git_dir)
        assert config.git_dir == empty_repo.git_dir

    @pytest.mark.unit
    def test_config_without_git_dir(self):
        """Test creating config without git directory."""
        config = Config()
        assert config.git_dir is None

    @pytest.mark.unit
    def test_get_nonexistent_value(self, empty_repo):
        """Test getting a non-existent config value."""
        config = Config(empty_repo.git_dir)
        result = config.get("nonexistent", "key")
        assert result is None

    @pytest.mark.unit
    def test_get_with_default(self, empty_repo):
        """Test getting with default value."""
        config = Config(empty_repo.git_dir)
        result = config.get("nonexistent", "key", "default_value")
        assert result == "default_value"

    @pytest.mark.unit
    def test_set_and_get(self, empty_repo):
        """Test setting and getting a value."""
        config = Config(empty_repo.git_dir)
        config.set("test", "key", "value", "local")

        result = config.get("test", "key")
        assert result == "value"

    @pytest.mark.unit
    def test_set_creates_section(self, empty_repo):
        """Test that set creates section if needed."""
        config = Config(empty_repo.git_dir)
        config.set("newsection", "newkey", "newvalue", "local")

        assert "newsection" in config.sections()


class TestConfigTypes:
    """Tests for typed config values."""

    @pytest.mark.unit
    def test_get_bool_true_values(self, empty_repo):
        """Test getting boolean true values."""
        config = Config(empty_repo.git_dir)

        for true_val in ["true", "yes", "1", "on"]:
            config.set("test", "bool", true_val, "local")
            assert config.get_bool("test", "bool") is True

    @pytest.mark.unit
    def test_get_bool_false_values(self, empty_repo):
        """Test getting boolean false values."""
        config = Config(empty_repo.git_dir)

        for false_val in ["false", "no", "0", "off"]:
            config.set("test", "bool", false_val, "local")
            assert config.get_bool("test", "bool") is False

    @pytest.mark.unit
    def test_get_bool_default(self, empty_repo):
        """Test boolean default value."""
        config = Config(empty_repo.git_dir)
        assert config.get_bool("nonexistent", "key", True) is True
        assert config.get_bool("nonexistent", "key", False) is False

    @pytest.mark.unit
    def test_get_int(self, empty_repo):
        """Test getting integer value."""
        config = Config(empty_repo.git_dir)
        config.set("test", "number", "42", "local")

        result = config.get_int("test", "number")
        assert result == 42

    @pytest.mark.unit
    def test_get_int_invalid(self, empty_repo):
        """Test getting invalid integer returns default."""
        config = Config(empty_repo.git_dir)
        config.set("test", "number", "not_a_number", "local")

        result = config.get_int("test", "number", 99)
        assert result == 99

    @pytest.mark.unit
    def test_get_int_default(self, empty_repo):
        """Test integer default value."""
        config = Config(empty_repo.git_dir)
        result = config.get_int("nonexistent", "key", 123)
        assert result == 123


class TestConfigSections:
    """Tests for section operations."""

    @pytest.mark.unit
    def test_sections_list(self, empty_repo):
        """Test listing sections."""
        config = Config(empty_repo.git_dir)
        config.set("section1", "key", "value", "local")
        config.set("section2", "key", "value", "local")

        sections = config.sections()
        assert "section1" in sections
        assert "section2" in sections

    @pytest.mark.unit
    def test_get_section(self, empty_repo):
        """Test getting all values in a section."""
        config = Config(empty_repo.git_dir)
        config.set("testsection", "key1", "value1", "local")
        config.set("testsection", "key2", "value2", "local")

        section = config.get_section("testsection")
        assert section["key1"] == "value1"
        assert section["key2"] == "value2"

    @pytest.mark.unit
    def test_get_section_nonexistent(self, empty_repo):
        """Test getting non-existent section."""
        config = Config(empty_repo.git_dir)
        section = config.get_section("nonexistent")
        assert section == {}


class TestConfigUnset:
    """Tests for unsetting config values."""

    @pytest.mark.unit
    def test_unset_existing(self, empty_repo):
        """Test unsetting an existing value."""
        config = Config(empty_repo.git_dir)
        config.set("test", "key", "value", "local")
        config.unset("test", "key", "local")

        result = config.get("test", "key")
        assert result is None

    @pytest.mark.unit
    def test_unset_nonexistent(self, empty_repo):
        """Test unsetting non-existent value doesn't raise."""
        config = Config(empty_repo.git_dir)
        # Should not raise
        config.unset("nonexistent", "key", "local")


class TestConfigUserInfo:
    """Tests for user info helpers."""

    @pytest.mark.unit
    def test_get_user_info_defaults(self, empty_repo):
        """Test getting user info returns values (may be from global config)."""
        config = Config(empty_repo.git_dir)
        info = config.get_user_info()

        # User info will either be empty or from global config
        assert "name" in info
        assert "email" in info
        assert isinstance(info["name"], str)
        assert isinstance(info["email"], str)

    @pytest.mark.unit
    def test_set_and_get_user_info(self, empty_repo):
        """Test setting and getting user info."""
        config = Config(empty_repo.git_dir)
        config.set("user", "name", "Test User", "local")
        config.set("user", "email", "test@example.com", "local")

        info = config.get_user_info()
        assert info["name"] == "Test User"
        assert info["email"] == "test@example.com"


class TestConfigRemote:
    """Tests for remote configuration helpers."""

    @pytest.mark.unit
    def test_set_remote(self, empty_repo):
        """Test setting remote configuration."""
        config = Config(empty_repo.git_dir)
        config.set_remote("origin", "https://github.com/user/repo.git")

        remote = config.get_remote("origin")
        assert remote["url"] == "https://github.com/user/repo.git"

    @pytest.mark.unit
    def test_set_remote_with_fetch(self, empty_repo):
        """Test setting remote with custom fetch refspec."""
        config = Config(empty_repo.git_dir)
        config.set_remote(
            "origin",
            "https://github.com/user/repo.git",
            "+refs/heads/*:refs/remotes/origin/*"
        )

        remote = config.get_remote("origin")
        assert remote["url"] == "https://github.com/user/repo.git"
        assert "fetch" in remote

    @pytest.mark.unit
    def test_get_remote_nonexistent(self, empty_repo):
        """Test getting non-existent remote."""
        config = Config(empty_repo.git_dir)
        remote = config.get_remote("nonexistent")
        assert remote == {}


class TestConfigBranch:
    """Tests for branch configuration helpers."""

    @pytest.mark.unit
    def test_set_branch(self, empty_repo):
        """Test setting branch configuration."""
        config = Config(empty_repo.git_dir)
        config.set_branch("main", "origin", "refs/heads/main")

        branch = config.get_branch("main")
        assert branch["remote"] == "origin"
        assert branch["merge"] == "refs/heads/main"

    @pytest.mark.unit
    def test_get_branch_nonexistent(self, empty_repo):
        """Test getting non-existent branch config."""
        config = Config(empty_repo.git_dir)
        branch = config.get_branch("nonexistent")
        assert branch == {}


class TestConfigStr:
    """Tests for string representation."""

    @pytest.mark.unit
    def test_str_representation(self, empty_repo):
        """Test string representation of config."""
        config = Config(empty_repo.git_dir)
        config.set("test", "key", "value", "local")

        config_str = str(config)
        assert "[test]" in config_str
        assert "key = value" in config_str


class TestConfigScopes:
    """Tests for configuration scopes."""

    @pytest.mark.unit
    def test_invalid_scope_raises(self, empty_repo):
        """Test that invalid scope raises error."""
        config = Config(empty_repo.git_dir)

        with pytest.raises(ValueError) as exc_info:
            config.set("test", "key", "value", "invalid_scope")

        assert "Invalid scope" in str(exc_info.value)
