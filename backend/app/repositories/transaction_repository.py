"""Small transaction-related repository errors shared by DBMS features."""


class TransactionNotFoundError(LookupError):
    """Raised when a query references an unknown transaction."""


class TransactionPIDMismatchError(ValueError):
    """Raised when a query PID differs from its transaction PID."""
