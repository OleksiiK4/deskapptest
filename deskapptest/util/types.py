from typing import Tuple, TypedDict


MatchRes = TypedDict(
    "MatchRes",
    {
        "result": Tuple[int, int],
        "confidence": float,
        "rectangle": Tuple[int, int, int, int],
    },
)
