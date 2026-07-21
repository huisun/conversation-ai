"""Core TAC functionality."""

from tac.core.config import TACConfig
from tac.core.logging import get_logger
from tac.core.tac import TAC

__all__ = ["TAC", "TACConfig", "get_logger"]
