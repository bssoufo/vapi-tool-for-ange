from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field, ConfigDict
from enum import Enum


class VoiceProvider(str, Enum):
    MINIMAX = "minimax"
    OPENAI = "openai"
    ELEVEN_LABS = "eleven_labs"
    ELEVENLABS = "elevenlabs"
    AZURE = "azure"
    PLAYHT = "playht"
    DEEPGRAM = "deepgram"


class ModelProvider(str, Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GROQ = "groq"
    AZURE = "azure"


class TranscriberProvider(str, Enum):
    DEEPGRAM = "deepgram"
    WHISPER = "whisper"
    AZURE = "azure"


class ToolType(str, Enum):
    END_CALL = "endCall"
    TRANSFER_CALL = "transferCall"
    FUNCTION = "function"


class FirstMessageMode(str, Enum):
    ASSISTANT_SPEAKS_FIRST = "assistant-speaks-first"
    ASSISTANT_SPEAKS_FIRST_WITH_MODEL_GENERATED_MESSAGE = "assistant-speaks-first-with-model-generated-message"
    WAIT_FOR_USER = "wait-for-user"


class Voice(BaseModel):
    model_config = ConfigDict(extra="allow")

    voice_id: Optional[str] = Field(None, alias="voiceId")
    provider: str


class TransferDestination(BaseModel):
    type: str
    number: Optional[str] = None
    description: Optional[str] = None


class Tool(BaseModel):
    model_config = ConfigDict(extra="allow")

    type: ToolType
    destinations: Optional[List[TransferDestination]] = None
    server: Optional[Dict[str, Any]] = None
    function: Optional[Dict[str, Any]] = None


class ModelConfig(BaseModel):
    model_config = ConfigDict(extra="allow")

    model: str
    provider: ModelProvider
    temperature: Optional[float] = None
    tools: Optional[List[Tool]] = None
    tool_ids: Optional[List[str]] = Field(None, alias="toolIds")
    messages: Optional[List[Dict[str, str]]] = None


class Transcriber(BaseModel):
    model_config = ConfigDict(extra="allow")

    model: str
    provider: TranscriberProvider
    language: Optional[str] = None


class Server(BaseModel):
    url: str
    timeout_seconds: Optional[int] = Field(None, alias="timeoutSeconds")


class SummaryPlan(BaseModel):
    enabled: bool
    messages: Optional[List[Dict[str, str]]] = None
    timeout_seconds: Optional[int] = Field(None, alias="timeoutSeconds")


class StructuredDataPlan(BaseModel):
    enabled: bool
    schema_: Optional[Dict[str, Any]] = Field(None, alias="schema")
    messages: Optional[List[Dict[str, str]]] = None
    timeout_seconds: Optional[int] = Field(None, alias="timeoutSeconds")


class AnalysisPlan(BaseModel):
    model_config = ConfigDict(extra="allow")

    min_messages_threshold: Optional[int] = Field(None, alias="minMessagesThreshold")
    summary_plan: Optional[SummaryPlan] = Field(None, alias="summaryPlan")
    structured_data_plan: Optional[StructuredDataPlan] = Field(None, alias="structuredDataPlan")


class Assistant(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: Optional[str] = None
    org_id: Optional[str] = Field(None, alias="orgId")
    name: str
    voice: Optional[Voice] = None
    model: ModelConfig
    transcriber: Optional[Transcriber] = None
    first_message: Optional[str] = Field(None, alias="firstMessage")
    first_message_mode: Optional[FirstMessageMode] = Field(None, alias="firstMessageMode")
    server_messages: Optional[List[str]] = Field(None, alias="serverMessages")
    analysis_plan: Optional[AnalysisPlan] = Field(None, alias="analysisPlan")
    server: Optional[Server] = None
    is_server_url_secret_set: Optional[bool] = Field(None, alias="isServerUrlSecretSet")
    created_at: Optional[datetime] = Field(None, alias="createdAt")
    updated_at: Optional[datetime] = Field(None, alias="updatedAt")


class AssistantCreateRequest(BaseModel):
    name: str
    voice: Voice
    model: ModelConfig
    transcriber: Optional[Transcriber] = None
    first_message: Optional[str] = Field(None, alias="firstMessage")
    first_message_mode: Optional[FirstMessageMode] = Field(None, alias="firstMessageMode")
    server_messages: Optional[List[str]] = Field(None, alias="serverMessages")
    analysis_plan: Optional[AnalysisPlan] = Field(None, alias="analysisPlan")
    server: Optional[Server] = None


class AssistantUpdateRequest(BaseModel):
    name: Optional[str] = None
    voice: Optional[Voice] = None
    model: Optional[ModelConfig] = None
    transcriber: Optional[Transcriber] = None
    first_message: Optional[str] = Field(None, alias="firstMessage")
    first_message_mode: Optional[FirstMessageMode] = Field(None, alias="firstMessageMode")
    server_messages: Optional[List[str]] = Field(None, alias="serverMessages")
    analysis_plan: Optional[AnalysisPlan] = Field(None, alias="analysisPlan")
    server: Optional[Server] = None