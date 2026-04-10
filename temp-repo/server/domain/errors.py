class DomainError(Exception):
    pass


class ProviderNotSupportedError(DomainError):
    pass


class InvalidCoordinateError(DomainError):
    pass
