from collections.abc import Iterator, Protocol


class ReadingSource(Protocol):
    def __iter__(self) -> Iterator[float | None]: ...
