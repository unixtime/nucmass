"""
Custom exceptions for the nucmass package.

These exceptions provide clear, actionable error messages for researchers
who may not be familiar with the underlying implementation details.
"""

__all__ = [
    "NucmassError",
    "NuclideNotFoundError",
    "InvalidNuclideError",
    "DatabaseNotInitializedError",
    "DataFileNotFoundError",
    "ExtractionError",
    "DatabaseCorruptError",
]


class NucmassError(Exception):
    """Base exception for all nucmass errors."""
    pass


class NuclideNotFoundError(NucmassError):
    """
    Raised when a requested nuclide is not found in the database.

    Attributes:
        z: Proton number that was requested.
        n: Neutron number that was requested.
        suggestions: List of nearby nuclides that do exist.
    """

    def __init__(self, z: int, n: int, suggestions: list[tuple[int, int]] | None = None):
        self.z = z
        self.n = n
        self.suggestions = suggestions or []

        message = f"No data found for nuclide with Z={z}, N={n} (A={z+n})"
        if self.suggestions:
            suggestion_str = ", ".join(f"N={s[1]}" for s in self.suggestions[:5])
            message += f". Available N values for Z={z}: {suggestion_str}"

        super().__init__(message)


class InvalidNuclideError(NucmassError):
    """
    Raised when nuclide parameters are physically invalid.

    Examples of invalid parameters:
    - Negative Z or N values
    - Z or N exceeding known limits
    """

    def __init__(self, message: str, z: int | None = None, n: int | None = None):
        self.z = z
        self.n = n
        super().__init__(message)


class DatabaseNotInitializedError(NucmassError):
    """Raised when trying to query before the database is ready."""
    pass


class DataFileNotFoundError(NucmassError):
    """Raised when required data files (CSV, PDF) are not found."""

    def __init__(self, filepath: str, suggestion: str | None = None):
        self.filepath = filepath
        message = f"Data file not found: {filepath}"
        if suggestion:
            message += f"\n{suggestion}"
        super().__init__(message)


class ExtractionError(NucmassError):
    """Raised when PDF extraction fails."""
    pass


class DatabaseCorruptError(NucmassError):
    """
    Raised when the database file exists but is corrupted or invalid.

    This can happen if:
    - The database file was partially written
    - The file is not a valid DuckDB database
    - Required tables or views are missing
    """

    def __init__(self, db_path: str, reason: str | None = None):
        self.db_path = db_path
        self.reason = reason
        message = f"Database at {db_path} is corrupted or invalid"
        if reason:
            message += f": {reason}"
        message += "\nDelete the file and run: nucmass init --rebuild"
        super().__init__(message)
