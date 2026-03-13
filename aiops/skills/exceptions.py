class SkillCreationError(Exception):
    """Generic skill creation error."""


class SkillQualityError(SkillCreationError):
    """Raised when skill quality is below threshold."""


class SecurityBlockedError(SkillCreationError):
    """Raised when security scan blocks a skill."""


class SkillExistsError(SkillCreationError):
    """Raised when skill already exists."""


class ValidationError(SkillCreationError):
    """Raised when validation fails."""
