"""
Credential Storage Service
Securely stores and retrieves Sleeper credentials using OS keychain
Falls back to file-based storage in Docker environments
"""
import keyring
import keyring.backends.fail
import json
import logging
from typing import Optional, Dict
from pydantic import BaseModel
from pathlib import Path

logger = logging.getLogger(__name__)

# Keyring service name
SERVICE_NAME = "fantasy-football-agent-sleeper"

# File-based fallback for Docker
CREDENTIALS_DIR = Path("data/credentials")
CREDENTIALS_DIR.mkdir(parents=True, exist_ok=True)


class SleeperCredentials(BaseModel):
    """Sleeper credentials model"""
    email: str
    password: str
    use_sso: bool = False


class CredentialService:
    """
    Manages secure storage of Sleeper credentials
    Uses OS keychain (macOS Keychain, Windows Credential Manager, Linux Secret Service)
    Falls back to file-based storage in Docker environments
    """

    @staticmethod
    def _get_key(user_id: str, field: str) -> str:
        """Generate keyring key for a specific user and field"""
        return f"{user_id}:{field}"

    @staticmethod
    def _get_credentials_file(user_id: str) -> Path:
        """Get the credentials file path for a user"""
        return CREDENTIALS_DIR / f"{user_id}.json"

    @staticmethod
    def _use_file_storage() -> bool:
        """Check if we should use file storage (keyring not available)"""
        try:
            keyring.get_keyring()
            backend = keyring.get_keyring()
            # Check if it's the fail backend
            return isinstance(backend, keyring.backends.fail.Keyring)
        except Exception:
            return True

    @staticmethod
    def _save_to_file(user_id: str, data: Dict) -> None:
        """Save credentials to file"""
        creds_file = CredentialService._get_credentials_file(user_id)
        with open(creds_file, 'w') as f:
            json.dump(data, f)
        logger.info(f"Credentials saved to file for user {user_id}")

    @staticmethod
    def _load_from_file(user_id: str) -> Optional[Dict]:
        """Load credentials from file"""
        creds_file = CredentialService._get_credentials_file(user_id)
        if not creds_file.exists():
            return None
        with open(creds_file, 'r') as f:
            return json.load(f)

    @staticmethod
    def save_credentials(
        user_id: str,
        email: str,
        password: str,
        use_sso: bool = False
    ) -> Dict[str, any]:
        """
        Save Sleeper credentials to OS keychain

        Args:
            user_id: User identifier
            email: Sleeper account email
            password: Sleeper account password (only stored if not using SSO)
            use_sso: Whether to use Google SSO

        Returns:
            Dict with success status
        """
        try:
            # Validate credentials
            if not email:
                raise ValueError("Email is required")

            if not use_sso and not password:
                raise ValueError("Password is required when not using SSO")

            # Use file storage if keyring is not available
            if CredentialService._use_file_storage():
                data = {
                    "email": email,
                    "password": password if not use_sso else "",
                    "use_sso": use_sso
                }
                CredentialService._save_to_file(user_id, data)
            else:
                # Store email
                keyring.set_password(
                    SERVICE_NAME,
                    CredentialService._get_key(user_id, "email"),
                    email
                )

                # Store password (only if not using SSO)
                if not use_sso:
                    keyring.set_password(
                        SERVICE_NAME,
                        CredentialService._get_key(user_id, "password"),
                        password
                    )
                else:
                    # Clear password if switching to SSO
                    try:
                        keyring.delete_password(
                            SERVICE_NAME,
                            CredentialService._get_key(user_id, "password")
                        )
                    except keyring.errors.PasswordDeleteError:
                        pass

                # Store SSO preference
                keyring.set_password(
                    SERVICE_NAME,
                    CredentialService._get_key(user_id, "use_sso"),
                    str(use_sso)
                )

            logger.info(f"Credentials saved for user {user_id} (SSO: {use_sso})")

            return {
                "success": True,
                "message": "Credentials saved successfully",
                "use_sso": use_sso
            }

        except Exception as e:
            logger.error(f"Error saving credentials: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }

    @staticmethod
    def get_credentials(user_id: str) -> Optional[SleeperCredentials]:
        """
        Retrieve Sleeper credentials from OS keychain

        Args:
            user_id: User identifier

        Returns:
            SleeperCredentials object or None if not found
        """
        try:
            # Use file storage if keyring is not available
            if CredentialService._use_file_storage():
                data = CredentialService._load_from_file(user_id)
                if not data:
                    logger.warning(f"No credentials found for user {user_id}")
                    return None

                return SleeperCredentials(
                    email=data.get("email", ""),
                    password=data.get("password", ""),
                    use_sso=data.get("use_sso", False)
                )
            else:
                # Get email
                email = keyring.get_password(
                    SERVICE_NAME,
                    CredentialService._get_key(user_id, "email")
                )

                if not email:
                    logger.warning(f"No credentials found for user {user_id}")
                    return None

                # Get SSO preference
                use_sso_str = keyring.get_password(
                    SERVICE_NAME,
                    CredentialService._get_key(user_id, "use_sso")
                )
                use_sso = use_sso_str == "True" if use_sso_str else False

                # Get password (if not using SSO)
                password = ""
                if not use_sso:
                    password = keyring.get_password(
                        SERVICE_NAME,
                        CredentialService._get_key(user_id, "password")
                    )
                    if not password:
                        logger.warning(f"Password not found for user {user_id}")
                        return None

                logger.info(f"Retrieved credentials for user {user_id}")

                return SleeperCredentials(
                    email=email,
                    password=password,
                    use_sso=use_sso
                )

        except Exception as e:
            logger.error(f"Error retrieving credentials: {e}", exc_info=True)
            return None

    @staticmethod
    def delete_credentials(user_id: str) -> Dict[str, any]:
        """
        Delete Sleeper credentials from OS keychain

        Args:
            user_id: User identifier

        Returns:
            Dict with success status
        """
        try:
            # Use file storage if keyring is not available
            if CredentialService._use_file_storage():
                creds_file = CredentialService._get_credentials_file(user_id)
                if creds_file.exists():
                    creds_file.unlink()
                    logger.info(f"Credentials file deleted for user {user_id}")
                return {
                    "success": True,
                    "message": "Credentials deleted successfully"
                }
            else:
                deleted_fields = []

                # Delete email
                try:
                    keyring.delete_password(
                        SERVICE_NAME,
                        CredentialService._get_key(user_id, "email")
                    )
                    deleted_fields.append("email")
                except keyring.errors.PasswordDeleteError:
                    pass

                # Delete password
                try:
                    keyring.delete_password(
                        SERVICE_NAME,
                        CredentialService._get_key(user_id, "password")
                    )
                    deleted_fields.append("password")
                except keyring.errors.PasswordDeleteError:
                    pass

                # Delete SSO preference
                try:
                    keyring.delete_password(
                        SERVICE_NAME,
                        CredentialService._get_key(user_id, "use_sso")
                    )
                    deleted_fields.append("use_sso")
                except keyring.errors.PasswordDeleteError:
                    pass

                logger.info(f"Deleted credentials for user {user_id}: {deleted_fields}")

                return {
                    "success": True,
                    "message": "Credentials deleted successfully",
                    "deleted_fields": deleted_fields
                }

        except Exception as e:
            logger.error(f"Error deleting credentials: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }

    @staticmethod
    def has_credentials(user_id: str) -> bool:
        """
        Check if credentials exist for a user

        Args:
            user_id: User identifier

        Returns:
            True if credentials exist, False otherwise
        """
        try:
            email = keyring.get_password(
                SERVICE_NAME,
                CredentialService._get_key(user_id, "email")
            )
            return email is not None

        except Exception as e:
            logger.error(f"Error checking credentials: {e}", exc_info=True)
            return False

    @staticmethod
    def test_credentials(user_id: str) -> Dict[str, any]:
        """
        Test if stored credentials are valid (just checks if they exist)

        Args:
            user_id: User identifier

        Returns:
            Dict with test results
        """
        try:
            credentials = CredentialService.get_credentials(user_id)

            if not credentials:
                return {
                    "success": False,
                    "message": "No credentials found"
                }

            # Basic validation
            if not credentials.email:
                return {
                    "success": False,
                    "message": "Email is missing"
                }

            if not credentials.use_sso and not credentials.password:
                return {
                    "success": False,
                    "message": "Password is missing"
                }

            return {
                "success": True,
                "message": "Credentials are stored and valid",
                "email": credentials.email,
                "use_sso": credentials.use_sso,
                "has_password": bool(credentials.password)
            }

        except Exception as e:
            logger.error(f"Error testing credentials: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }


# Singleton instance
credential_service = CredentialService()
