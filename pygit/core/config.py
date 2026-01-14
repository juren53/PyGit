"""
Configuration management system for PyGit.

This module provides Git-compatible configuration management,
supporting both repository-specific and global configurations.
"""

import os
import configparser
from pathlib import Path
from typing import Dict, List, Optional, Any, Union


class Config:
    """Git configuration manager."""

    def __init__(self, git_dir: Path = None):
        self.git_dir = git_dir
        self.global_config_file = Path.home() / ".gitconfig"
        self.system_config_file = Path("/etc/gitconfig")

        # Load configuration in order of precedence
        self.config = configparser.ConfigParser()
        self._load_configs()

    def _load_configs(self):
        """Load configuration from system, global, and repository sources."""
        # System config (lowest precedence)
        if self.system_config_file.exists():
            self.config.read(self.system_config_file)

        # Global config (medium precedence)
        if self.global_config_file.exists():
            self.config.read(self.global_config_file)

        # Repository config (highest precedence)
        if self.git_dir:
            repo_config_file = self.git_dir / "config"
            if repo_config_file.exists():
                self.config.read(repo_config_file)

    def get(self, section: str, key: str, default: Any = None) -> Optional[str]:
        """Get a configuration value."""
        try:
            return self.config.get(section, key)
        except (configparser.NoSectionError, configparser.NoOptionError):
            return default

    def set(self, section: str, key: str, value: str, scope: str = "local"):
        """Set a configuration value."""
        if not self.config.has_section(section):
            self.config.add_section(section)

        self.config.set(section, key, value)

        # Write to appropriate config file
        if scope == "local" and self.git_dir:
            config_file = self.git_dir / "config"
        elif scope == "global":
            config_file = self.global_config_file
        elif scope == "system":
            config_file = self.system_config_file
        else:
            raise ValueError(f"Invalid scope: {scope}")

        config_file.parent.mkdir(parents=True, exist_ok=True)
        self.config.write(config_file.open("w"))

    def get_bool(self, section: str, key: str, default: bool = False) -> bool:
        """Get a boolean configuration value."""
        value = self.get(section, key, str(default))
        return value.lower() in ("true", "yes", "1", "on")

    def get_int(self, section: str, key: str, default: int = 0) -> int:
        """Get an integer configuration value."""
        try:
            return int(self.get(section, key, str(default)))
        except ValueError:
            return default

    def get_all(self, section: str, key: str) -> List[str]:
        """Get all values for a multivar key."""
        try:
            return self.config.get(section, key).split("\n")
        except (configparser.NoSectionError, configparser.NoOptionError):
            return []

    def get_section(self, section: str) -> Dict[str, str]:
        """Get all keys and values in a section."""
        try:
            return dict(self.config.items(section))
        except configparser.NoSectionError:
            return {}

    def unset(self, section: str, key: str, scope: str = "local"):
        """Remove a configuration value."""
        try:
            self.config.remove_option(section, key)
        except (configparser.NoSectionError, configparser.NoOptionError):
            return

        # Write to appropriate config file
        if scope == "local" and self.git_dir:
            config_file = self.git_dir / "config"
        elif scope == "global":
            config_file = self.global_config_file
        elif scope == "system":
            config_file = self.system_config_file
        else:
            raise ValueError(f"Invalid scope: {scope}")

        if config_file.exists():
            self.config.write(config_file.open("w"))

    def sections(self) -> List[str]:
        """Get all configuration sections."""
        return self.config.sections()

    def get_user_info(self) -> Dict[str, str]:
        """Get user name and email configuration."""
        return {
            "name": self.get("user", "name", ""),
            "email": self.get("user", "email", ""),
        }

    def set_user_info(self, name: str, email: str, scope: str = "global"):
        """Set user name and email configuration."""
        self.set("user", "name", name, scope)
        self.set("user", "email", email, scope)

    def get_remote(self, name: str) -> Dict[str, str]:
        """Get remote configuration."""
        return self.get_section(f'remote "{name}"')

    def set_remote(self, name: str, url: str, fetch: str = None, scope: str = "local"):
        """Set remote configuration."""
        section_name = f'remote "{name}"'
        self.set(section_name, "url", url, scope)

        if fetch:
            self.set(section_name, "fetch", fetch, scope)
        else:
            # Default fetch refspec
            self.set(
                section_name, "fetch", "+refs/heads/*:refs/remotes/{name}/*", scope
            )

    def get_branch(self, name: str) -> Dict[str, str]:
        """Get branch configuration."""
        return self.get_section(f'branch "{name}"')

    def set_branch(
        self, name: str, remote: str = None, merge: str = None, scope: str = "local"
    ):
        """Set branch configuration."""
        section_name = f'branch "{name}"'

        if remote:
            self.set(section_name, "remote", remote, scope)
        if merge:
            self.set(section_name, "merge", merge, scope)

    def __str__(self) -> str:
        """String representation of configuration."""
        lines = []
        for section in self.sections():
            lines.append(f"[{section}]")
            for key, value in self.config.items(section):
                lines.append(f"\t{key} = {value}")
            lines.append("")

        return "\n".join(lines)
