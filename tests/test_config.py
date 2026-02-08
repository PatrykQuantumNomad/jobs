"""Config integration tests (CFG-01 through CFG-04).

Validates that config.py correctly loads YAML, validates inputs, applies defaults,
and respects source precedence (env > yaml > model default).

All tests use isolated YAML files and /dev/null for env_file to prevent
contamination from real .env or config.yaml files.
"""

import pytest
import yaml
from pydantic import ValidationError

from apply_engine.config import ApplyConfig
from config import (
    AppSettings,
    ScheduleConfig,
    ScoringWeights,
    SearchQueryConfig,
    get_settings,
    reset_settings,
)
from models import CandidateProfile

# -- Test constants -----------------------------------------------------------

MINIMAL_YAML = {
    "search": {"queries": [{"title": "test engineer"}]},
    "scoring": {"target_titles": ["Senior Engineer"], "tech_keywords": ["python"]},
}

FULL_YAML = {
    "search": {
        "min_salary": 180000,
        "queries": [
            {"title": "Staff Engineer", "keywords": ["kubernetes", "cloud"], "max_pages": 3},
            {"title": "DevOps Lead", "platforms": ["indeed"]},
        ],
    },
    "scoring": {
        "target_titles": ["Staff Engineer", "Principal Engineer"],
        "tech_keywords": ["python", "kubernetes", "terraform"],
        "weights": {"title_match": 3.0, "tech_overlap": 2.5, "remote": 1.0, "salary": 0.5},
    },
    "platforms": {
        "indeed": {"enabled": True},
        "dice": {"enabled": False},
        "remoteok": {"enabled": True},
    },
    "timing": {
        "nav_delay_min": 1.0,
        "nav_delay_max": 3.0,
        "form_delay_min": 0.5,
        "form_delay_max": 1.5,
        "page_load_timeout": 15000,
    },
    "schedule": {"enabled": True, "hour": 9, "minute": 30, "weekdays": [1, 2, 3, 4, 5]},
    "apply": {
        "default_mode": "easy_apply_only",
        "confirm_before_submit": False,
        "max_concurrent_applies": 3,
    },
}


# -- Fixture: isolated YAML config loader ------------------------------------


@pytest.fixture
def config_from_yaml(tmp_path):
    """Load AppSettings from a temp YAML, isolated from real .env."""
    original_yaml = AppSettings.model_config.get("yaml_file")
    original_env = AppSettings.model_config.get("env_file")

    def _load(yaml_data: dict) -> AppSettings:
        yaml_path = tmp_path / "test.yaml"
        yaml_path.write_text(yaml.dump(yaml_data))
        reset_settings()
        AppSettings.model_config["yaml_file"] = str(yaml_path)
        AppSettings.model_config["env_file"] = "/dev/null"
        return AppSettings()  # type: ignore[call-arg]  # search/scoring from YAML

    yield _load

    AppSettings.model_config["yaml_file"] = original_yaml
    AppSettings.model_config["env_file"] = original_env
    reset_settings()


# =============================================================================
# CFG-01: YAML Loading
# =============================================================================


@pytest.mark.integration
class TestConfigLoading:
    """Verify that valid YAML configs load correctly with proper types."""

    def test_full_yaml_loads_all_sections(self, config_from_yaml):
        """All YAML sections parse to their correct sub-model types."""
        settings = config_from_yaml(FULL_YAML)

        assert settings.search.min_salary == 180000
        assert settings.scoring.weights.title_match == 3.0
        assert settings.platforms.dice.enabled is False
        assert settings.timing.nav_delay_min == 1.0
        assert settings.schedule.enabled is True
        assert settings.schedule.weekdays == [1, 2, 3, 4, 5]
        assert settings.apply.default_mode == "easy_apply_only"

    def test_search_queries_parsed_correctly(self, config_from_yaml):
        """Search queries preserve title, keywords, and max_pages."""
        settings = config_from_yaml(FULL_YAML)

        assert len(settings.search.queries) == 2
        first = settings.search.queries[0]
        assert first.title == "Staff Engineer"
        assert first.keywords == ["kubernetes", "cloud"]
        assert first.max_pages == 3

    def test_scoring_weights_typed_correctly(self, config_from_yaml):
        """All scoring weight fields are float type with correct values."""
        settings = config_from_yaml(FULL_YAML)
        w = settings.scoring.weights

        assert isinstance(w.title_match, float)
        assert isinstance(w.tech_overlap, float)
        assert isinstance(w.remote, float)
        assert isinstance(w.salary, float)

        assert w.title_match == 3.0
        assert w.tech_overlap == 2.5
        assert w.remote == 1.0
        assert w.salary == 0.5

    def test_get_search_queries_filters_by_platform(self, config_from_yaml):
        """get_search_queries returns only queries matching the platform."""
        settings = config_from_yaml(FULL_YAML)

        # indeed: both queries match (Staff Engineer has no platform filter,
        # DevOps Lead has platforms=["indeed"])
        indeed_queries = settings.get_search_queries("indeed")
        assert len(indeed_queries) == 2

        # dice: only Staff Engineer (no platform filter); DevOps Lead is indeed-only
        dice_queries = settings.get_search_queries("dice")
        assert len(dice_queries) == 1
        assert "Staff Engineer" in dice_queries[0].query

    def test_enabled_platforms_returns_correct_list(self, config_from_yaml):
        """enabled_platforms filters out platforms with enabled=False."""
        settings = config_from_yaml(FULL_YAML)

        enabled = settings.enabled_platforms()
        assert enabled == ["indeed", "remoteok"]
        assert "dice" not in enabled

    def test_validate_platform_credentials(self, config_from_yaml):
        """Credential validation: indeed/remoteok always True, dice needs creds."""
        settings = config_from_yaml(MINIMAL_YAML)

        assert settings.validate_platform_credentials("indeed") is True
        assert settings.validate_platform_credentials("remoteok") is True
        # dice requires email + password; with /dev/null env_file, both are None
        assert settings.validate_platform_credentials("dice") is False

    def test_build_candidate_profile_returns_model(self, config_from_yaml):
        """build_candidate_profile returns CandidateProfile with scoring fields."""
        settings = config_from_yaml(MINIMAL_YAML)
        profile = settings.build_candidate_profile()

        assert isinstance(profile, CandidateProfile)
        assert profile.target_titles == ["Senior Engineer"]
        assert profile.tech_keywords == ["python"]

    def test_get_settings_singleton_caches(self, config_from_yaml, tmp_path):
        """get_settings returns the same object on consecutive calls."""
        yaml_path = tmp_path / "singleton_test.yaml"
        yaml_path.write_text(yaml.dump(MINIMAL_YAML))

        reset_settings()
        AppSettings.model_config["yaml_file"] = str(yaml_path)
        AppSettings.model_config["env_file"] = "/dev/null"

        first = get_settings(str(yaml_path))
        second = get_settings(str(yaml_path))
        assert first is second

    def test_extra_yaml_keys_ignored(self, config_from_yaml):
        """Unknown YAML sections do not raise errors (extra='ignore')."""
        extended = {**MINIMAL_YAML, "unknown_section": {"foo": "bar"}}
        settings = config_from_yaml(extended)
        # No error raised -- just verify it loaded
        assert settings.search.queries[0].title == "test engineer"


# =============================================================================
# CFG-02: Validation Rejection
# =============================================================================


@pytest.mark.integration
class TestConfigValidation:
    """Verify that invalid config values produce clear ValidationError."""

    def test_empty_yaml_missing_required_fields(self, config_from_yaml):
        """Empty YAML fails validation for missing search and scoring."""
        with pytest.raises(ValidationError) as exc_info:
            config_from_yaml({})

        error_locs = [e["loc"] for e in exc_info.value.errors()]
        # search and scoring are required
        assert any("search" in loc for loc in error_locs)
        assert any("scoring" in loc for loc in error_locs)

    def test_missing_scoring_section(self, config_from_yaml):
        """YAML with search but no scoring raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            config_from_yaml({"search": {"queries": [{"title": "x"}]}})

        error_locs = [e["loc"] for e in exc_info.value.errors()]
        assert any("scoring" in loc for loc in error_locs)

    def test_invalid_type_min_salary(self, config_from_yaml):
        """Non-numeric min_salary produces a clear type error."""
        bad = {
            **MINIMAL_YAML,
            "search": {**MINIMAL_YAML["search"], "min_salary": "not-a-number"},
        }
        with pytest.raises(ValidationError) as exc_info:
            config_from_yaml(bad)

        errors = exc_info.value.errors()
        salary_errors = [e for e in errors if tuple(e["loc"]) == ("search", "min_salary")]
        assert len(salary_errors) > 0
        assert salary_errors[0]["type"] == "int_parsing"

    @pytest.mark.parametrize(
        "model_cls, kwargs, expected_error_type",
        [
            pytest.param(
                ScoringWeights,
                {"title_match": -1.0},
                "greater_than_equal",
                id="negative-weight",
            ),
            pytest.param(
                SearchQueryConfig,
                {"title": "test", "max_pages": 99},
                "less_than_equal",
                id="max-pages-too-high",
            ),
            pytest.param(
                SearchQueryConfig,
                {"title": "test", "max_pages": 0},
                "greater_than_equal",
                id="max-pages-too-low",
            ),
            pytest.param(
                ScheduleConfig,
                {"weekdays": [7]},
                "value_error",
                id="weekday-out-of-range",
            ),
            pytest.param(
                ScheduleConfig,
                {"hour": 25},
                "less_than_equal",
                id="hour-too-high",
            ),
            pytest.param(
                ApplyConfig,
                {"max_concurrent_applies": 10},
                "less_than_equal",
                id="max-applies-too-high",
            ),
            pytest.param(
                ApplyConfig,
                {"max_concurrent_applies": 0},
                "greater_than_equal",
                id="max-applies-too-low",
            ),
            pytest.param(
                ApplyConfig,
                {"default_mode": "yolo"},
                "enum",
                id="invalid-apply-mode",
            ),
            pytest.param(
                ApplyConfig,
                {"ats_form_fill_timeout": 5},
                "greater_than_equal",
                id="ats-timeout-too-low",
            ),
            pytest.param(
                ApplyConfig,
                {"ats_form_fill_timeout": 999},
                "less_than_equal",
                id="ats-timeout-too-high",
            ),
        ],
    )
    def test_sub_model_validation(self, model_cls, kwargs, expected_error_type):
        """Sub-model constraint violations raise ValidationError with expected type."""
        with pytest.raises(ValidationError) as exc_info:
            model_cls(**kwargs)

        error_types = [e["type"] for e in exc_info.value.errors()]
        assert any(expected_error_type in t for t in error_types), (
            f"Expected error type containing '{expected_error_type}', got {error_types}"
        )

    def test_missing_yaml_file_raises_validation_error(self, tmp_path):
        """Non-existent YAML path raises ValidationError (not FileNotFoundError)."""
        original_yaml = AppSettings.model_config.get("yaml_file")
        original_env = AppSettings.model_config.get("env_file")

        try:
            reset_settings()
            AppSettings.model_config["yaml_file"] = "/tmp/does_not_exist_xyz.yaml"
            AppSettings.model_config["env_file"] = "/dev/null"

            with pytest.raises(ValidationError) as exc_info:
                AppSettings()  # type: ignore[call-arg]  # intentionally missing

            # Missing YAML means required fields (search, scoring) are missing
            error_locs = [e["loc"] for e in exc_info.value.errors()]
            assert any("search" in loc for loc in error_locs)
        finally:
            AppSettings.model_config["yaml_file"] = original_yaml
            AppSettings.model_config["env_file"] = original_env
            reset_settings()


# =============================================================================
# CFG-03: Default Values
# =============================================================================


@pytest.mark.integration
class TestConfigDefaults:
    """Verify that optional fields get documented default values."""

    def test_minimal_yaml_gets_all_defaults(self, config_from_yaml):
        """Loading only required fields fills all defaults correctly."""
        settings = config_from_yaml(MINIMAL_YAML)

        # search defaults
        assert settings.search.min_salary == 150_000

        # platforms all default to enabled
        assert settings.platforms.indeed.enabled is True
        assert settings.platforms.dice.enabled is True
        assert settings.platforms.remoteok.enabled is True

        # timing defaults
        assert settings.timing.nav_delay_min == 2.0
        assert settings.timing.nav_delay_max == 5.0
        assert settings.timing.form_delay_min == 1.0
        assert settings.timing.form_delay_max == 2.0
        assert settings.timing.page_load_timeout == 30_000

        # schedule defaults
        assert settings.schedule.enabled is False
        assert settings.schedule.hour == 8
        assert settings.schedule.minute == 0
        assert settings.schedule.weekdays is None

        # scoring weight defaults
        assert settings.scoring.weights.title_match == 2.0
        assert settings.scoring.weights.tech_overlap == 2.0
        assert settings.scoring.weights.remote == 1.0
        assert settings.scoring.weights.salary == 1.0

        # apply defaults
        assert settings.apply.default_mode == "semi_auto"
        assert settings.apply.confirm_before_submit is True
        assert settings.apply.max_concurrent_applies == 1
        assert settings.apply.screenshot_before_submit is True
        assert settings.apply.headed_mode is True
        assert settings.apply.ats_form_fill_enabled is True
        assert settings.apply.ats_form_fill_timeout == 120

    def test_credential_defaults_are_none_or_empty(self, config_from_yaml):
        """Credential and candidate fields default to None/empty with /dev/null env."""
        settings = config_from_yaml(MINIMAL_YAML)

        assert settings.indeed_email is None
        assert settings.dice_email is None
        assert settings.dice_password is None
        assert settings.candidate_first_name == ""
        assert settings.candidate_desired_salary_usd == 200_000
        assert settings.candidate_resume_path == "resumes/Patryk_Golabek_Resume_ATS.pdf"

    def test_partial_section_gets_remaining_defaults(self, config_from_yaml):
        """Partial timing section keeps defaults for unspecified fields."""
        partial = {**MINIMAL_YAML, "timing": {"nav_delay_min": 0.5}}
        settings = config_from_yaml(partial)

        assert settings.timing.nav_delay_min == 0.5
        assert settings.timing.nav_delay_max == 5.0  # default
        assert settings.timing.form_delay_min == 1.0  # default
        assert settings.timing.form_delay_max == 2.0  # default
        assert settings.timing.page_load_timeout == 30_000  # default

    def test_search_query_defaults(self, config_from_yaml):
        """Query with only title gets default keywords, location, max_pages."""
        settings = config_from_yaml(MINIMAL_YAML)
        query = settings.search.queries[0]

        assert query.title == "test engineer"
        assert query.keywords == []
        assert query.location == ""
        assert query.max_pages == 5
        assert query.platforms == []


# =============================================================================
# CFG-04: Environment Variable Overrides
# =============================================================================


@pytest.mark.integration
class TestConfigEnvOverrides:
    """Verify that environment variables override YAML and model defaults."""

    def test_top_level_env_overrides_default(self, monkeypatch, config_from_yaml):
        """Env var overrides the model default for a top-level scalar field."""
        monkeypatch.setenv("CANDIDATE_DESIRED_SALARY_USD", "300000")
        settings = config_from_yaml(MINIMAL_YAML)

        assert settings.candidate_desired_salary_usd == 300_000

    def test_credential_env_overrides(self, monkeypatch, config_from_yaml):
        """Env vars for credentials populate fields that default to None."""
        monkeypatch.setenv("DICE_EMAIL", "test@test.com")
        monkeypatch.setenv("DICE_PASSWORD", "secret")
        settings = config_from_yaml(MINIMAL_YAML)

        assert settings.dice_email == "test@test.com"
        assert settings.dice_password == "secret"

    def test_json_env_overrides_nested_section(self, monkeypatch, config_from_yaml):
        """JSON env var overrides an entire nested section."""
        import json

        monkeypatch.setenv(
            "TIMING",
            json.dumps(
                {
                    "nav_delay_min": 99.0,
                    "nav_delay_max": 99.0,
                    "form_delay_min": 99.0,
                    "form_delay_max": 99.0,
                    "page_load_timeout": 99000,
                }
            ),
        )
        settings = config_from_yaml(MINIMAL_YAML)

        assert settings.timing.nav_delay_min == 99.0
        assert settings.timing.page_load_timeout == 99000

    def test_underscore_delimiter_does_not_work_for_nested(self, monkeypatch, config_from_yaml):
        """Double-underscore env vars do NOT override nested fields (no env_nested_delimiter)."""
        monkeypatch.setenv("TIMING__NAV_DELAY_MIN", "99")
        settings = config_from_yaml(MINIMAL_YAML)

        # Unchanged because pydantic-settings has no env_nested_delimiter configured
        assert settings.timing.nav_delay_min == 2.0

    def test_env_overrides_yaml_value(self, monkeypatch, config_from_yaml):
        """Env var wins over YAML-specified value (env > yaml precedence)."""
        import json

        monkeypatch.setenv(
            "SEARCH",
            json.dumps({"min_salary": 250000, "queries": [{"title": "test"}]}),
        )
        # FULL_YAML sets search.min_salary=180000, but env should win
        settings = config_from_yaml(FULL_YAML)

        assert settings.search.min_salary == 250_000

    def test_source_priority_chain(self, monkeypatch, config_from_yaml):
        """Full priority chain: model default < yaml < env var."""
        # Step 1: model default (no YAML override, no env var)
        settings = config_from_yaml(MINIMAL_YAML)
        assert settings.candidate_desired_salary_usd == 200_000  # model default

        # Step 2: env var overrides model default
        monkeypatch.setenv("CANDIDATE_DESIRED_SALARY_USD", "350000")
        settings = config_from_yaml(MINIMAL_YAML)
        assert settings.candidate_desired_salary_usd == 350_000  # env wins

    def test_env_file_dev_null_isolates_from_real_dotenv(self, config_from_yaml):
        """With env_file=/dev/null, real .env values do not leak in."""
        settings = config_from_yaml(MINIMAL_YAML)

        # If real .env leaked, dice_password would be set
        assert settings.dice_password is None
