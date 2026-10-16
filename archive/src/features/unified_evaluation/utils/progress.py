"""
Progress tracking utilities for unified evaluation

This module provides progress tracking and visual progress indicators
for long-running evaluations.
"""

import sys
import time
from typing import Optional, Callable, Any
from datetime import datetime

from ..models import ProgressUpdate


class ProgressTracker:
    """
    Progress tracker for evaluation operations
    
    This class provides progress tracking functionality with
    optional callback support for custom progress handling.
    """
    
    def __init__(self, total_steps: int, callback: Optional[Callable[[ProgressUpdate], None]] = None):
        """
        Initialize progress tracker
        
        Args:
            total_steps: Total number of steps in the operation
            callback: Optional callback function for progress updates
        """
        self.total_steps = total_steps
        self.current_step = 0
        self.callback = callback
        self.start_time = datetime.now()
        self.last_update_time = self.start_time
        
    def update(self, current_model: str, current_test: str, message: str):
        """
        Update progress
        
        Args:
            current_model: Current model being evaluated
            current_test: Current test being run
            message: Progress message
        """
        self.current_step += 1
        
        progress_update = ProgressUpdate(
            current_step=self.current_step,
            total_steps=self.total_steps,
            current_model=current_model,
            current_test=current_test,
            message=message
        )
        
        if self.callback:
            self.callback(progress_update)
        
        self.last_update_time = datetime.now()
    
    def set_step(self, step: int):
        """Set current step directly"""
        self.current_step = step
    
    def is_complete(self) -> bool:
        """Check if progress is complete"""
        return self.current_step >= self.total_steps
    
    def get_elapsed_time(self) -> float:
        """Get elapsed time in seconds"""
        return (datetime.now() - self.start_time).total_seconds()
    
    def get_estimated_remaining_time(self) -> Optional[float]:
        """Get estimated remaining time in seconds"""
        if self.current_step == 0:
            return None
        
        elapsed = self.get_elapsed_time()
        rate = self.current_step / elapsed
        remaining_steps = self.total_steps - self.current_step
        
        return remaining_steps / rate if rate > 0 else None


class ProgressBar:
    """
    Console progress bar for evaluation operations
    
    This class provides a visual progress bar that can be updated
    during long-running operations.
    """
    
    def __init__(self, total_steps: int, width: int = 50, show_eta: bool = True):
        """
        Initialize progress bar
        
        Args:
            total_steps: Total number of steps
            width: Width of the progress bar in characters
            show_eta: Whether to show estimated time of arrival
        """
        self.total_steps = total_steps
        self.current_step = 0
        self.width = width
        self.show_eta = show_eta
        self.start_time = time.time()
        self.last_print_time = 0
        self.min_update_interval = 0.1  # Minimum seconds between updates
        
    def update(self, step: int, message: str = ""):
        """
        Update progress bar
        
        Args:
            step: Current step number
            message: Optional message to display
        """
        self.current_step = step
        
        # Throttle updates to avoid too frequent redraws
        current_time = time.time()
        if current_time - self.last_print_time < self.min_update_interval and step < self.total_steps:
            return
        
        self.last_print_time = current_time
        self._draw_progress_bar(message)
    
    def finish(self, message: str = "Complete"):
        """
        Finish progress bar
        
        Args:
            message: Final message to display
        """
        self.current_step = self.total_steps
        self._draw_progress_bar(message)
        print()  # New line after completion
    
    def _draw_progress_bar(self, message: str):
        """Draw the progress bar"""
        percentage = (self.current_step / self.total_steps) * 100 if self.total_steps > 0 else 0
        filled_length = int(self.width * self.current_step / self.total_steps) if self.total_steps > 0 else 0
        
        # Create the bar
        bar = '█' * filled_length + '░' * (self.width - filled_length)
        
        # Create the status line
        status_parts = [
            f"[{bar}]",
            f"{percentage:5.1f}%",
            f"({self.current_step}/{self.total_steps})"
        ]
        
        # Add ETA if enabled
        if self.show_eta and self.current_step > 0:
            eta = self._calculate_eta()
            if eta:
                status_parts.append(f"ETA: {eta}")
        
        # Add message if provided
        if message:
            status_parts.append(message)
        
        # Print the status line
        status_line = " ".join(status_parts)
        print(f"\r{status_line}", end="", flush=True)
    
    def _calculate_eta(self) -> Optional[str]:
        """Calculate estimated time of arrival"""
        if self.current_step == 0:
            return None
        
        elapsed_time = time.time() - self.start_time
        rate = self.current_step / elapsed_time
        remaining_steps = self.total_steps - self.current_step
        
        if rate > 0:
            eta_seconds = remaining_steps / rate
            return self._format_time(eta_seconds)
        
        return None
    
    def _format_time(self, seconds: float) -> str:
        """Format time in human-readable format"""
        if seconds < 60:
            return f"{seconds:.0f}s"
        elif seconds < 3600:
            minutes = int(seconds // 60)
            seconds = int(seconds % 60)
            return f"{minutes}m {seconds}s"
        else:
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            return f"{hours}h {minutes}m"


class SpinnerProgress:
    """
    Spinner progress indicator for indeterminate operations
    
    This class provides a spinning indicator for operations
    where the total progress is unknown.
    """
    
    def __init__(self, message: str = "Working..."):
        """
        Initialize spinner progress
        
        Args:
            message: Message to display with the spinner
        """
        self.message = message
        self.spinner_chars = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
        self.current_char = 0
        self.start_time = time.time()
        self.last_update_time = 0
        self.update_interval = 0.1  # 100ms between updates
        
    def update(self, message: str = None):
        """
        Update spinner
        
        Args:
            message: Optional new message to display
        """
        current_time = time.time()
        
        # Throttle updates
        if current_time - self.last_update_time < self.update_interval:
            return
        
        self.last_update_time = current_time
        
        if message:
            self.message = message
        
        # Get current spinner character
        spinner_char = self.spinner_chars[self.current_char]
        self.current_char = (self.current_char + 1) % len(self.spinner_chars)
        
        # Calculate elapsed time
        elapsed_time = current_time - self.start_time
        time_str = self._format_time(elapsed_time)
        
        # Print the spinner line
        print(f"\r{spinner_char} {self.message} ({time_str})", end="", flush=True)
    
    def finish(self, message: str = "Done"):
        """
        Finish spinner
        
        Args:
            message: Final message to display
        """
        elapsed_time = time.time() - self.start_time
        time_str = self._format_time(elapsed_time)
        print(f"\r✓ {message} ({time_str})")
    
    def _format_time(self, seconds: float) -> str:
        """Format time in human-readable format"""
        if seconds < 60:
            return f"{seconds:.1f}s"
        elif seconds < 3600:
            minutes = int(seconds // 60)
            seconds = int(seconds % 60)
            return f"{minutes}m {seconds}s"
        else:
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            return f"{hours}h {minutes}m"


def create_progress_callback(show_progress: bool = True) -> Optional[Callable[[ProgressUpdate], None]]:
    """
    Create a progress callback function
    
    Args:
        show_progress: Whether to show progress indicators
        
    Returns:
        Progress callback function or None if progress is disabled
    """
    if not show_progress:
        return None
    
    def progress_callback(update: ProgressUpdate):
        """Progress callback that prints to console"""
        percentage = update.progress_percent
        bar_width = 30
        filled_length = int(bar_width * percentage / 100)
        bar = '█' * filled_length + '░' * (bar_width - filled_length)
        
        print(f"\r[{bar}] {percentage:5.1f}% - {update.current_model}: {update.message}", 
              end="", flush=True)
    
    return progress_callback