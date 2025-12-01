"""Unit tests for CLI commands."""

import tempfile
from pathlib import Path

from typer.testing import CliRunner

from specmem.cli.main import app


runner = CliRunner()


class TestVersionCommand:
    """Tests for version command."""

    def test_version_shows_version(self) -> None:
        """Version command should display version."""
        result = runner.invoke(app, ["version"])
        assert result.exit_code == 0
        assert "SpecMem version" in result.stdout


class TestInitCommand:
    """Tests for init command."""

    def test_init_creates_config(self) -> None:
        """Init should create .specmem.toml config file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = runner.invoke(app, ["init", tmpdir])
            assert result.exit_code == 0
            assert "Initialized SpecMem" in result.stdout

            config_path = Path(tmpdir) / ".specmem.toml"
            assert config_path.exists()

    def test_init_fails_if_config_exists(self) -> None:
        """Init should fail if config already exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create existing config
            config_path = Path(tmpdir) / ".specmem.toml"
            config_path.write_text("[embedding]\nprovider = 'local'\n")

            result = runner.invoke(app, ["init", tmpdir])
            assert result.exit_code == 1
            assert "already exists" in result.stdout


class TestScanCommand:
    """Tests for scan command."""

    def test_scan_no_specs_found(self) -> None:
        """Scan should report when no specs found."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = runner.invoke(app, ["scan", tmpdir])
            assert result.exit_code == 1
            assert "No specification frameworks detected" in result.stdout

    def test_scan_finds_kiro_specs(self) -> None:
        """Scan should detect Kiro specs."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create Kiro spec structure
            spec_dir = Path(tmpdir) / ".kiro" / "specs" / "test-feature"
            spec_dir.mkdir(parents=True)
            (spec_dir / "requirements.md").write_text(
                "# Requirements\n\n### Requirement 1\n\n**User Story:** Test story\n"
            )

            result = runner.invoke(app, ["scan", tmpdir])
            assert result.exit_code == 0
            assert "Detected" in result.stdout
            assert "Kiro" in result.stdout


class TestInfoCommand:
    """Tests for info command."""

    def test_info_no_data(self) -> None:
        """Info should report when no data exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = runner.invoke(app, ["info", tmpdir])
            assert result.exit_code == 1
            assert "No SpecMem data found" in result.stdout


class TestQueryCommand:
    """Tests for query command."""

    def test_query_no_data(self) -> None:
        """Query should report when no data exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create empty config
            config_path = Path(tmpdir) / ".specmem.toml"
            config_path.write_text("[embedding]\nprovider = 'local'\n")

            # Create vectordb path
            vectordb_path = Path(tmpdir) / ".specmem" / "vectordb"
            vectordb_path.mkdir(parents=True)

            result = runner.invoke(app, ["query", "test query", "--path", tmpdir])
            assert result.exit_code == 1
            assert "No data in memory" in result.stdout


class TestVerboseFlag:
    """Tests for verbose flag."""

    def test_verbose_flag_accepted(self) -> None:
        """Verbose flag should be accepted."""
        result = runner.invoke(app, ["--verbose", "version"])
        assert result.exit_code == 0
        assert "SpecMem version" in result.stdout

    def test_short_verbose_flag(self) -> None:
        """Short verbose flag should work."""
        result = runner.invoke(app, ["-v", "version"])
        assert result.exit_code == 0


class TestServeCommand:
    """Tests for serve command."""

    def test_serve_no_specs_found(self) -> None:
        """Serve should report when no specs found."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = runner.invoke(app, ["serve", tmpdir])
            assert result.exit_code == 1
            assert "No specification frameworks detected" in result.stdout

    def test_serve_accepts_port_option(self) -> None:
        """Serve should accept --port option."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Just test that the option is accepted (will fail due to no specs)
            result = runner.invoke(app, ["serve", tmpdir, "--port", "9000"])
            assert result.exit_code == 1
            assert "No specification frameworks detected" in result.stdout

    def test_serve_accepts_short_port_option(self) -> None:
        """Serve should accept -p short option."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = runner.invoke(app, ["serve", tmpdir, "-p", "9000"])
            assert result.exit_code == 1
            assert "No specification frameworks detected" in result.stdout

    def test_serve_help_shows_description(self) -> None:
        """Serve help should show command description."""
        result = runner.invoke(app, ["serve", "--help"])
        assert result.exit_code == 0
        assert "Web UI" in result.stdout or "web server" in result.stdout.lower()


class TestGraphCommands:
    """Tests for graph subcommands."""

    def test_graph_help(self) -> None:
        """Graph help should show available commands."""
        result = runner.invoke(app, ["graph", "--help"])
        assert result.exit_code == 0
        assert "impact" in result.stdout
        assert "show" in result.stdout
        assert "export" in result.stdout
        assert "stats" in result.stdout

    def test_graph_stats_no_graph(self) -> None:
        """Graph stats should report when no graph exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = runner.invoke(app, ["graph", "stats", "--path", tmpdir])
            assert result.exit_code == 1
            assert "No impact graph found" in result.stdout

    def test_graph_show_no_graph(self) -> None:
        """Graph show should report when no graph exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = runner.invoke(app, ["graph", "show", "spec:test", "--path", tmpdir])
            assert result.exit_code == 1
            assert "No impact graph found" in result.stdout

    def test_graph_export_no_graph(self) -> None:
        """Graph export should report when no graph exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = runner.invoke(app, ["graph", "export", "--path", tmpdir])
            assert result.exit_code == 1
            assert "No impact graph found" in result.stdout

    def test_graph_impact_builds_graph(self) -> None:
        """Graph impact should build graph if not exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a simple spec
            spec_dir = Path(tmpdir) / ".kiro" / "specs" / "test-feature"
            spec_dir.mkdir(parents=True)
            (spec_dir / "requirements.md").write_text(
                "# Requirements\n\n### Requirement 1\n\n**User Story:** Test story\n"
            )

            result = runner.invoke(app, ["graph", "impact", "test.py", "--path", tmpdir])
            # Should succeed (even if no impact found)
            assert "Impact Analysis" in result.stdout or "Building impact graph" in result.stdout

    def test_graph_stats_with_graph(self) -> None:
        """Graph stats should show statistics when graph exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create graph file
            specmem_dir = Path(tmpdir) / ".specmem"
            specmem_dir.mkdir(parents=True)
            graph_path = specmem_dir / "impact_graph.json"
            graph_path.write_text('{"nodes": [], "edges": []}')

            result = runner.invoke(app, ["graph", "stats", "--path", tmpdir])
            assert result.exit_code == 0
            assert "Statistics" in result.stdout
            assert "Total Nodes" in result.stdout

    def test_graph_export_json_format(self) -> None:
        """Graph export should output JSON format."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create graph file
            specmem_dir = Path(tmpdir) / ".specmem"
            specmem_dir.mkdir(parents=True)
            graph_path = specmem_dir / "impact_graph.json"
            graph_path.write_text('{"nodes": [], "edges": []}')

            result = runner.invoke(app, ["graph", "export", "--format", "json", "--path", tmpdir])
            assert result.exit_code == 0
            assert '"nodes"' in result.stdout
            assert '"edges"' in result.stdout

    def test_graph_export_dot_format(self) -> None:
        """Graph export should output DOT format."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create graph file
            specmem_dir = Path(tmpdir) / ".specmem"
            specmem_dir.mkdir(parents=True)
            graph_path = specmem_dir / "impact_graph.json"
            graph_path.write_text('{"nodes": [], "edges": []}')

            result = runner.invoke(app, ["graph", "export", "--format", "dot", "--path", tmpdir])
            assert result.exit_code == 0
            assert "digraph" in result.stdout

    def test_graph_export_mermaid_format(self) -> None:
        """Graph export should output Mermaid format."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create graph file
            specmem_dir = Path(tmpdir) / ".specmem"
            specmem_dir.mkdir(parents=True)
            graph_path = specmem_dir / "impact_graph.json"
            graph_path.write_text('{"nodes": [], "edges": []}')

            result = runner.invoke(
                app, ["graph", "export", "--format", "mermaid", "--path", tmpdir]
            )
            assert result.exit_code == 0
            assert "graph" in result.stdout


class TestSpecDiffCommands:
    """Tests for SpecDiff CLI commands (diff, history, drift, stale, deprecations)."""

    def test_diff_no_history(self) -> None:
        """Diff should report when no history exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = runner.invoke(app, ["diff", "test.spec", "--path", tmpdir])
            assert result.exit_code == 1
            assert "No SpecDiff history found" in result.stdout

    def test_diff_with_history(self) -> None:
        """Diff should show changes when history exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            from specmem.core.specir import SpecBlock, SpecType
            from specmem.diff import SpecDiff

            # Create specdiff database with history
            specmem_dir = Path(tmpdir) / ".specmem"
            specmem_dir.mkdir(parents=True)
            db_path = specmem_dir / "specdiff.db"

            diff = SpecDiff(db_path)
            spec1 = SpecBlock(
                id="test.spec",
                type=SpecType.REQUIREMENT,
                text="Original content",
                source="test.md",
            )
            spec2 = SpecBlock(
                id="test.spec",
                type=SpecType.REQUIREMENT,
                text="Modified content",
                source="test.md",
            )
            diff.track_version(spec1, commit_ref="v1")
            diff.track_version(spec2, commit_ref="v2")
            diff.close()

            result = runner.invoke(app, ["diff", "test.spec", "--path", tmpdir])
            assert result.exit_code == 0
            assert "Spec Diff" in result.stdout
            assert "test.spec" in result.stdout

    def test_diff_no_changes(self) -> None:
        """Diff should report when no changes found."""
        with tempfile.TemporaryDirectory() as tmpdir:
            from specmem.core.specir import SpecBlock, SpecType
            from specmem.diff import SpecDiff

            specmem_dir = Path(tmpdir) / ".specmem"
            specmem_dir.mkdir(parents=True)
            db_path = specmem_dir / "specdiff.db"

            diff = SpecDiff(db_path)
            spec = SpecBlock(
                id="test.spec",
                type=SpecType.REQUIREMENT,
                text="Content",
                source="test.md",
            )
            diff.track_version(spec, commit_ref="v1")
            diff.close()

            result = runner.invoke(app, ["diff", "test.spec", "--path", tmpdir])
            assert result.exit_code == 0
            assert "No changes found" in result.stdout

    def test_history_no_data(self) -> None:
        """History should report when no history exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = runner.invoke(app, ["history", "test.spec", "--path", tmpdir])
            assert result.exit_code == 1
            assert "No SpecDiff history found" in result.stdout

    def test_history_with_versions(self) -> None:
        """History should show version timeline."""
        with tempfile.TemporaryDirectory() as tmpdir:
            from specmem.core.specir import SpecBlock, SpecType
            from specmem.diff import SpecDiff

            specmem_dir = Path(tmpdir) / ".specmem"
            specmem_dir.mkdir(parents=True)
            db_path = specmem_dir / "specdiff.db"

            diff = SpecDiff(db_path)
            for i in range(3):
                spec = SpecBlock(
                    id="test.spec",
                    type=SpecType.REQUIREMENT,
                    text=f"Content version {i}",
                    source="test.md",
                )
                diff.track_version(spec, commit_ref=f"v{i}")
            diff.close()

            result = runner.invoke(app, ["history", "test.spec", "--path", tmpdir])
            assert result.exit_code == 0
            assert "Version History" in result.stdout
            assert "test.spec" in result.stdout
            assert "v0" in result.stdout
            assert "v1" in result.stdout
            assert "v2" in result.stdout

    def test_history_limit_option(self) -> None:
        """History should respect --limit option."""
        with tempfile.TemporaryDirectory() as tmpdir:
            from specmem.core.specir import SpecBlock, SpecType
            from specmem.diff import SpecDiff

            specmem_dir = Path(tmpdir) / ".specmem"
            specmem_dir.mkdir(parents=True)
            db_path = specmem_dir / "specdiff.db"

            diff = SpecDiff(db_path)
            for i in range(5):
                spec = SpecBlock(
                    id="test.spec",
                    type=SpecType.REQUIREMENT,
                    text=f"Content version {i}",
                    source="test.md",
                )
                diff.track_version(spec, commit_ref=f"v{i}")
            diff.close()

            result = runner.invoke(app, ["history", "test.spec", "--limit", "2", "--path", tmpdir])
            assert result.exit_code == 0
            assert "2 versions" in result.stdout

    def test_drift_no_history(self) -> None:
        """Drift should report when no history exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = runner.invoke(app, ["drift", "--path", tmpdir])
            assert result.exit_code == 1
            assert "No SpecDiff history found" in result.stdout

    def test_drift_no_drift_detected(self) -> None:
        """Drift should report when no drift detected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            from specmem.core.specir import SpecBlock, SpecType
            from specmem.diff import SpecDiff

            specmem_dir = Path(tmpdir) / ".specmem"
            specmem_dir.mkdir(parents=True)
            db_path = specmem_dir / "specdiff.db"

            diff = SpecDiff(db_path)
            spec = SpecBlock(
                id="test.spec",
                type=SpecType.REQUIREMENT,
                text="Content",
                source="test.md",
            )
            diff.track_version(spec, commit_ref="v1")
            diff.close()

            result = runner.invoke(app, ["drift", "--path", tmpdir])
            assert result.exit_code == 0
            assert "No code drift detected" in result.stdout

    def test_drift_severity_filter(self) -> None:
        """Drift should accept --severity filter."""
        with tempfile.TemporaryDirectory() as tmpdir:
            from specmem.diff import SpecDiff

            specmem_dir = Path(tmpdir) / ".specmem"
            specmem_dir.mkdir(parents=True)
            db_path = specmem_dir / "specdiff.db"

            diff = SpecDiff(db_path)
            diff.close()

            result = runner.invoke(app, ["drift", "--severity", "0.5", "--path", tmpdir])
            assert result.exit_code == 0

    def test_stale_no_history(self) -> None:
        """Stale should report when no history exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = runner.invoke(app, ["stale", "--path", tmpdir])
            assert result.exit_code == 1
            assert "No SpecDiff history found" in result.stdout

    def test_stale_acknowledge_option(self) -> None:
        """Stale should accept --acknowledge option."""
        with tempfile.TemporaryDirectory() as tmpdir:
            from specmem.core.specir import SpecBlock, SpecType
            from specmem.diff import SpecDiff

            specmem_dir = Path(tmpdir) / ".specmem"
            specmem_dir.mkdir(parents=True)
            db_path = specmem_dir / "specdiff.db"

            diff = SpecDiff(db_path)
            spec = SpecBlock(
                id="test.spec",
                type=SpecType.REQUIREMENT,
                text="Content",
                source="test.md",
            )
            diff.track_version(spec, commit_ref="v1")
            diff.close()

            result = runner.invoke(
                app, ["stale", "--acknowledge", "test.spec:v1", "--path", tmpdir]
            )
            assert result.exit_code == 0
            assert "Acknowledged staleness" in result.stdout

    def test_stale_invalid_acknowledge_format(self) -> None:
        """Stale should reject invalid acknowledge format."""
        with tempfile.TemporaryDirectory() as tmpdir:
            from specmem.diff import SpecDiff

            specmem_dir = Path(tmpdir) / ".specmem"
            specmem_dir.mkdir(parents=True)
            db_path = specmem_dir / "specdiff.db"

            diff = SpecDiff(db_path)
            diff.close()

            result = runner.invoke(app, ["stale", "--acknowledge", "invalid", "--path", tmpdir])
            assert result.exit_code == 0
            assert "Invalid format" in result.stdout

    def test_deprecations_no_history(self) -> None:
        """Deprecations should report when no history exists."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = runner.invoke(app, ["deprecations", "--path", tmpdir])
            assert result.exit_code == 1
            assert "No SpecDiff history found" in result.stdout

    def test_deprecations_none_found(self) -> None:
        """Deprecations should report when none found."""
        with tempfile.TemporaryDirectory() as tmpdir:
            from specmem.diff import SpecDiff

            specmem_dir = Path(tmpdir) / ".specmem"
            specmem_dir.mkdir(parents=True)
            db_path = specmem_dir / "specdiff.db"

            diff = SpecDiff(db_path)
            diff.close()

            result = runner.invoke(app, ["deprecations", "--path", tmpdir])
            assert result.exit_code == 0
            assert "No deprecated specifications" in result.stdout

    def test_deprecations_with_data(self) -> None:
        """Deprecations should list deprecated specs."""
        with tempfile.TemporaryDirectory() as tmpdir:
            from specmem.diff import SpecDiff

            specmem_dir = Path(tmpdir) / ".specmem"
            specmem_dir.mkdir(parents=True)
            db_path = specmem_dir / "specdiff.db"

            diff = SpecDiff(db_path)
            diff.deprecate_spec(
                spec_id="old.spec",
                urgency=0.8,
            )
            diff.close()

            result = runner.invoke(app, ["deprecations", "--path", tmpdir])
            assert result.exit_code == 0
            assert "Deprecated Specifications" in result.stdout
            assert "old.spec" in result.stdout

    def test_deprecations_expired_option(self) -> None:
        """Deprecations should accept --expired option."""
        with tempfile.TemporaryDirectory() as tmpdir:
            from specmem.diff import SpecDiff

            specmem_dir = Path(tmpdir) / ".specmem"
            specmem_dir.mkdir(parents=True)
            db_path = specmem_dir / "specdiff.db"

            diff = SpecDiff(db_path)
            diff.close()

            result = runner.invoke(app, ["deprecations", "--expired", "--path", tmpdir])
            assert result.exit_code == 0

    def test_diff_help(self) -> None:
        """Diff help should show command description."""
        result = runner.invoke(app, ["diff", "--help"])
        assert result.exit_code == 0
        assert "changes" in result.stdout.lower()

    def test_history_help(self) -> None:
        """History help should show command description."""
        result = runner.invoke(app, ["history", "--help"])
        assert result.exit_code == 0
        assert "timeline" in result.stdout.lower() or "version" in result.stdout.lower()

    def test_drift_help(self) -> None:
        """Drift help should show command description."""
        result = runner.invoke(app, ["drift", "--help"])
        assert result.exit_code == 0
        assert "drift" in result.stdout.lower()

    def test_stale_help(self) -> None:
        """Stale help should show command description."""
        result = runner.invoke(app, ["stale", "--help"])
        assert result.exit_code == 0
        assert "stale" in result.stdout.lower()

    def test_deprecations_help(self) -> None:
        """Deprecations help should show command description."""
        result = runner.invoke(app, ["deprecations", "--help"])
        assert result.exit_code == 0
        assert "deprecated" in result.stdout.lower()
