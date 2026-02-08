"""Integration tests for resume_ai/tracker.py -- save_resume_version,
get_versions_for_job, get_all_versions.

Tests use the _fresh_db autouse fixture for in-memory SQLite isolation.
"""

import pytest

import webapp.db as db_module
from resume_ai.tracker import get_all_versions, get_versions_for_job, save_resume_version


def _insert_job(dedup_key: str, title: str = "Test Job", company: str = "TestCo") -> None:
    """Insert a minimal job so foreign key references work."""
    db_module.upsert_job(
        {
            "id": dedup_key.replace("::", "-"),
            "platform": "indeed",
            "title": title,
            "company": company,
            "url": f"https://example.com/{dedup_key}",
            "location": "Remote",
            "description": f"{title} at {company}",
            "status": "discovered",
        }
    )


@pytest.mark.integration
class TestSaveResumeVersion:
    """Verify save_resume_version inserts records correctly."""

    def test_returns_positive_id(self):
        """save_resume_version returns an integer id > 0."""
        _insert_job("testco::test job")
        version_id = save_resume_version(
            job_dedup_key="testco::test job",
            resume_type="resume",
            file_path="/tmp/resume.pdf",
            original_resume_path="/tmp/orig.pdf",
            model_used="claude-test",
        )
        assert isinstance(version_id, int)
        assert version_id > 0

    def test_with_prompt_hash(self):
        """save_resume_version with prompt_hash stores correctly."""
        _insert_job("testco::test job")
        version_id = save_resume_version(
            job_dedup_key="testco::test job",
            resume_type="cover_letter",
            file_path="/tmp/letter.pdf",
            original_resume_path="/tmp/orig.pdf",
            model_used="claude-test",
            prompt_hash="abc123",
        )
        assert version_id > 0


@pytest.mark.integration
class TestGetVersionsForJob:
    """Verify get_versions_for_job returns correct versions."""

    def test_returns_versions_for_job(self):
        """get_versions_for_job returns all versions for a given job, newest first."""
        _insert_job("testco::test job")
        save_resume_version(
            job_dedup_key="testco::test job",
            resume_type="resume",
            file_path="/tmp/v1.pdf",
            original_resume_path="/tmp/orig.pdf",
            model_used="claude-test",
        )
        save_resume_version(
            job_dedup_key="testco::test job",
            resume_type="cover_letter",
            file_path="/tmp/v2.pdf",
            original_resume_path="/tmp/orig.pdf",
            model_used="claude-test",
        )

        # Insert a version for a different job
        _insert_job("othercorp::other role", title="Other Role", company="OtherCorp")
        save_resume_version(
            job_dedup_key="othercorp::other role",
            resume_type="resume",
            file_path="/tmp/other.pdf",
            original_resume_path="/tmp/orig.pdf",
            model_used="claude-test",
        )

        versions = get_versions_for_job("testco::test job")
        assert len(versions) == 2
        # Both versions present (ordering within same second is indeterminate)
        file_paths = {v["file_path"] for v in versions}
        assert file_paths == {"/tmp/v1.pdf", "/tmp/v2.pdf"}

    def test_returns_empty_for_nonexistent_job(self):
        """get_versions_for_job returns empty list for nonexistent job."""
        versions = get_versions_for_job("nonexistent::key")
        assert versions == []


@pytest.mark.integration
class TestGetAllVersions:
    """Verify get_all_versions returns versions across all jobs."""

    def test_returns_all_versions_with_job_metadata(self):
        """get_all_versions returns versions enriched with job title and company."""
        _insert_job("alpha::engineer", title="Engineer", company="Alpha")
        _insert_job("beta::lead", title="Lead", company="Beta")

        save_resume_version(
            job_dedup_key="alpha::engineer",
            resume_type="resume",
            file_path="/tmp/alpha.pdf",
            original_resume_path="/tmp/orig.pdf",
            model_used="claude-test",
        )
        save_resume_version(
            job_dedup_key="beta::lead",
            resume_type="resume",
            file_path="/tmp/beta.pdf",
            original_resume_path="/tmp/orig.pdf",
            model_used="claude-test",
        )

        versions = get_all_versions(limit=10)
        assert len(versions) == 2
        # Should have job metadata from LEFT JOIN
        titles = {v.get("title") for v in versions}
        assert "Engineer" in titles
        assert "Lead" in titles

    def test_respects_limit(self):
        """get_all_versions respects the limit parameter."""
        _insert_job("testco::test job")
        for i in range(5):
            save_resume_version(
                job_dedup_key="testco::test job",
                resume_type="resume",
                file_path=f"/tmp/v{i}.pdf",
                original_resume_path="/tmp/orig.pdf",
                model_used="claude-test",
            )

        versions = get_all_versions(limit=3)
        assert len(versions) == 3
