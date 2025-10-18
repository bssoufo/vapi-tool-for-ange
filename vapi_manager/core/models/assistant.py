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


class ToolMessageType(str, Enum):
    """Types of messages that can be spoken during tool execution.

    - REQUEST_START: Spoken when the tool call begins
    - REQUEST_COMPLETE: Spoken when the tool call completes successfully
    - REQUEST_FAILED: Spoken when the tool call fails
    - REQUEST_RESPONSE_DELAYED: Spoken when the tool response is delayed beyond a threshold
    """
    REQUEST_START = "request-start"
    REQUEST_COMPLETE = "request-complete"
    REQUEST_FAILED = "request-failed"
    REQUEST_RESPONSE_DELAYED = "request-response-delayed"


class ToolMessageContent(BaseModel):
    """Content structure for tool messages."""
    type: str = "text"
    text: str
    language: Optional[str] = "en"


class ToolMessage(BaseModel):
    """Message configuration for tool execution states.

    Allows the assistant to speak during different stages of tool execution.

    Attributes:
        type: The message type (request-start, request-complete, etc.)
        contents: Array of content objects (VAPI API format)
        content: Simplified string content (YAML format, auto-converted to contents)
        timing_milliseconds: Delay in milliseconds before speaking this message
        language: Language code for the message (default: 'en')

    Example YAML:
        messages:
          - type: request-start
            content: "Let me check that for you..."
          - type: request-complete
            content: "I found the information!"
          - type: request-response-delayed
            content: "Still working on it..."
            timingMilliseconds: 5000
    """
    model_config = ConfigDict(extra="allow")

    type: ToolMessageType
    contents: Optional[List[ToolMessageContent]] = None
    content: Optional[str] = None  # Simplified content for YAML
    timing_milliseconds: Optional[int] = Field(None, alias="timingMilliseconds")
    language: Optional[str] = None


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
    messages: Optional[List[ToolMessage]] = None  # Tool execution messages


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

    model: Optional[str] = None
    provider: TranscriberProvider
    language: Optional[str] = None


class Server(BaseModel):
    url: str
    timeout_seconds: Optional[int] = Field(None, alias="timeoutSeconds")


class SummaryPlan(BaseModel):
    enabled: bool = Field(default=False)  # Default to False if not provided
    messages: Optional[List[Dict[str, str]]] = None
    timeout_seconds: Optional[int] = Field(None, alias="timeoutSeconds")


class StructuredDataPlan(BaseModel):
    enabled: bool = Field(default=False)  # Default to False if not provided
    schema_: Optional[Dict[str, Any]] = Field(None, alias="schema")
    messages: Optional[List[Dict[str, str]]] = None
    timeout_seconds: Optional[int] = Field(None, alias="timeoutSeconds")


class AnalysisPlan(BaseModel):
    model_config = ConfigDict(extra="allow")

    min_messages_threshold: Optional[int] = Field(None, alias="minMessagesThreshold")
    summary_plan: Optional[SummaryPlan] = Field(None, alias="summaryPlan")
    structured_data_plan: Optional[StructuredDataPlan] = Field(None, alias="structuredDataPlan")


class SmartDenoisingPlan(BaseModel):
    """AI-powered smart denoising configuration.

    Uses machine learning to intelligently detect and remove background noise
    while preserving speech quality.
    """
    model_config = ConfigDict(extra="allow")

    enabled: bool = Field(default=False, description="Enable smart denoising")


class FourierDenoisingPlan(BaseModel):
    """Fourier-based denoising configuration with advanced controls.

    Uses frequency domain analysis to remove background noise with fine-grained control.
    """
    model_config = ConfigDict(extra="allow")

    enabled: bool = Field(default=False, description="Enable Fourier denoising")
    media_detection_enabled: Optional[bool] = Field(
        True,
        alias="mediaDetectionEnabled",
        description="Automatically detect and preserve media (music, TV, etc.)"
    )
    static_threshold: Optional[int] = Field(
        -35,
        alias="staticThreshold",
        description="Noise floor threshold in dB (default: -35)"
    )
    baseline_offset_db: Optional[int] = Field(
        -15,
        alias="baselineOffsetDb",
        description="Offset from baseline noise level in dB (default: -15)"
    )
    window_size_ms: Optional[int] = Field(
        3000,
        alias="windowSizeMs",
        description="Analysis window size in milliseconds (default: 3000)"
    )
    baseline_percentile: Optional[int] = Field(
        85,
        alias="baselinePercentile",
        description="Percentile for baseline noise calculation (default: 85)"
    )


class BackgroundSpeechDenoisingPlan(BaseModel):
    """Background speech denoising configuration.

    Supports two denoising methods:
    1. Smart Denoising: AI-powered, recommended for most use cases
    2. Fourier Denoising: Advanced frequency-based denoising with fine-grained control

    You can enable both methods simultaneously or choose one.
    """
    model_config = ConfigDict(extra="allow")

    smart_denoising_plan: Optional[SmartDenoisingPlan] = Field(
        None,
        alias="smartDenoisingPlan",
        description="AI-powered smart denoising configuration"
    )
    fourier_denoising_plan: Optional[FourierDenoisingPlan] = Field(
        None,
        alias="fourierDenoisingPlan",
        description="Fourier-based denoising configuration"
    )


class HookAction(BaseModel):
    """Action to perform when a hook is triggered."""
    model_config = ConfigDict(extra="allow")

    type: str  # e.g., "say"
    exact: Optional[str] = None  # Exact message to say (static)
    prompt: Optional[str] = None  # Prompt for model-generated message (contextual)


class HookOptions(BaseModel):
    """Options for hook configuration."""
    model_config = ConfigDict(extra="allow")

    timeout_seconds: Optional[int] = Field(None, alias="timeoutSeconds")
    trigger_max_count: Optional[int] = Field(None, alias="triggerMaxCount")
    trigger_reset_mode: Optional[str] = Field(None, alias="triggerResetMode")


class Hook(BaseModel):
    """Hook configuration for event-driven actions like idle messages."""
    model_config = ConfigDict(extra="allow")

    on: str  # Event name, e.g., "customer.speech.timeout"
    options: Optional[HookOptions] = None
    do: Optional[List[HookAction]] = None


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
    background_speech_denoising_plan: Optional[BackgroundSpeechDenoisingPlan] = Field(
        None,
        alias="backgroundSpeechDenoisingPlan",
        description="Background speech denoising configuration"
    )
    hooks: Optional[List[Hook]] = None
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
    background_speech_denoising_plan: Optional[BackgroundSpeechDenoisingPlan] = Field(
        None,
        alias="backgroundSpeechDenoisingPlan",
        description="Background speech denoising configuration"
    )
    hooks: Optional[List[Hook]] = None
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
    background_speech_denoising_plan: Optional[BackgroundSpeechDenoisingPlan] = Field(
        None,
        alias="backgroundSpeechDenoisingPlan",
        description="Background speech denoising configuration"
    )
    hooks: Optional[List[Hook]] = None
    server: Optional[Server] = None