"""Factory Boy factories for Pydantic v2 models.

factory-boy has no native Pydantic integration, but setting
``class Meta: model = Job`` works because factory-boy calls
``Job(field1=val1, ...)`` which triggers Pydantic validation.
"""

# pyright: reportPrivateImportUsage=false
import factory
from faker import Faker

from core.models import Job, JobStatus

fake = Faker()


class JobFactory(factory.Factory):
    """Factory producing valid models.Job instances.

    All field values satisfy Pydantic constraints:
    - platform: cycles through valid Literal values
    - score: 1-5 (ge=1, le=5)
    - salary_max >= salary_min (cross-field validator)
    - description: str (not list -- Faker's paragraphs returns list)
    """

    class Meta:  # type: ignore[reportIncompatibleVariableOverride]
        model = Job

    id = factory.LazyFunction(lambda: fake.hexify("????????????????"))
    platform = factory.Iterator(["indeed", "dice", "remoteok"])
    title = factory.Faker("job")
    company = factory.Faker("company")
    location = factory.LazyFunction(
        lambda: fake.random_element(["Remote", "New York, NY", "Toronto, ON"])
    )
    url = factory.LazyFunction(lambda: f"https://example.com/jobs/{fake.uuid4()}")
    salary = factory.LazyFunction(lambda: f"${fake.random_int(150, 300)}K")
    salary_min = factory.LazyFunction(lambda: fake.random_int(150000, 200000))
    # salary_max must be >= salary_min (Pydantic validator)
    salary_max = factory.LazyAttribute(lambda obj: obj.salary_min + fake.random_int(0, 150000))
    posted_date = factory.LazyFunction(lambda: fake.date_between("-14d", "today").isoformat())
    tags = factory.LazyFunction(
        lambda: fake.random_elements(
            ["python", "kubernetes", "terraform", "docker", "aws", "gcp"],
            unique=True,
            length=3,
        )
    )
    easy_apply = factory.Faker("boolean")
    score = factory.LazyFunction(lambda: fake.random_int(1, 5))
    status = JobStatus.SCORED

    @factory.lazy_attribute
    def description(self):
        """Join paragraphs into a single string (Faker's paragraphs returns list)."""
        return "\n\n".join(fake.paragraphs(nb=3))
