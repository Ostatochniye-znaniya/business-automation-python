class ApplicationError(Exception):
    """An expected application failure."""


class NotFoundError(ApplicationError):
    """Requested entity does not exist."""


class ConflictError(ApplicationError):
    """Operation conflicts with existing state."""


class ForbiddenError(ApplicationError):
    """Operation is not permitted."""


class ValidationError(ApplicationError):
    """Input violates an application rule."""


class FeatureNotImplementedError(ApplicationError):
    """Requirements for this use case are not agreed yet."""
