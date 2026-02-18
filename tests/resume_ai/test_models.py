"""Unit tests for resume_ai Pydantic models -- SkillSection, WorkExperience,
TailoredResume, CoverLetter.

Tests cover:
- Valid construction of each model with required fields
- model_dump(mode="json") produces expected keys
- Missing required fields raise ValidationError
"""

import pytest
from pydantic import ValidationError

from resume_ai.models import CoverLetter, SkillSection, TailoredResume, WorkExperience


@pytest.mark.unit
class TestSkillSection:
    """Verify SkillSection construction and serialization."""

    def test_construct_valid(self):
        """SkillSection with category and skills constructs correctly."""
        s = SkillSection(category="Backend", skills=["Python", "Go"])
        assert s.category == "Backend"
        assert s.skills == ["Python", "Go"]

    def test_model_dump_keys(self):
        """model_dump(mode='json') returns dict with category and skills."""
        s = SkillSection(category="Cloud", skills=["AWS", "GCP"])
        dumped = s.model_dump(mode="json")
        assert "category" in dumped
        assert "skills" in dumped
        assert dumped["category"] == "Cloud"

    def test_missing_category_raises(self):
        """Missing category raises ValidationError."""
        with pytest.raises(ValidationError):
            SkillSection(skills=["Python"])  # type: ignore[call-arg]

    def test_missing_skills_raises(self):
        """Missing skills raises ValidationError."""
        with pytest.raises(ValidationError):
            SkillSection(category="Backend")  # type: ignore[call-arg]


@pytest.mark.unit
class TestWorkExperience:
    """Verify WorkExperience construction and serialization."""

    def test_construct_valid(self):
        """WorkExperience with all required fields constructs correctly."""
        w = WorkExperience(
            company="Acme",
            title="Engineer",
            period="2020-2024",
            achievements=["Led team"],
        )
        assert w.company == "Acme"
        assert w.title == "Engineer"
        assert w.period == "2020-2024"
        assert w.achievements == ["Led team"]

    def test_model_dump_keys(self):
        """model_dump has all four keys."""
        w = WorkExperience(
            company="Corp",
            title="SRE",
            period="2019-2021",
            achievements=["Built infra", "Reduced latency"],
        )
        dumped = w.model_dump(mode="json")
        assert set(dumped.keys()) == {"company", "title", "period", "achievements"}

    def test_missing_achievements_raises(self):
        """Missing achievements raises ValidationError."""
        with pytest.raises(ValidationError):
            WorkExperience(company="X", title="Y", period="2020")  # type: ignore[call-arg]


@pytest.mark.unit
class TestTailoredResume:
    """Verify TailoredResume construction and serialization."""

    def _make_resume(self, **overrides):
        defaults = {
            "professional_summary": "Experienced engineer",
            "technical_skills": [SkillSection(category="Backend", skills=["Python"])],
            "work_experience": [
                WorkExperience(
                    company="Acme",
                    title="Engineer",
                    period="2020-2024",
                    achievements=["Built API"],
                )
            ],
            "key_projects": ["Open source CLI tool"],
            "education": "BSc Computer Science",
            "tailoring_notes": "Reordered skills for backend focus",
        }
        defaults.update(overrides)
        return TailoredResume(**defaults)

    def test_construct_valid(self):
        """TailoredResume with all required fields constructs correctly."""
        r = self._make_resume()
        assert r.professional_summary == "Experienced engineer"
        assert len(r.technical_skills) == 1
        assert len(r.work_experience) == 1
        assert r.education == "BSc Computer Science"

    def test_model_dump_keys(self):
        """model_dump(mode='json') returns dict with all seven keys."""
        r = self._make_resume()
        dumped = r.model_dump(mode="json")
        expected_keys = {
            "professional_summary",
            "technical_skills",
            "work_experience",
            "key_projects",
            "education",
            "tailoring_notes",
            "keyword_alignment",
        }
        assert set(dumped.keys()) == expected_keys

    def test_missing_professional_summary_raises(self):
        """Missing professional_summary raises ValidationError."""
        with pytest.raises(ValidationError):
            TailoredResume(
                technical_skills=[],
                work_experience=[],
                key_projects=[],
                education="BSc",
                tailoring_notes="notes",
            )  # type: ignore[call-arg]

    def test_missing_tailoring_notes_raises(self):
        """Missing tailoring_notes raises ValidationError."""
        with pytest.raises(ValidationError):
            TailoredResume(
                professional_summary="summary",
                technical_skills=[],
                work_experience=[],
                key_projects=[],
                education="BSc",
            )  # type: ignore[call-arg]

    def test_keyword_alignment_defaults_to_empty_list(self):
        """keyword_alignment defaults to empty list when not provided."""
        r = self._make_resume()
        assert r.keyword_alignment == []

    def test_keyword_alignment_accepts_list(self):
        """keyword_alignment accepts a list of keyword strings."""
        r = self._make_resume(keyword_alignment=["kubernetes", "terraform"])
        assert r.keyword_alignment == ["kubernetes", "terraform"]


@pytest.mark.unit
class TestCoverLetter:
    """Verify CoverLetter construction and serialization."""

    def _make_letter(self, **overrides):
        defaults = {
            "greeting": "Dear Hiring Manager,",
            "opening_paragraph": "I am excited to apply for the role.",
            "body_paragraphs": ["Paragraph one.", "Paragraph two."],
            "closing_paragraph": "I look forward to discussing further.",
            "sign_off": "Sincerely,",
        }
        defaults.update(overrides)
        return CoverLetter(**defaults)

    def test_construct_valid(self):
        """CoverLetter with all required fields constructs correctly."""
        cl = self._make_letter()
        assert cl.greeting == "Dear Hiring Manager,"
        assert len(cl.body_paragraphs) == 2

    def test_model_dump_keys(self):
        """model_dump(mode='json') returns dict with all five keys."""
        cl = self._make_letter()
        dumped = cl.model_dump(mode="json")
        expected_keys = {
            "greeting",
            "opening_paragraph",
            "body_paragraphs",
            "closing_paragraph",
            "sign_off",
        }
        assert set(dumped.keys()) == expected_keys

    def test_missing_greeting_raises(self):
        """Missing greeting raises ValidationError."""
        with pytest.raises(ValidationError):
            CoverLetter(
                opening_paragraph="x",
                body_paragraphs=[],
                closing_paragraph="x",
                sign_off="x",
            )  # type: ignore[call-arg]

    def test_missing_body_paragraphs_raises(self):
        """Missing body_paragraphs raises ValidationError."""
        with pytest.raises(ValidationError):
            CoverLetter(
                greeting="Hi",
                opening_paragraph="x",
                closing_paragraph="x",
                sign_off="x",
            )  # type: ignore[call-arg]
