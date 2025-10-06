"""
Storage service abstraction for NGL
Supports both local filesystem and AWS S3 storage
"""
from abc import ABC, abstractmethod
import os
import logging
from typing import Optional, BinaryIO
from database import SessionLocal
from models import S3Configuration

logger = logging.getLogger(__name__)


class StorageService(ABC):
    """Abstract base class for storage services"""

    @abstractmethod
    def save_file(self, file_data: BinaryIO, filepath: str) -> str:
        """
        Save a file to storage

        Args:
            file_data: File-like object containing the data
            filepath: Desired path/key for the file

        Returns:
            str: The actual path/key where the file was stored
        """
        pass

    @abstractmethod
    def get_file(self, filepath: str) -> Optional[str]:
        """
        Get a file from storage

        Args:
            filepath: Path/key of the file

        Returns:
            str: Local path to the file, or presigned URL for S3
        """
        pass

    @abstractmethod
    def delete_file(self, filepath: str) -> bool:
        """
        Delete a file from storage

        Args:
            filepath: Path/key of the file

        Returns:
            bool: True if successful, False otherwise
        """
        pass

    @abstractmethod
    def file_exists(self, filepath: str) -> bool:
        """
        Check if a file exists in storage

        Args:
            filepath: Path/key of the file

        Returns:
            bool: True if file exists, False otherwise
        """
        pass

    @abstractmethod
    def get_storage_type(self) -> str:
        """
        Get the storage type identifier

        Returns:
            str: 'local' or 's3'
        """
        pass


class LocalStorageService(StorageService):
    """Local filesystem storage implementation"""

    def __init__(self, base_path: str = '/app/uploads'):
        self.base_path = base_path
        os.makedirs(base_path, exist_ok=True)

    def save_file(self, file_data: BinaryIO, filepath: str) -> str:
        """Save file to local filesystem"""
        full_path = os.path.join(self.base_path, filepath)

        # Ensure directory exists
        os.makedirs(os.path.dirname(full_path), exist_ok=True)

        # Save file
        with open(full_path, 'wb') as f:
            file_data.seek(0)
            f.write(file_data.read())

        logger.info(f"Saved file to local storage: {full_path}")
        return full_path

    def get_file(self, filepath: str) -> Optional[str]:
        """Get file path from local filesystem"""
        if os.path.isabs(filepath):
            # Already an absolute path
            return filepath if os.path.exists(filepath) else None

        full_path = os.path.join(self.base_path, filepath)
        return full_path if os.path.exists(full_path) else None

    def delete_file(self, filepath: str) -> bool:
        """Delete file from local filesystem"""
        try:
            if os.path.exists(filepath):
                os.remove(filepath)
                logger.info(f"Deleted file from local storage: {filepath}")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to delete file {filepath}: {str(e)}")
            return False

    def file_exists(self, filepath: str) -> bool:
        """Check if file exists in local filesystem"""
        return os.path.exists(filepath)

    def get_storage_type(self) -> str:
        return 'local'


class S3StorageService(StorageService):
    """AWS S3 storage implementation"""

    def __init__(self, config: S3Configuration):
        try:
            import boto3
            from botocore.exceptions import ClientError

            self.config = config
            self.ClientError = ClientError

            # Initialize S3 client
            self.s3_client = boto3.client(
                's3',
                aws_access_key_id=config.aws_access_key_id,
                aws_secret_access_key=config.aws_secret_access_key,
                region_name=config.region
            )

            logger.info(f"Initialized S3 storage service for bucket: {config.bucket_name}")
        except ImportError:
            raise ImportError("boto3 is required for S3 storage. Install with: pip install boto3")

    def save_file(self, file_data: BinaryIO, filepath: str) -> str:
        """Save file to S3"""
        try:
            # Use the filename as S3 key
            s3_key = os.path.basename(filepath)

            # Prepare extra args for encryption
            extra_args = {}
            if self.config.server_side_encryption:
                extra_args['ServerSideEncryption'] = 'AES256'

            # Upload to S3
            file_data.seek(0)
            self.s3_client.upload_fileobj(
                file_data,
                self.config.bucket_name,
                s3_key,
                ExtraArgs=extra_args
            )

            logger.info(f"Saved file to S3: s3://{self.config.bucket_name}/{s3_key}")
            return s3_key

        except self.ClientError as e:
            logger.error(f"Failed to upload file to S3: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error uploading to S3: {str(e)}")
            raise

    def get_file(self, s3_key: str) -> Optional[str]:
        """Get presigned URL for S3 file"""
        try:
            # Generate presigned URL (expires in 1 hour)
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': self.config.bucket_name,
                    'Key': s3_key
                },
                ExpiresIn=3600  # 1 hour
            )

            logger.info(f"Generated presigned URL for: {s3_key}")
            return url

        except self.ClientError as e:
            logger.error(f"Failed to generate presigned URL for {s3_key}: {str(e)}")
            return None

    def delete_file(self, s3_key: str) -> bool:
        """Delete file from S3"""
        try:
            self.s3_client.delete_object(
                Bucket=self.config.bucket_name,
                Key=s3_key
            )
            logger.info(f"Deleted file from S3: {s3_key}")
            return True

        except self.ClientError as e:
            logger.error(f"Failed to delete file from S3 {s3_key}: {str(e)}")
            return False

    def file_exists(self, s3_key: str) -> bool:
        """Check if file exists in S3"""
        try:
            self.s3_client.head_object(
                Bucket=self.config.bucket_name,
                Key=s3_key
            )
            return True
        except self.ClientError:
            return False

    def get_storage_type(self) -> str:
        return 's3'


class StorageFactory:
    """Factory to create appropriate storage service based on configuration"""

    @staticmethod
    def get_storage_service() -> StorageService:
        """
        Get the active storage service based on configuration

        Returns:
            StorageService: Active storage service (S3 or Local)
        """
        db = SessionLocal()
        try:
            # Check if S3 is configured and enabled
            s3_config = db.query(S3Configuration).first()

            if s3_config and s3_config.is_enabled:
                try:
                    # Try to create S3 service
                    logger.info("S3 storage is enabled, using S3StorageService")
                    return S3StorageService(s3_config)
                except Exception as e:
                    logger.error(f"Failed to initialize S3 storage, falling back to local: {str(e)}")
                    # Fall back to local storage
                    return LocalStorageService()
            else:
                logger.info("S3 not configured or disabled, using LocalStorageService")
                return LocalStorageService()

        finally:
            db.close()

    @staticmethod
    def test_s3_connection(config: S3Configuration) -> tuple[bool, str]:
        """
        Test S3 connection by creating and deleting a test file

        Args:
            config: S3Configuration object

        Returns:
            tuple: (success: bool, message: str)
        """
        try:
            # Create S3 service with provided config
            service = S3StorageService(config)

            # Create test file
            test_key = '.ngl_connection_test'
            test_content = b'NGL S3 Connection Test'

            import io
            test_file = io.BytesIO(test_content)

            # Try to upload
            service.save_file(test_file, test_key)

            # Try to check existence
            if not service.file_exists(test_key):
                return False, "File upload succeeded but file not found in bucket"

            # Try to delete
            if not service.delete_file(test_key):
                return False, "File upload succeeded but failed to delete test file"

            return True, f"Successfully connected to S3 bucket: {config.bucket_name}"

        except Exception as e:
            error_msg = str(e)
            logger.error(f"S3 connection test failed: {error_msg}")
            return False, f"Connection failed: {error_msg}"
