import os
import boto3
from botocore.exceptions import ClientError
import logging
from typing import Optional, BinaryIO, Dict
from datetime import timedelta

logger = logging.getLogger(__name__)

class R2Service:
    """Service for interacting with Cloudflare R2 storage"""
    
    def __init__(self):
        """Initialize R2 client with credentials from environment"""
        self.account_id = os.environ.get('CLOUDFLARE_ACCOUNT_ID')
        self.access_key_id = os.environ.get('CLOUDFLARE_ACCESS_KEY_ID')
        self.secret_access_key = os.environ.get('CLOUDFLARE_SECRET_ACCESS_KEY')
        self.endpoint = os.environ.get('R2_ENDPOINT')
        self.public_url = os.environ.get('R2_PUBLIC_URL', '')
        
        # Bucket names
        self.bucket_preset_videos = os.environ.get('R2_BUCKET_PRESET_VIDEOS', 'app-preset-videos')
        self.bucket_user_videos = os.environ.get('R2_BUCKET_USER_VIDEOS', 'app-user-videos')
        self.bucket_user_audio = os.environ.get('R2_BUCKET_USER_AUDIO', 'app-user-audio')
        self.bucket_user_texts = os.environ.get('R2_BUCKET_USER_TEXTS', 'app-user-texts')
        
        if not all([self.account_id, self.access_key_id, self.secret_access_key, self.endpoint]):
            raise ValueError("R2 credentials not properly configured in environment variables")
        
        # Initialize boto3 S3 client for R2
        self.client = boto3.client(
            's3',
            endpoint_url=self.endpoint,
            aws_access_key_id=self.access_key_id,
            aws_secret_access_key=self.secret_access_key,
            region_name='auto'
        )
        
        logger.info(f"✅ R2 Service initialized with endpoint: {self.endpoint}")
    
    def upload_file(
        self,
        file_path: str,
        bucket_name: str,
        object_key: str,
        content_type: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None
    ) -> str:
        """
        Upload a file to R2
        
        Args:
            file_path: Local path to file
            bucket_name: Target bucket name
            object_key: Object key (path) in bucket
            content_type: MIME type of file
            metadata: Custom metadata dict
            
        Returns:
            Object key of uploaded file
        """
        try:
            extra_args = {}
            if content_type:
                extra_args['ContentType'] = content_type
            if metadata:
                extra_args['Metadata'] = metadata
            
            self.client.upload_file(
                file_path,
                bucket_name,
                object_key,
                ExtraArgs=extra_args
            )
            
            logger.info(f"✅ Uploaded file to R2: {bucket_name}/{object_key}")
            return object_key
            
        except ClientError as e:
            logger.error(f"Error uploading file to R2: {e}")
            raise
    
    def upload_fileobj(
        self,
        file_obj: BinaryIO,
        bucket_name: str,
        object_key: str,
        content_type: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None
    ) -> str:
        """
        Upload a file object to R2
        
        Args:
            file_obj: File-like object
            bucket_name: Target bucket name
            object_key: Object key (path) in bucket
            content_type: MIME type of file
            metadata: Custom metadata dict
            
        Returns:
            Object key of uploaded file
        """
        try:
            extra_args = {}
            if content_type:
                extra_args['ContentType'] = content_type
            if metadata:
                extra_args['Metadata'] = metadata
            
            self.client.upload_fileobj(
                file_obj,
                bucket_name,
                object_key,
                ExtraArgs=extra_args
            )
            
            logger.info(f"✅ Uploaded file object to R2: {bucket_name}/{object_key}")
            return object_key
            
        except ClientError as e:
            logger.error(f"Error uploading file object to R2: {e}")
            raise
    
    def download_file(
        self,
        bucket_name: str,
        object_key: str,
        local_path: str
    ) -> str:
        """
        Download a file from R2
        
        Args:
            bucket_name: Source bucket name
            object_key: Object key in bucket
            local_path: Local path to save file
            
        Returns:
            Local path where file was saved
        """
        try:
            self.client.download_file(bucket_name, object_key, local_path)
            logger.info(f"✅ Downloaded file from R2: {bucket_name}/{object_key} to {local_path}")
            return local_path
            
        except ClientError as e:
            logger.error(f"Error downloading file from R2: {e}")
            raise
    
    def get_file_object(self, bucket_name: str, object_key: str):
        """
        Get file object from R2 for streaming
        
        Args:
            bucket_name: Source bucket name
            object_key: Object key in bucket
            
        Returns:
            Boto3 streaming body object
        """
        try:
            response = self.client.get_object(Bucket=bucket_name, Key=object_key)
            return response['Body']
            
        except ClientError as e:
            logger.error(f"Error getting file object from R2: {e}")
            raise
    
    def delete_file(self, bucket_name: str, object_key: str) -> bool:
        """
        Delete a file from R2
        
        Args:
            bucket_name: Bucket name
            object_key: Object key to delete
            
        Returns:
            True if successful
        """
        try:
            self.client.delete_object(Bucket=bucket_name, Key=object_key)
            logger.info(f"✅ Deleted file from R2: {bucket_name}/{object_key}")
            return True
            
        except ClientError as e:
            logger.error(f"Error deleting file from R2: {e}")
            raise
    
    def file_exists(self, bucket_name: str, object_key: str) -> bool:
        """
        Check if file exists in R2
        
        Args:
            bucket_name: Bucket name
            object_key: Object key to check
            
        Returns:
            True if file exists
        """
        try:
            self.client.head_object(Bucket=bucket_name, Key=object_key)
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                return False
            raise
    
    def generate_presigned_url(
        self,
        bucket_name: str,
        object_key: str,
        expiration: int = 3600
    ) -> str:
        """
        Generate presigned URL for temporary access
        
        Args:
            bucket_name: Bucket name
            object_key: Object key
            expiration: URL expiration in seconds (default 1 hour)
            
        Returns:
            Presigned URL string
        """
        try:
            url = self.client.generate_presigned_url(
                'get_object',
                Params={'Bucket': bucket_name, 'Key': object_key},
                ExpiresIn=expiration
            )
            logger.info(f"Generated presigned URL for {bucket_name}/{object_key} (expires in {expiration}s)")
            return url
            
        except ClientError as e:
            logger.error(f"Error generating presigned URL: {e}")
            raise
    
    def list_files(
        self,
        bucket_name: str,
        prefix: str = '',
        max_keys: int = 1000
    ) -> list:
        """
        List files in bucket with optional prefix
        
        Args:
            bucket_name: Bucket name
            prefix: Key prefix to filter
            max_keys: Maximum number of keys to return
            
        Returns:
            List of file metadata dicts
        """
        try:
            response = self.client.list_objects_v2(
                Bucket=bucket_name,
                Prefix=prefix,
                MaxKeys=max_keys
            )
            
            files = []
            for obj in response.get('Contents', []):
                files.append({
                    'key': obj['Key'],
                    'size': obj['Size'],
                    'last_modified': obj['LastModified'].isoformat(),
                    'etag': obj['ETag']
                })
            
            logger.info(f"Listed {len(files)} files from {bucket_name} with prefix '{prefix}'")
            return files
            
        except ClientError as e:
            logger.error(f"Error listing files from R2: {e}")
            raise
    
    def get_public_url(self, bucket_name: str, object_key: str) -> str:
        """
        Get public URL for a file (if bucket has public access enabled)
        
        Args:
            bucket_name: Bucket name
            object_key: Object key
            
        Returns:
            Public URL string
        """
        # For now, return presigned URL with long expiration
        # You can enable R2 public buckets and use: https://pub-{account_id}.r2.dev/{object_key}
        return self.generate_presigned_url(bucket_name, object_key, expiration=86400)  # 24 hours


# Global R2 service instance
r2_service = None

def get_r2_service() -> R2Service:
    """Get or create global R2 service instance"""
    global r2_service
    if r2_service is None:
        r2_service = R2Service()
    return r2_service
