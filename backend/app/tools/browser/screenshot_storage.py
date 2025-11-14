"""
Screenshot Storage and Management
Handles saving, serving, and cleanup of browser automation screenshots
"""
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
import uuid

logger = logging.getLogger(__name__)


class ScreenshotStorage:
    """
    Manages screenshot storage for browser automation
    """

    def __init__(self, base_path: str = "uploads/screenshots"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"Screenshot storage initialized at: {self.base_path}")

    def _get_thread_dir(self, thread_id: str) -> Path:
        """Get or create directory for a specific thread"""
        thread_dir = self.base_path / thread_id
        thread_dir.mkdir(parents=True, exist_ok=True)
        return thread_dir

    def _generate_filename(self, tag: Optional[str] = None) -> str:
        """
        Generate unique filename for screenshot

        Args:
            tag: Optional tag to include in filename

        Returns:
            Filename string
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid.uuid4())[:8]

        if tag:
            # Sanitize tag (remove special characters)
            safe_tag = "".join(c for c in tag if c.isalnum() or c in (' ', '_', '-')).strip()
            safe_tag = safe_tag.replace(' ', '_')
            return f"{timestamp}_{safe_tag}_{unique_id}.png"
        else:
            return f"{timestamp}_{unique_id}.png"

    async def save_screenshot(
        self,
        screenshot_bytes: bytes,
        thread_id: str,
        tag: Optional[str] = None
    ) -> dict:
        """
        Save screenshot to file system

        Args:
            screenshot_bytes: Screenshot image data
            thread_id: Thread/conversation ID for organization
            tag: Optional tag for the screenshot (e.g., "login", "before_swap")

        Returns:
            Dict with file path and URL info
        """
        try:
            # Get thread directory
            thread_dir = self._get_thread_dir(thread_id)

            # Generate filename
            filename = self._generate_filename(tag)
            file_path = thread_dir / filename

            # Save file
            with open(file_path, 'wb') as f:
                f.write(screenshot_bytes)

            # Generate URL path (relative to uploads directory)
            relative_path = f"screenshots/{thread_id}/{filename}"
            url = f"/uploads/{relative_path}"

            logger.info(f"Screenshot saved: {file_path}")

            return {
                "success": True,
                "file_path": str(file_path),
                "url": url,
                "filename": filename,
                "tag": tag,
                "timestamp": datetime.now().isoformat(),
                "size_bytes": len(screenshot_bytes)
            }

        except Exception as e:
            logger.error(f"Error saving screenshot: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }

    def get_screenshot_url(self, thread_id: str, filename: str) -> str:
        """
        Get URL for a specific screenshot

        Args:
            thread_id: Thread ID
            filename: Screenshot filename

        Returns:
            URL path to screenshot
        """
        return f"/uploads/screenshots/{thread_id}/{filename}"

    def get_thread_screenshots(self, thread_id: str) -> list:
        """
        Get all screenshots for a specific thread

        Args:
            thread_id: Thread ID

        Returns:
            List of screenshot info dicts
        """
        thread_dir = self._get_thread_dir(thread_id)

        if not thread_dir.exists():
            return []

        screenshots = []
        for file_path in sorted(thread_dir.glob("*.png"), key=lambda p: p.stat().st_mtime):
            screenshots.append({
                "filename": file_path.name,
                "url": self.get_screenshot_url(thread_id, file_path.name),
                "size_bytes": file_path.stat().st_size,
                "created_at": datetime.fromtimestamp(file_path.stat().st_mtime).isoformat()
            })

        return screenshots

    def cleanup_old_screenshots(self, days: int = 7) -> int:
        """
        Delete screenshots older than specified days

        Args:
            days: Number of days to keep screenshots

        Returns:
            Count of deleted files
        """
        cutoff_time = datetime.now() - timedelta(days=days)
        deleted_count = 0

        try:
            for thread_dir in self.base_path.iterdir():
                if not thread_dir.is_dir():
                    continue

                for file_path in thread_dir.glob("*.png"):
                    file_time = datetime.fromtimestamp(file_path.stat().st_mtime)
                    if file_time < cutoff_time:
                        file_path.unlink()
                        deleted_count += 1
                        logger.info(f"Deleted old screenshot: {file_path}")

                # Remove empty directories
                if not any(thread_dir.iterdir()):
                    thread_dir.rmdir()
                    logger.info(f"Removed empty directory: {thread_dir}")

            logger.info(f"Cleanup completed: {deleted_count} screenshots deleted")
            return deleted_count

        except Exception as e:
            logger.error(f"Error during cleanup: {e}", exc_info=True)
            return deleted_count

    def delete_thread_screenshots(self, thread_id: str) -> int:
        """
        Delete all screenshots for a specific thread

        Args:
            thread_id: Thread ID

        Returns:
            Count of deleted files
        """
        thread_dir = self._get_thread_dir(thread_id)
        deleted_count = 0

        if not thread_dir.exists():
            return 0

        try:
            for file_path in thread_dir.glob("*.png"):
                file_path.unlink()
                deleted_count += 1

            # Remove directory
            thread_dir.rmdir()
            logger.info(f"Deleted {deleted_count} screenshots for thread {thread_id}")

            return deleted_count

        except Exception as e:
            logger.error(f"Error deleting thread screenshots: {e}", exc_info=True)
            return deleted_count

    def get_storage_stats(self) -> dict:
        """
        Get storage statistics

        Returns:
            Dict with storage stats
        """
        total_files = 0
        total_size = 0
        thread_count = 0

        try:
            for thread_dir in self.base_path.iterdir():
                if not thread_dir.is_dir():
                    continue

                thread_count += 1
                for file_path in thread_dir.glob("*.png"):
                    total_files += 1
                    total_size += file_path.stat().st_size

            return {
                "total_screenshots": total_files,
                "total_threads": thread_count,
                "total_size_bytes": total_size,
                "total_size_mb": round(total_size / (1024 * 1024), 2),
                "base_path": str(self.base_path)
            }

        except Exception as e:
            logger.error(f"Error getting storage stats: {e}", exc_info=True)
            return {
                "error": str(e)
            }


# Singleton instance
screenshot_storage = ScreenshotStorage()
