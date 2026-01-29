"""Test for Fix #1: MinIO presigned URL endpoint"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.db.miniodb import AsyncMinIOManager


@pytest.mark.asyncio
async def test_presigned_url_uses_minio_url_not_server_ip():
    """
    CRITICAL FIX #1 VALIDATION
    
    Verify that create_presigned_url uses settings.minio_url
    instead of settings.server_ip
    
    This ensures presigned URLs point to the correct MinIO endpoint
    for file downloads.
    """
    manager = AsyncMinIOManager()
    
    # Mock the settings to verify the correct endpoint is used
    with patch('app.db.miniodb.settings') as mock_settings:
        mock_settings.minio_url = 'http://minio:9000'
        mock_settings.minio_public_url = 'http://localhost:9000'
        mock_settings.minio_bucket_name = 'test-bucket'
        mock_settings.minio_access_key = 'test-key'
        mock_settings.minio_secret_key = 'test-secret'
        mock_settings.server_ip = 'http://localhost:8090'  # WRONG endpoint
        
        # Mock the S3 client
        mock_client = AsyncMock()
        mock_client.generate_presigned_url = AsyncMock(
            return_value='http://localhost:9000/test-bucket/test-file.pdf?...'
        )
        
        with patch.object(manager.session, 'client') as mock_session_client:
            # Setup context manager mock
            mock_session_client.return_value.__aenter__.return_value = mock_client
            
            # Call the method
            url = await manager.create_presigned_url('test-file.pdf')
            
            # Verify correct endpoint was used
            mock_session_client.assert_called_once()
            call_args = mock_session_client.call_args
            
            # Extract endpoint_url from kwargs
            endpoint_url = call_args.kwargs.get('endpoint_url')
            
            # VERIFY FIX: endpoint_url should be minio_public_url, not server_ip
            assert endpoint_url == 'http://localhost:9000', \
                f"Expected minio_public_url (http://localhost:9000) but got {endpoint_url}"
            assert endpoint_url != 'http://localhost:8090', \
                "Should NOT use server_ip for presigned URLs"


@pytest.mark.asyncio
async def test_presigned_url_calls_generate_presigned_url():
    """
    Verify that the presigned URL generation calls the correct S3 method
    with proper parameters.
    """
    manager = AsyncMinIOManager()
    manager.bucket_name = 'test-bucket'
    
    mock_client = AsyncMock()
    mock_url = 'http://minio:9000/test-bucket/file.pdf?signed=token'
    mock_client.generate_presigned_url = AsyncMock(return_value=mock_url)
    
    with patch.object(manager.session, 'client') as mock_session_client:
        mock_session_client.return_value.__aenter__.return_value = mock_client
        
        result = await manager.create_presigned_url('file.pdf', expires=3600)
        
        # Verify the call
        mock_client.generate_presigned_url.assert_called_once()
        call_args = mock_client.generate_presigned_url.call_args
        
        assert call_args.kwargs['ExpiresIn'] == 3600
        assert call_args.kwargs['Params']['Bucket'] == 'test-bucket'
        assert call_args.kwargs['Params']['Key'] == 'file.pdf'
        assert result == mock_url
