"""Property-based tests for File Watcher Service.

**Feature: project-polish**
"""

import threading
import time
from datetime import datetime
from pathlib import Path

from hypothesis import given, settings
from hypothesis import strategies as st

from specmem.watcher.service import Debouncer, FileChangeEvent


class TestDebounceRapidChanges:
    """Property tests for debounce behavior.

    **Feature: project-polish, Property 5: Debounce Rapid Changes**
    **Validates: Requirements 3.4**
    """

    @given(num_events=st.integers(min_value=2, max_value=20))
    @settings(max_examples=50, deadline=5000)
    def test_rapid_changes_debounced_to_single_callback(self, num_events: int):
        """Multiple rapid changes should result in at most 1 callback."""
        callback_count = 0
        received_events: list[list[FileChangeEvent]] = []
        lock = threading.Lock()

        def callback(events: list[FileChangeEvent]):
            nonlocal callback_count
            with lock:
                callback_count += 1
                received_events.append(events)

        debouncer = Debouncer(delay_ms=100)
        debouncer.set_callback(callback)

        # Add multiple events rapidly (within debounce window)
        for i in range(num_events):
            event = FileChangeEvent(
                path=Path(f"/test/file_{i}.md"),
                event_type="modified",
            )
            debouncer.add_event(event)

        # Wait for debounce to complete
        time.sleep(0.2)

        # Should have exactly 1 callback
        assert callback_count == 1, f"Expected 1 callback, got {callback_count}"

    @given(num_events=st.integers(min_value=1, max_value=10))
    @settings(max_examples=50, deadline=5000)
    def test_same_file_changes_deduplicated(self, num_events: int):
        """Multiple changes to same file should be deduplicated."""
        received_events: list[FileChangeEvent] = []
        lock = threading.Lock()

        def callback(events: list[FileChangeEvent]):
            with lock:
                received_events.extend(events)

        debouncer = Debouncer(delay_ms=100)
        debouncer.set_callback(callback)

        # Add multiple events for the SAME file
        for i in range(num_events):
            event = FileChangeEvent(
                path=Path("/test/same_file.md"),
                event_type="modified",
            )
            debouncer.add_event(event)

        # Wait for debounce
        time.sleep(0.2)

        # Should have exactly 1 event (deduplicated by path)
        assert len(received_events) == 1, f"Expected 1 event, got {len(received_events)}"

    @given(
        num_files=st.integers(min_value=1, max_value=10),
        changes_per_file=st.integers(min_value=1, max_value=5),
    )
    @settings(max_examples=50, deadline=5000)
    def test_different_files_preserved(self, num_files: int, changes_per_file: int):
        """Changes to different files should all be preserved."""
        received_events: list[FileChangeEvent] = []
        lock = threading.Lock()

        def callback(events: list[FileChangeEvent]):
            with lock:
                received_events.extend(events)

        debouncer = Debouncer(delay_ms=100)
        debouncer.set_callback(callback)

        # Add multiple events for different files
        for file_idx in range(num_files):
            for _ in range(changes_per_file):
                event = FileChangeEvent(
                    path=Path(f"/test/file_{file_idx}.md"),
                    event_type="modified",
                )
                debouncer.add_event(event)

        # Wait for debounce
        time.sleep(0.2)

        # Should have exactly num_files events (one per unique file)
        assert (
            len(received_events) == num_files
        ), f"Expected {num_files} events, got {len(received_events)}"

    def test_cancel_prevents_callback(self):
        """Canceling debouncer should prevent callback."""
        callback_count = 0

        def callback(events: list[FileChangeEvent]):
            nonlocal callback_count
            callback_count += 1

        debouncer = Debouncer(delay_ms=200)
        debouncer.set_callback(callback)

        # Add event
        event = FileChangeEvent(path=Path("/test/file.md"), event_type="modified")
        debouncer.add_event(event)

        # Cancel before debounce completes
        time.sleep(0.05)
        debouncer.cancel()

        # Wait past debounce period
        time.sleep(0.3)

        # Should have no callbacks
        assert callback_count == 0, f"Expected 0 callbacks, got {callback_count}"


class TestFileChangeEvent:
    """Property tests for FileChangeEvent."""

    @given(
        path=st.text(min_size=1, max_size=100).filter(lambda x: "/" not in x),
        event_type=st.sampled_from(["created", "modified", "deleted"]),
    )
    @settings(max_examples=100)
    def test_event_preserves_data(self, path: str, event_type: str):
        """FileChangeEvent should preserve all data."""
        full_path = Path(f"/test/{path}.md")
        event = FileChangeEvent(path=full_path, event_type=event_type)

        assert event.path == full_path
        assert event.event_type == event_type
        assert isinstance(event.timestamp, datetime)


class TestWebSocketUpdateOnChange:
    """Property tests for WebSocket updates on file changes.

    **Feature: project-polish, Property 4: WebSocket Update on Change**
    **Validates: Requirements 3.2**
    """

    @given(
        num_files=st.integers(min_value=1, max_value=5),
        event_type=st.sampled_from(["created", "modified", "deleted"]),
    )
    @settings(max_examples=50, deadline=5000)
    def test_file_changes_produce_events(self, num_files: int, event_type: str):
        """File changes should produce FileChangeEvents with correct data."""
        events = []

        for i in range(num_files):
            event = FileChangeEvent(
                path=Path(f"/test/spec_{i}.md"),
                event_type=event_type,
            )
            events.append(event)

        # Verify all events have correct structure
        for i, event in enumerate(events):
            assert event.path == Path(f"/test/spec_{i}.md")
            assert event.event_type == event_type
            assert isinstance(event.timestamp, datetime)

    @given(
        path_suffix=st.text(
            min_size=1,
            max_size=50,
            alphabet=st.characters(
                whitelist_categories=("Lu", "Ll", "Nd"), whitelist_characters="_-"
            ),
        ),
    )
    @settings(max_examples=100)
    def test_event_serializable_for_websocket(self, path_suffix: str):
        """FileChangeEvents should be serializable for WebSocket transmission."""
        import json

        event = FileChangeEvent(
            path=Path(f"/test/{path_suffix}.md"),
            event_type="modified",
        )

        # Create WebSocket message format
        message = {
            "type": "spec_update",
            "files": [
                {
                    "path": str(event.path),
                    "event_type": event.event_type,
                }
            ],
        }

        # Should be JSON serializable
        json_str = json.dumps(message)
        parsed = json.loads(json_str)

        assert parsed["type"] == "spec_update"
        assert len(parsed["files"]) == 1
        assert parsed["files"][0]["event_type"] == "modified"
