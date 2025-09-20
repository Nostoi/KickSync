"""
Utility functions for the Soccer Coach Sideline Timekeeper application.

This module contains common utility functions used throughout the application.
"""
import time


def fmt_mmss(seconds: int) -> str:
    """
    Format seconds as MM:SS string.
    
    Args:
        seconds: Number of seconds to format
        
    Returns:
        Formatted time string in MM:SS format
        
    Example:
        >>> fmt_mmss(90)
        '01:30'
        >>> fmt_mmss(3661)
        '61:01'
    """
    m = seconds // 60
    s = seconds % 60
    return f"{m:02d}:{s:02d}"


def now_ts() -> float:
    """
    Get current timestamp in epoch seconds.
    
    Returns:
        Current time as floating point epoch seconds
    """
    return time.time()