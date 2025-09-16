class BurpSuiteException(Exception):
    """ Base exception """
    pass


class ConnectionError(BurpSuiteException):
    """ Raised when there's a connection error with the Burp Suite server """
    pass


class AuthorizationError(BurpSuiteException):
    """ Raised when the Burp Suite server returns a 401 status code """
    pass


class BadRequestError(BurpSuiteException):
    """ Raised when the Burp Suite API returns a 400 status code """
    pass


class InternalServerError(BurpSuiteException):
    """ Raised when the Burp Suite API returns a 500 status code """
    pass


class IssueTypeIdError(BurpSuiteException):
    """ Raised when a issue_type_id is not found when using get_definition """
    pass