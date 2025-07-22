"""Mock objects for external services used in tests."""
from unittest.mock import MagicMock, AsyncMock
import json
from typing import Dict, Any, List

class MockChromaCollection:
    """Mock ChromaDB collection."""
    
    def __init__(self, name: str):
        self.name = name
        self._documents = []
        self._embeddings = []
        self._metadatas = []
        self._ids = []
    
    def add(self, documents=None, embeddings=None, metadatas=None, ids=None):
        """Mock add method."""
        if documents:
            self._documents.extend(documents)
        if embeddings:
            self._embeddings.extend(embeddings)
        if metadatas:
            self._metadatas.extend(metadatas)
        if ids:
            self._ids.extend(ids)
    
    def query(self, query_texts=None, query_embeddings=None, n_results=10, **kwargs):
        """Mock query method."""
        return {
            'ids': [self._ids[:n_results] if self._ids else []],
            'distances': [[0.1, 0.2, 0.3][:n_results]],
            'documents': [self._documents[:n_results] if self._documents else []],
            'metadatas': [self._metadatas[:n_results] if self._metadatas else []]
        }
    
    def get(self, ids=None, **kwargs):
        """Mock get method."""
        return {
            'ids': self._ids,
            'documents': self._documents,
            'metadatas': self._metadatas
        }

class MockChromaClient:
    """Mock ChromaDB client."""
    
    def __init__(self):
        self._collections = {}
    
    def list_collections(self):
        """Mock list collections."""
        return [MagicMock(name=name) for name in self._collections.keys()]
    
    def get_or_create_collection(self, name: str, **kwargs):
        """Mock get or create collection."""
        if name not in self._collections:
            self._collections[name] = MockChromaCollection(name)
        return self._collections[name]
    
    def get_collection(self, name: str):
        """Mock get collection."""
        if name not in self._collections:
            raise ValueError(f"Collection {name} does not exist")
        return self._collections[name]
    
    def delete_collection(self, name: str):
        """Mock delete collection."""
        if name in self._collections:
            del self._collections[name]

class MockOpenAIResponse:
    """Mock OpenAI API response."""
    
    def __init__(self, content: str = "Test AI response"):
        self.choices = [
            MagicMock(
                message=MagicMock(content=content),
                finish_reason="stop"
            )
        ]
        self.usage = MagicMock(
            prompt_tokens=10,
            completion_tokens=20,
            total_tokens=30
        )

class MockOpenAIClient:
    """Mock OpenAI client."""
    
    def __init__(self):
        self.chat = MagicMock()
        self.chat.completions = MagicMock()
        self.chat.completions.create = AsyncMock(
            return_value=MockOpenAIResponse()
        )
        
        self.embeddings = MagicMock()
        self.embeddings.create = AsyncMock(
            return_value=MagicMock(
                data=[MagicMock(embedding=[0.1] * 1536)]
            )
        )

class MockGoogleDriveService:
    """Mock Google Drive service."""
    
    def __init__(self):
        self._files = {
            'test_file_id': {
                'id': 'test_file_id',
                'name': 'test_file.txt',
                'mimeType': 'text/plain',
                'parents': ['test_folder_id']
            }
        }
        self._folders = {
            'test_folder_id': {
                'id': 'test_folder_id',
                'name': 'Test Folder',
                'mimeType': 'application/vnd.google-apps.folder'
            }
        }
    
    def files(self):
        """Mock files resource."""
        mock_files = MagicMock()
        mock_files.list.return_value.execute.return_value = {
            'files': list(self._files.values()) + list(self._folders.values())
        }
        mock_files.get.return_value.execute.return_value = self._files['test_file_id']
        mock_files.get_media.return_value.execute.return_value = b"Test file content"
        return mock_files

class MockCrewAIAgent:
    """Mock CrewAI Agent."""
    
    def __init__(self, role="Test Agent", goal="Test goal", backstory="Test backstory", **kwargs):
        self.role = role
        self.goal = goal
        self.backstory = backstory
        self.tools = kwargs.get('tools', [])
        self.llm = kwargs.get('llm')

class MockCrewAITask:
    """Mock CrewAI Task."""
    
    def __init__(self, description="Test task", agent=None, **kwargs):
        self.description = description
        self.agent = agent or MockCrewAIAgent()
        self.expected_output = kwargs.get('expected_output', "Test output")

class MockCrewAICrew:
    """Mock CrewAI Crew."""
    
    def __init__(self, agents=None, tasks=None, **kwargs):
        self.agents = agents or [MockCrewAIAgent()]
        self.tasks = tasks or [MockCrewAITask()]
        self.process = kwargs.get('process', 'sequential')
        self.memory = kwargs.get('memory', False)
    
    def kickoff(self, inputs=None):
        """Mock crew execution."""
        return MagicMock(
            raw="Test crew execution result",
            tasks_output=[
                MagicMock(
                    raw="Test task output",
                    description="Test task description"
                )
            ],
            json_dict={"result": "test"},
            token_usage={"total_tokens": 100}
        )

def get_mock_chroma_client():
    """Get a mock ChromaDB client."""
    return MockChromaClient()

def get_mock_openai_client():
    """Get a mock OpenAI client."""
    return MockOpenAIClient()

def get_mock_google_drive_service():
    """Get a mock Google Drive service."""
    return MockGoogleDriveService()

# Patch functions for easy mocking in tests
def patch_external_services(monkeypatch):
    """Patch all external services with mocks."""
    # ChromaDB
    monkeypatch.setattr(
        "src.utils.chroma_client.get_chroma_client",
        get_mock_chroma_client
    )
    
    # OpenAI
    monkeypatch.setattr(
        "openai.AsyncOpenAI",
        lambda **kwargs: get_mock_openai_client()
    )
    
    # Google Drive
    monkeypatch.setattr(
        "src.tools.google_drive_tool.build",
        lambda service, version, credentials: get_mock_google_drive_service()
    )
    
    # CrewAI components
    monkeypatch.setattr("crewai.Agent", MockCrewAIAgent)
    monkeypatch.setattr("crewai.Task", MockCrewAITask)
    monkeypatch.setattr("crewai.Crew", MockCrewAICrew)