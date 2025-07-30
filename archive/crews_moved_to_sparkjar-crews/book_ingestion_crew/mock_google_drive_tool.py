"""Mock Google Drive Tool for testing without database."""
import json
from typing import List, Optional
from crewai.tools import BaseTool
from pydantic import BaseModel, Field

class MockGoogleDriveTool(BaseTool):
    """Mock tool that returns test file data."""
    
    name: str = "google_drive_tool"
    description: str = "Mock Google Drive tool for testing"
    
    def _run(self, folder_path: str, client_user_id: str, 
             file_types: List[str] = None, max_files: Optional[int] = None, 
             download: bool = True, **kwargs) -> str:
        """Return mock file list for testing."""
        
        # Create mock files following baron naming convention
        mock_files = []
        
        # First 25 pages (baron001 group)
        # Page 1
        mock_files.append({
            "file_id": "mock_001_base",
            "file_name": "baron001.png",
            "calculated_page_number": 1,
            "mime_type": "image/png"
        })
        
        # Pages 2-25
        for i in range(1, 25):
            mock_files.append({
                "file_id": f"mock_001_{i}",
                "file_name": f"baron001 {i}.png",
                "calculated_page_number": i + 1,
                "mime_type": "image/png"
            })
        
        return json.dumps({
            "status": "success",
            "files": mock_files,
            "total": len(mock_files),
            "folder_path": folder_path
        })
    
    def _upload(self, **kwargs) -> str:
        """Mock upload - not implemented."""
        return json.dumps({
            "status": "error",
            "error": "Upload not available in mock mode"
        })