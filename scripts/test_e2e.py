#!/usr/bin/env python3
"""
AI Architect v2 - End-to-End Test

Verifies the complete pipeline runs without errors.
"""

import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_imports():
    """Test all imports work."""
    print("Testing imports...")

    from src.collectors.base import CollectedItem, SourceType
    from src.collectors.blogs import BlogsCollector
    from src.collectors.docs import DocsCollector
    from src.collectors.github_emerging import GitHubEmergingCollector
    from src.collectors.github_repos import GitHubReposCollector
    from src.collectors.github_signals import GitHubSignalsCollector
    from src.collectors.stackoverflow import StackOverflowCollector

    from src.processors.analyzer import Analyzer
    from src.processors.claude_client import ClaudeClient
    from src.processors.novelty_detector import NoveltyDetector
    from src.processors.signal_ranker import SignalRanker
    from src.processors.synthesizer import Synthesizer

    from src.storage.markdown_gen import MarkdownGenerator
    from src.storage.vector_store import VectorStore

    from src.utils.config import get_config, load_config
    from src.utils.logger import configure_logging, get_logger
    from src.utils.notifier import Notifier

    print("✓ All imports successful")
    return True


def test_config():
    """Test configuration loading."""
    print("\nTesting configuration...")

    from src.utils.config import load_config, get_settings

    config = load_config()
    assert config.mode == "daily"
    assert config.models.analysis == "claude-sonnet-4-20250514"
    assert config.thresholds.signal_score_min == 4

    settings = get_settings()
    # API key should be in .env
    print(f"  API Key set: {'Yes' if settings.anthropic_api_key else 'No (will fail at runtime)'}")

    print("✓ Configuration loaded successfully")
    return True


def test_directory_structure():
    """Test required directories exist."""
    print("\nTesting directory structure...")

    required_dirs = [
        "src/collectors",
        "src/processors",
        "src/storage",
        "src/utils",
        "output/daily",
        "output/weekly",
        "output/monthly",
        "data/snapshots",
    ]

    for dir_path in required_dirs:
        p = Path(dir_path)
        if not p.exists():
            print(f"  ✗ Missing: {dir_path}")
            return False

    print("✓ All directories exist")
    return True


def test_collected_item():
    """Test CollectedItem creation and serialization."""
    print("\nTesting CollectedItem...")

    from datetime import datetime, timezone
    from src.collectors.base import CollectedItem, SourceType

    item = CollectedItem(
        id="test_123",
        source_type=SourceType.DOCS,
        source_url="https://example.com",
        title="Test Item",
        content="This is test content for the item.",
        author="Test Author",
        published_at=datetime.now(timezone.utc),
    )

    # Test to_dict
    d = item.to_dict()
    assert d["title"] == "Test Item"
    assert d["source_type"] == "docs"

    # Test to_json
    j = item.to_json()
    assert '"title": "Test Item"' in j

    print("✓ CollectedItem works correctly")
    return True


def test_vector_store():
    """Test ChromaDB vector store."""
    print("\nTesting VectorStore...")

    from src.storage.vector_store import VectorStore

    store = VectorStore(persist_directory="data/chromadb_test")

    # Add a test document
    store.add(
        collection="items",
        documents=["Test document for vector search"],
        ids=["test_doc_1"],
        metadatas=[{"source": "test"}],
    )

    # Search
    results = store.search(
        query="test document",
        collection="items",
        n_results=1,
    )

    assert len(results.get("ids", [[]])[0]) == 1

    # Clean up
    store.delete(collection="items", ids=["test_doc_1"])

    print("✓ VectorStore works correctly")
    return True


def test_markdown_generator():
    """Test markdown generation."""
    print("\nTesting MarkdownGenerator...")

    from datetime import datetime, timezone
    from src.collectors.base import CollectedItem, SourceType
    from src.processors.synthesizer import DailySynthesis
    from src.storage.markdown_gen import MarkdownGenerator

    gen = MarkdownGenerator(output_dir="output_test")

    # Create test synthesis
    synthesis = DailySynthesis(
        date="2026-02-17",
        relevance_score=7,
        highlights=["Test highlight 1", "Test highlight 2"],
        patterns=["Pattern 1"],
        recommendations=["Recommendation 1"],
        key_changes=["Change 1"],
        summary="This is a test summary.",
    )

    # Create test items
    items = [
        (
            CollectedItem(
                id="test_1",
                source_type=SourceType.DOCS,
                source_url="https://example.com/1",
                title="Test Item 1",
                content="Content 1",
            ),
            None,
        ),
    ]

    # Generate
    path = gen.generate_daily(synthesis, items)
    assert path.exists()

    # Clean up
    path.unlink()
    import shutil
    shutil.rmtree("output_test", ignore_errors=True)

    print("✓ MarkdownGenerator works correctly")
    return True


def test_notifier():
    """Test notifier initialization."""
    print("\nTesting Notifier...")

    from src.utils.notifier import Notifier

    # Create with notifications disabled
    notifier = Notifier(topic="ai-architect-test", enabled=False)

    # Should not actually send (disabled)
    result = notifier.send("Test message", title="Test")
    assert result is False  # Returns False because disabled

    print("✓ Notifier initialized correctly")
    return True


def run_all_tests():
    """Run all tests."""
    print("=" * 50)
    print("AI Architect v2 - End-to-End Test")
    print("=" * 50)

    tests = [
        test_imports,
        test_config,
        test_directory_structure,
        test_collected_item,
        test_vector_store,
        test_markdown_generator,
        test_notifier,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"  ✗ Error: {e}")
            failed += 1

    print("\n" + "=" * 50)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 50)

    return failed == 0


if __name__ == "__main__":
    # Configure logging for tests
    from src.utils.logger import configure_logging
    configure_logging()

    success = run_all_tests()
    sys.exit(0 if success else 1)
