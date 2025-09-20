#!/usr/bin/env python3
"""
Tests for the retention enforcer functionality.
"""

import os
import sys
import tempfile
import time
from datetime import datetime, timedelta

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.retention import RetentionEnforcer


def test_retention_enforcer_initialization():
    """Test that RetentionEnforcer initializes correctly."""
    enforcer = RetentionEnforcer(".", 30)

    assert enforcer.base_directory == "."
    assert enforcer.retention_days == 30
    assert isinstance(enforcer.retention_threshold, datetime)

    print("✅ RetentionEnforcer initialization test passed")


def test_file_age_calculation():
    """Test file age calculation functionality."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create a test file
        test_file = os.path.join(temp_dir, "test.txt")
        with open(test_file, 'w') as f:
            f.write("test content")

        enforcer = RetentionEnforcer(temp_dir, 30)
        file_age = enforcer.get_file_age(test_file)

        # File age should be recent (within last few seconds)
        now = datetime.now()
        time_diff = (now - file_age).total_seconds()
        assert time_diff < 10, f"File age calculation seems incorrect: {time_diff} seconds"

        print("✅ File age calculation test passed")


def test_file_old_detection():
    """Test detection of old files."""
    with tempfile.TemporaryDirectory() as temp_dir:
        enforcer = RetentionEnforcer(temp_dir, 1)  # 1 day retention

        # Create a recent file
        recent_file = os.path.join(temp_dir, "recent.txt")
        with open(recent_file, 'w') as f:
            f.write("recent content")

        # Create an old file by manipulating its timestamp
        old_file = os.path.join(temp_dir, "old.txt")
        with open(old_file, 'w') as f:
            f.write("old content")

        # Set the old file's modification time to 2 days ago
        old_time = time.time() - (2 * 24 * 60 * 60)  # 2 days ago
        os.utime(old_file, (old_time, old_time))

        # Test old file detection
        assert not enforcer.is_file_old(recent_file), "Recent file should not be considered old"
        assert enforcer.is_file_old(old_file), "Old file should be considered old"

        print("✅ File old detection test passed")


def test_csv_file_discovery():
    """Test CSV file discovery functionality."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create various CSV files
        csv_files = [
            "normal.csv",
            "hmrc_export_123_2024-09-01_2024-09-30.csv",
            "test_export.csv",
            "data.csv"
        ]

        for csv_file in csv_files:
            file_path = os.path.join(temp_dir, csv_file)
            with open(file_path, 'w') as f:
                f.write("test,data\n1,2\n")

        # Create a non-CSV file
        non_csv = os.path.join(temp_dir, "not_csv.txt")
        with open(non_csv, 'w') as f:
            f.write("not csv content")

        enforcer = RetentionEnforcer(temp_dir, 30)
        found_files = enforcer.find_csv_files()

        # Should find all CSV files but not the text file
        assert len(found_files) >= len(csv_files), f"Expected at least {len(csv_files)} CSV files, found {len(found_files)}"

        # Check that all expected CSV files are found
        found_basenames = [os.path.basename(f) for f in found_files]
        for csv_file in csv_files:
            assert csv_file in found_basenames, f"CSV file {csv_file} not found in results"

        print("✅ CSV file discovery test passed")


def test_analysis_functionality():
    """Test file analysis functionality."""
    with tempfile.TemporaryDirectory() as temp_dir:
        enforcer = RetentionEnforcer(temp_dir, 1)  # 1 day retention

        # Create recent and old files
        recent_file = os.path.join(temp_dir, "recent.csv")
        with open(recent_file, 'w') as f:
            f.write("recent,data\n1,2\n")

        old_file = os.path.join(temp_dir, "old.csv")
        with open(old_file, 'w') as f:
            f.write("old,data\n3,4\n")

        # Set old file timestamp
        old_time = time.time() - (2 * 24 * 60 * 60)  # 2 days ago
        os.utime(old_file, (old_time, old_time))

        analysis = enforcer.analyze_csv_files()

        # Validate analysis structure
        required_keys = ["total_files", "old_files", "recent_files", "retention_threshold", "retention_days"]
        for key in required_keys:
            assert key in analysis, f"Analysis missing key: {key}"

        assert analysis["total_files"] == 2, f"Expected 2 total files, got {analysis['total_files']}"
        assert len(analysis["old_files"]) == 1, f"Expected 1 old file, got {len(analysis['old_files'])}"
        assert len(analysis["recent_files"]) == 1, f"Expected 1 recent file, got {len(analysis['recent_files'])}"

        # Validate file info structure
        old_file_info = analysis["old_files"][0]
        required_file_keys = ["path", "filename", "size_bytes", "modified_time", "is_old"]
        for key in required_file_keys:
            assert key in old_file_info, f"File info missing key: {key}"

        assert old_file_info["is_old"] is True, "Old file should be marked as old"

        print("✅ Analysis functionality test passed")


def test_cleanup_dry_run():
    """Test cleanup functionality in dry-run mode."""
    with tempfile.TemporaryDirectory() as temp_dir:
        enforcer = RetentionEnforcer(temp_dir, 1)  # 1 day retention

        # Create old files
        old_files = ["old1.csv", "old2.csv"]
        for old_file in old_files:
            file_path = os.path.join(temp_dir, old_file)
            with open(file_path, 'w') as f:
                f.write("old,data\n1,2\n")

            # Set old timestamp
            old_time = time.time() - (2 * 24 * 60 * 60)  # 2 days ago
            os.utime(file_path, (old_time, old_time))

        # Run dry-run cleanup
        results = enforcer.cleanup_old_files(dry_run=True)

        # Validate results structure
        required_keys = ["dry_run", "files_processed", "files_deleted", "errors", "deleted_files", "total_size_freed_bytes"]
        for key in required_keys:
            assert key in results, f"Results missing key: {key}"

        assert results["dry_run"] is True, "Should be in dry-run mode"
        assert results["files_processed"] == 2, f"Expected 2 files processed, got {results['files_processed']}"
        assert results["files_deleted"] == 2, f"Expected 2 files would be deleted, got {results['files_deleted']}"

        # Files should still exist in dry-run mode
        for old_file in old_files:
            file_path = os.path.join(temp_dir, old_file)
            assert os.path.exists(file_path), f"File {old_file} should still exist after dry-run"

        print("✅ Cleanup dry-run test passed")


def test_cleanup_actual_deletion():
    """Test actual file deletion functionality."""
    with tempfile.TemporaryDirectory() as temp_dir:
        enforcer = RetentionEnforcer(temp_dir, 1)  # 1 day retention

        # Create old files
        old_files = ["old1.csv", "old2.csv"]
        for old_file in old_files:
            file_path = os.path.join(temp_dir, old_file)
            with open(file_path, 'w') as f:
                f.write("old,data\n1,2\n")

            # Set old timestamp
            old_time = time.time() - (2 * 24 * 60 * 60)  # 2 days ago
            os.utime(file_path, (old_time, old_time))

        # Create a recent file that should not be deleted
        recent_file = os.path.join(temp_dir, "recent.csv")
        with open(recent_file, 'w') as f:
            f.write("recent,data\n1,2\n")

        # Run actual cleanup
        results = enforcer.cleanup_old_files(dry_run=False)

        assert results["dry_run"] is False, "Should not be in dry-run mode"
        assert results["files_processed"] == 2, f"Expected 2 files processed, got {results['files_processed']}"
        assert results["files_deleted"] == 2, f"Expected 2 files deleted, got {results['files_deleted']}"

        # Old files should be deleted
        for old_file in old_files:
            file_path = os.path.join(temp_dir, old_file)
            assert not os.path.exists(file_path), f"File {old_file} should be deleted"

        # Recent file should still exist
        assert os.path.exists(recent_file), "Recent file should not be deleted"

        print("✅ Cleanup actual deletion test passed")


def test_deletion_test_functionality():
    """Test the deletion test functionality."""
    with tempfile.TemporaryDirectory() as temp_dir:
        enforcer = RetentionEnforcer(temp_dir, 30)

        # Run deletion test
        success = enforcer.test_deletion()

        assert success is True, "Deletion test should succeed"

        # Ensure test file was cleaned up
        test_file = os.path.join(temp_dir, "retention_test_file.tmp")
        assert not os.path.exists(test_file), "Test file should be cleaned up"

        print("✅ Deletion test functionality passed")


def test_report_generation():
    """Test report generation functionality."""
    with tempfile.TemporaryDirectory() as temp_dir:
        enforcer = RetentionEnforcer(temp_dir, 7)  # 7 day retention

        # Create some test files
        test_files = ["file1.csv", "file2.csv"]
        for test_file in test_files:
            file_path = os.path.join(temp_dir, test_file)
            with open(file_path, 'w') as f:
                f.write("test,data\n1,2\n")

        report = enforcer.generate_report()

        # Validate report content
        assert "CSV File Retention Report" in report
        assert "Base Directory:" in report
        assert "Retention Period: 7 days" in report
        assert "Total CSV files found:" in report
        assert "file1.csv" in report or "file2.csv" in report

        print("✅ Report generation test passed")


if __name__ == "__main__":
    print("🧪 Running retention enforcer tests...\n")

    try:
        test_retention_enforcer_initialization()
        test_file_age_calculation()
        test_file_old_detection()
        test_csv_file_discovery()
        test_analysis_functionality()
        test_cleanup_dry_run()
        test_cleanup_actual_deletion()
        test_deletion_test_functionality()
        test_report_generation()

        print("\n🎉 All retention enforcer tests passed!")
        sys.exit(0)
    except Exception as e:
        print(f"\n💥 Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
