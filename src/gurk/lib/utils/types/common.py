from pathlib import Path
from typing import TypeAlias, TypeVar

T = TypeVar("T")

PathLike: TypeAlias = str | Path
ListOrTuple: TypeAlias = list[T] | tuple[T, ...]
