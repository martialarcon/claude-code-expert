"""
AI Architect v2 - Configuration Loader

Loads configuration from config.yaml with environment variable support.
"""

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings


class ModelsConfig(BaseModel):
    """Model configuration."""
    # Provider: "claude" or "glm"
    provider: str = "claude"
    # Claude models
    analysis: str = "claude-sonnet-4-20250514"
    synthesis: str = "claude-opus-4-6"
    # GLM models (used when provider="glm")
    glm_analysis: str = "glm-4-flash"
    glm_synthesis: str = "glm-4-plus"


class ThresholdsConfig(BaseModel):
    """Processing thresholds."""
    signal_score_min: int = Field(default=4, ge=1, le=10)
    novelty_score_min: float = Field(default=0.3, ge=0.0, le=1.0)
    batch_size: int = Field(default=10, ge=1, le=50)
    # Rate limiting delays (seconds)
    request_delay: float = Field(default=5.0, ge=0.0, le=60.0)  # Delay between individual API calls
    batch_delay: float = Field(default=3.0, ge=0.0, le=60.0)    # Delay between batch API calls


class GitHubRepoConfig(BaseModel):
    """GitHub repository configuration."""
    owner: str
    repo: str


class DocsCollectorConfig(BaseModel):
    """Documentation collector configuration."""
    enabled: bool = True
    sources: list[str] = []
    snapshot_dir: str = "data/snapshots"


class GitHubSignalsCollectorConfig(BaseModel):
    """GitHub signals collector configuration."""
    enabled: bool = True
    repos: list[GitHubRepoConfig] = []
    max_items: int = 50


class GitHubEmergingCollectorConfig(BaseModel):
    """GitHub emerging repos collector configuration."""
    enabled: bool = True
    max_stars: int = 100
    min_growth_rate: float = 1.5
    topics: list[str] = []
    max_items: int = 30


class GitHubReposCollectorConfig(BaseModel):
    """GitHub consolidated repos collector configuration."""
    enabled: bool = True
    min_stars: int = 100
    topics: list[str] = []
    max_items: int = 30


class FeedConfig(BaseModel):
    """RSS feed configuration."""
    name: str
    url: str


class BlogsCollectorConfig(BaseModel):
    """Blogs collector configuration."""
    enabled: bool = True
    feeds: list[FeedConfig] = []
    max_items: int = 20


class StackOverflowCollectorConfig(BaseModel):
    """StackOverflow collector configuration."""
    enabled: bool = True
    tags: list[str] = []
    min_score: int = 5
    max_items: int = 30


class CollectorsConfig(BaseModel):
    """All collectors configuration."""
    docs: DocsCollectorConfig = DocsCollectorConfig()
    github_signals: GitHubSignalsCollectorConfig = GitHubSignalsCollectorConfig()
    github_emerging: GitHubEmergingCollectorConfig = GitHubEmergingCollectorConfig()
    github_repos: GitHubReposCollectorConfig = GitHubReposCollectorConfig()
    blogs: BlogsCollectorConfig = BlogsCollectorConfig()
    stackoverflow: StackOverflowCollectorConfig = StackOverflowCollectorConfig()


class ChromaDBConfig(BaseModel):
    """ChromaDB storage configuration."""
    persist_directory: str = "data/chromadb"
    collections: list[str] = ["items", "analysis", "synthesis", "snapshots"]


class StorageConfig(BaseModel):
    """Storage configuration."""
    chromadb: ChromaDBConfig = ChromaDBConfig()


class OutputConfig(BaseModel):
    """Output directories configuration."""
    daily_dir: str = "output/daily"
    weekly_dir: str = "output/weekly"
    monthly_dir: str = "output/monthly"
    topics_dir: str = "output/topics"
    competitive_dir: str = "output/competitive"
    master_file: str = "output/master.md"
    index_file: str = "output/index.md"


class NtfyConfig(BaseModel):
    """ntfy.sh notification configuration."""
    enabled: bool = True
    topic: str = "ai-architect"
    url: str = "https://ntfy.sh"


class NotificationsConfig(BaseModel):
    """Notifications configuration."""
    ntfy: NtfyConfig = NtfyConfig()


class LoggingConfig(BaseModel):
    """Logging configuration."""
    level: str = "INFO"
    format: str = "json"  # json | text


class Config(BaseModel):
    """Main configuration model."""
    models: ModelsConfig = ModelsConfig()
    thresholds: ThresholdsConfig = ThresholdsConfig()
    mode: str = "daily"
    collectors: CollectorsConfig = CollectorsConfig()
    storage: StorageConfig = StorageConfig()
    output: OutputConfig = OutputConfig()
    notifications: NotificationsConfig = NotificationsConfig()
    logging: LoggingConfig = LoggingConfig()


class Settings(BaseSettings):
    """Environment-based settings."""
    anthropic_api_key: str = ""
    glm_api_key: str = ""           # Also reads from ZHIPUAI_API_KEY
    zhipuai_api_key: str = ""       # Alias for glm_api_key
    github_token: str = ""
    ntfy_topic: str = "ai-architect"
    log_level: str = "INFO"

    @property
    def effective_glm_key(self) -> str:
        """Get GLM API key from either variable."""
        return self.glm_api_key or self.zhipuai_api_key

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


def load_config(config_path: str | Path = "config.yaml") -> Config:
    """
    Load configuration from YAML file.

    Args:
        config_path: Path to config.yaml file

    Returns:
        Config object with validated settings
    """
    config_path = Path(config_path)

    if not config_path.exists():
        return Config()

    with open(config_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    return Config(**data)


# Global instances
_config: Config | None = None
_settings: Settings | None = None


def get_config() -> Config:
    """Get or create configuration instance."""
    global _config
    if _config is None:
        _config = load_config()
    return _config


def get_settings() -> Settings:
    """Get or create settings instance."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def reload_config(config_path: str | Path = "config.yaml") -> Config:
    """Reload configuration from file."""
    global _config
    _config = load_config(config_path)
    return _config
