"""
Collection of smaller classes, mostly used for flagging other obects.
"""


from enum import Enum, IntFlag, auto


class Contract(Enum):
    """Represents contract types."""

    FULLTIME = 1
    PARTTIME = 2


class PropertyFlag(IntFlag):
    """Represents all special properties employees can have."""

    NONE = 0
    CAN_OPEN = auto()
    CAN_CLOSE = auto()
    IS_STUDENT = auto()
    IS_IN_SCHOOL = auto()
    HAS_KEYS = auto()


class Preference(IntFlag):
    """Represents employee preference or availability for a shift.

    Undesirable flag also works as a dissatisfaction
    factor in the objective function.
    """

    NORMAL = 0
    UNAVAILABLE = 1
    UNDESIRABLE = 8
