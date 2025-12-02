import requests
import json
from packaging import version
from datetime import datetime, timedelta

# GitHub configuration
GITHUB_OWNER = "definitelynotrafa"
GITHUB_REPO = "ISTEC-Wargaming"
GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/releases/latest"
CURRENT_VERSION = "1.0.0"

def get_latest_version():
    """Get latest version from GitHub releases"""
    try:
        response = requests.get(GITHUB_API_URL, timeout=5)
        if response.status_code == 200:
            data = response.json()
            return data.get('tag_name', '').lstrip('v')
        return None
    except Exception as e:
        print(f"Error fetching latest version: {e}")
        return None

def check_version_freshness():
    """Check if the current version is up to date and return status message"""
    try:
        current = CURRENT_VERSION
        latest = get_latest_version()
        
        if not latest:
            # Can't check - network issue
            return "Your vegetables are fresh!", "#4CAF50", f"v{current}"
        
        current_ver = version.parse(current)
        latest_ver = version.parse(latest)
        
        if current_ver < latest_ver:
            return f"Update available: v{latest}", "#FF6B6B", f"v{current}"
        elif current_ver == latest_ver:
            return "You're up to date!", "#4CAF50", f"v{current}"
        else:
            return "Development version", "#2196F3", f"v{current}"
            
    except Exception as e:
        print(f"Error checking version freshness: {e}")
        # Return default values instead of None
        return "Version check failed", "#FFA500", "v0.0.0"


class VersionChecker:
    
    # Cache settings
    CACHE_DURATION_HOURS = 24
    
    def __init__(self):
        self.is_outdated = False
        self.latest_version = None
        self.update_message = ""
        self.last_check = None
        
    def check_version(self, force=False):
        """
        Check if current version is outdated
        
        Args:
            force (bool): Force check even if cached result exists
            
        Returns:
            dict: {
                'is_outdated': bool,
                'current_version': str,
                'latest_version': str,
                'message': str,
                'release_url': str
            }
        """
        # Skip check if recently checked and not forced
        if not force and self.last_check:
            time_since_check = datetime.now() - self.last_check
            if time_since_check < timedelta(hours=self.CACHE_DURATION_HOURS):
                return self._get_result()
        
        try:
            # Fetch latest release from GitHub
            response = requests.get(GITHUB_API_URL, timeout=5)
            
            if response.status_code == 200:
                release_data = response.json()
                self.latest_version = release_data.get('tag_name', '').lstrip('v')
                
                # Compare versions
                if self.latest_version:
                    current = version.parse(self.CURRENT_VERSION)
                    latest = version.parse(self.latest_version)
                    
                    self.is_outdated = current < latest
                    
                    if self.is_outdated:
                        self.update_message = "Your vegetables are rotting!"
                    else:
                        self.update_message = f"v{self.CURRENT_VERSION}"
                    
                    self.last_check = datetime.now()
                    return self._get_result(release_data.get('html_url', ''))
            
            # If API call fails, assume up to date
            self.is_outdated = False
            self.update_message = f"v{self.CURRENT_VERSION}"
            return self._get_result()
            
        except (requests.RequestException, json.JSONDecodeError, Exception) as e:
            # On any error, assume up to date and don't alarm user
            print(f"Version check failed: {e}")
            self.is_outdated = False
            self.update_message = f"v{self.CURRENT_VERSION}"
            return self._get_result()
    
    def _get_result(self, release_url=""):
        """Format and return check result"""
        return {
            'is_outdated': self.is_outdated,
            'current_version': self.CURRENT_VERSION,
            'latest_version': self.latest_version or self.CURRENT_VERSION,
            'message': self.update_message,
            'release_url': release_url
        }
    
    def get_version_badge_style(self):
        """
        Get CSS style for version badge based on update status
        
        Returns:
            dict: {'background_color': str, 'text': str}
        """
        if self.is_outdated:
            return {
                'background_color': '#dc2626',  # Red background
                'text': self.update_message,
                'border_color': '#991b1b'
            }
        else:
            return {
                'background_color': '#2563eb',  # Blue background
                'text': self.update_message,
                'border_color': '#1e40af'
            }


# Global instance
_version_checker = None


def get_version_checker():
    """Get or create global version checker instance"""
    global _version_checker
    if _version_checker is None:
        _version_checker = VersionChecker()
    return _version_checker


def check_for_updates(force=False):
    """
    Convenience function to check for updates
    
    Args:
        force (bool): Force check even if cached
        
    Returns:
        dict: Version check result
    """
    checker = get_version_checker()
    return checker.check_version(force=force)


def is_outdated():
    """
    Check if current version is outdated (uses cache)
    
    Returns:
        bool: True if outdated
    """
    checker = get_version_checker()
    if not checker.last_check:
        checker.check_version()
    return checker.is_outdated


def get_version_info():
    """
    Get current version information
    
    Returns:
        dict: Version badge style information
    """
    checker = get_version_checker()
    if not checker.last_check:
        checker.check_version()
    return checker.get_version_badge_style()