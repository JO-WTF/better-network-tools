class HttpError(Exception):
    pass


class BadStatusError(HttpError):
    pass


class BadJsonError(HttpError):
    pass
