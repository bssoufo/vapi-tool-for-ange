# Pronunciation Dictionaries Configuration Guide

## Overview

Pronunciation dictionaries allow you to control how your AI assistant pronounces specific words and phrases. This is essential for:
- Brand names (e.g., "Anthropic", "Vapi")
- Technical terms and jargon
- Acronyms (e.g., "UN", "NASA")
- Names with unusual pronunciations
- Industry-specific terminology

When your assistant encounters specified words during conversation, it will automatically use your custom pronunciations.

**Important:**
- Pronunciation dictionaries are **provider-specific** and currently only supported by **ElevenLabs** voice provider (`11labs`)
- **Requires ElevenLabs integration**: You must have ElevenLabs properly configured with your Vapi account
- **IPA format**: When using IPA phonemes, they must be wrapped in forward slashes (e.g., `/həˈloʊ/`)
- **Account permissions**: Dictionary creation requires proper API permissions for ElevenLabs features

## How It Works

1. **Create a pronunciation dictionary** with custom rules via the Vapi API
2. **Get the dictionary ID** from the API response
3. **Reference the dictionary ID** in your assistant's voice configuration
4. When the assistant speaks, it uses your custom pronunciations automatically

**Note:** When a pronunciation dictionary is added, SSML parsing will be automatically enabled for your assistant.

## Pronunciation Rule Types

### 1. Phoneme Rules

Specifies exact pronunciation using phonetic alphabets. Provides the most precise control.

**Supported Alphabets:**
- **IPA** (International Phonetic Alphabet) - Standard phonetic notation
- **CMU** (CMU Arpabet) - Computer-readable phonetic notation

**Example:**
```yaml
- type: phoneme
  string: Anthropic
  phoneme: /ænˈθɹɑpɪk/  # Must wrap in forward slashes
  alphabet: ipa
```

### 2. Alias Rules

Replaces words with alternative spellings or phrases. Works with all ElevenLabs models.

**Use cases:**
- Convert acronyms to full words
- Replace technical terms with spoken equivalents
- Simplify complex terminology

**Example:**
```yaml
- type: alias
  string: UN
  alias: United Nations
```

## Creating Pronunciation Dictionaries

### Using Python API

```python
import asyncio
from vapi_manager.services import PronunciationDictionaryService

async def create_dictionary():
    service = PronunciationDictionaryService()

    # Define pronunciation rules
    rules = [
        {
            "type": "phoneme",
            "string": "Anthropic",
            "phoneme": "/ænˈθɹɑpɪk/",
            "alphabet": "ipa"
        },
        {
            "type": "phoneme",
            "string": "Vapi",
            "phoneme": "/ˈvɑːpi/",
            "alphabet": "ipa"
        },
        {
            "type": "alias",
            "string": "AI",
            "alias": "Artificial Intelligence"
        },
        {
            "type": "alias",
            "string": "LLM",
            "alias": "Large Language Model"
        }
    ]

    # Create the dictionary
    dictionary = await service.create_dictionary(
        name="Tech Company Dictionary",
        rules=rules,
        description="Pronunciations for tech companies and AI terms"
    )

    print(f"Dictionary created with ID: {dictionary.id}")
    return dictionary.id

# Run the async function
asyncio.run(create_dictionary())
```

### Using Direct API Call

```python
import requests

url = "https://api.vapi.ai/provider/11labs/pronunciation-dictionary"
headers = {
    "Authorization": "Bearer YOUR_API_KEY",
    "Content-Type": "application/json"
}

payload = {
    "name": "Tech Company Dictionary",
    "description": "Pronunciations for tech companies and AI terms",
    "rules": [
        {
            "type": "phoneme",
            "string": "Anthropic",
            "phoneme": "/ænˈθɹɑpɪk/",
            "alphabet": "ipa"
        },
        {
            "type": "alias",
            "string": "AI",
            "alias": "Artificial Intelligence"
        }
    ]
}

response = requests.post(url, headers=headers, json=payload)
dictionary = response.json()
print(f"Dictionary ID: {dictionary['id']}")
```

## Configuring Assistants

Once you have a dictionary ID, reference it in your assistant's voice configuration.

### YAML Configuration

```yaml
# assistant.yaml

name: "Customer Support Assistant"

voice:
  provider: 11labs  # Must be ElevenLabs
  voiceId: "21m00Tcm4TlvDq8ikWAM"  # Rachel voice
  pronunciationDictionaryIds:
    - "dict-abc123"  # Your dictionary ID
    - "dict-def456"  # You can add multiple dictionaries

model:
  provider: openai
  model: gpt-4o-mini
  temperature: 0.7

transcriber:
  provider: deepgram
  model: nova-2
  language: en
```

### Python Configuration

```python
from vapi_manager.core.models import Voice, ModelConfig, AssistantCreateRequest

# Create voice with pronunciation dictionary
voice = Voice(
    provider="11labs",
    voice_id="21m00Tcm4TlvDq8ikWAM",
    pronunciation_dictionary_ids=["dict-abc123", "dict-def456"]
)

# Create assistant
assistant_request = AssistantCreateRequest(
    name="Customer Support Assistant",
    voice=voice,
    model=ModelConfig(
        provider="openai",
        model="gpt-4o-mini"
    )
)
```

## Complete Examples

### Tech Startup Assistant

```python
import asyncio
from vapi_manager.services import PronunciationDictionaryService, AssistantService
from vapi_manager.core.models import Voice, ModelConfig, AssistantCreateRequest

async def create_tech_assistant():
    # Step 1: Create pronunciation dictionary
    dict_service = PronunciationDictionaryService()

    tech_rules = [
        {
            "type": "phoneme",
            "string": "Anthropic",
            "phoneme": "/ænˈθɹɑpɪk/",
            "alphabet": "ipa"
        },
        {
            "type": "phoneme",
            "string": "Vapi",
            "phoneme": "/ˈvɑːpi/",
            "alphabet": "ipa"
        },
        {
            "type": "alias",
            "string": "API",
            "alias": "A P I"
        },
        {
            "type": "alias",
            "string": "LLM",
            "alias": "Large Language Model"
        },
        {
            "type": "alias",
            "string": "GPT",
            "alias": "G P T"
        }
    ]

    dictionary = await dict_service.create_dictionary(
        name="Tech Startup Dictionary",
        rules=tech_rules
    )

    print(f"Created dictionary: {dictionary.id}")

    # Step 2: Create assistant with pronunciation dictionary
    assistant_service = AssistantService()

    voice = Voice(
        provider="11labs",
        voice_id="21m00Tcm4TlvDq8ikWAM",
        pronunciation_dictionary_ids=[dictionary.id]
    )

    assistant_request = AssistantCreateRequest(
        name="Tech Startup Assistant",
        voice=voice,
        model=ModelConfig(
            provider="openai",
            model="gpt-4o-mini",
            temperature=0.7
        ),
        first_message="Hi! I'm here to help you learn about AI technology."
    )

    assistant = await assistant_service.create_assistant(assistant_request)
    print(f"Created assistant: {assistant.id}")

asyncio.run(create_tech_assistant())
```

### Healthcare Assistant

```python
async def create_healthcare_assistant():
    dict_service = PronunciationDictionaryService()

    medical_rules = [
        {
            "type": "phoneme",
            "string": "acetaminophen",
            "phoneme": "/əˌsiːtəˈmɪnəfən/",
            "alphabet": "ipa"
        },
        {
            "type": "alias",
            "string": "BP",
            "alias": "blood pressure"
        },
        {
            "type": "alias",
            "string": "ECG",
            "alias": "electrocardiogram"
        },
        {
            "type": "alias",
            "string": "MRI",
            "alias": "M R I scan"
        }
    ]

    dictionary = await dict_service.create_dictionary(
        name="Healthcare Terms",
        rules=medical_rules,
        description="Common medical terms and abbreviations"
    )

    # Create assistant with this dictionary...
```

### Legal Assistant

```python
async def create_legal_assistant():
    dict_service = PronunciationDictionaryService()

    legal_rules = [
        {
            "type": "alias",
            "string": "LLC",
            "alias": "Limited Liability Company"
        },
        {
            "type": "alias",
            "string": "NDA",
            "alias": "Non-Disclosure Agreement"
        },
        {
            "type": "phoneme",
            "string": "voir dire",
            "phoneme": "/vwɑːrˈdɪər/",
            "alphabet": "ipa"
        },
        {
            "type": "phoneme",
            "string": "pro bono",
            "phoneme": "/proʊˈboʊnoʊ/",
            "alphabet": "ipa"
        }
    ]

    dictionary = await dict_service.create_dictionary(
        name="Legal Terminology",
        rules=legal_rules
    )
```

### Brand Names Assistant

```python
async def create_brand_assistant():
    dict_service = PronunciationDictionaryService()

    brand_rules = [
        {
            "type": "phoneme",
            "string": "Huawei",
            "phoneme": "/ˈwɑːweɪ/",
            "alphabet": "ipa"
        },
        {
            "type": "phoneme",
            "string": "Nike",
            "phoneme": "/ˈnaɪki/",
            "alphabet": "ipa"
        },
        {
            "type": "phoneme",
            "string": "Porsche",
            "phoneme": "/ˈpɔːrʃə/",
            "alphabet": "ipa"
        },
        {
            "type": "phoneme",
            "string": "Xiaomi",
            "phoneme": "/ˈʃaʊmi/",
            "alphabet": "ipa"
        }
    ]

    dictionary = await dict_service.create_dictionary(
        name="Brand Pronunciations",
        rules=brand_rules
    )
```

## Managing Dictionaries

### List All Dictionaries

```python
async def list_dictionaries():
    service = PronunciationDictionaryService()
    dictionaries = await service.list_dictionaries()

    for dict in dictionaries:
        print(f"ID: {dict.id}")
        print(f"Name: {dict.name}")
        print(f"Rules: {len(dict.rules)}")
        print("---")
```

### Get Dictionary by ID

```python
async def get_dictionary(dictionary_id):
    service = PronunciationDictionaryService()
    dictionary = await service.get_dictionary(dictionary_id)

    print(f"Name: {dictionary.name}")
    print(f"Description: {dictionary.description}")
    print("Rules:")
    for rule in dictionary.rules:
        print(f"  - {rule.string}: {rule.get('phoneme') or rule.get('alias')}")
```

### Update Dictionary

```python
async def update_dictionary(dictionary_id):
    service = PronunciationDictionaryService()

    # Add new rules
    new_rules = [
        {
            "type": "alias",
            "string": "CEO",
            "alias": "Chief Executive Officer"
        },
        {
            "type": "alias",
            "string": "CFO",
            "alias": "Chief Financial Officer"
        }
    ]

    dictionary = await service.update_dictionary(
        dictionary_id,
        rules=new_rules,
        description="Updated with executive titles"
    )
```

### Delete Dictionary

```python
async def delete_dictionary(dictionary_id):
    service = PronunciationDictionaryService()
    success = await service.delete_dictionary(dictionary_id)

    if success:
        print(f"Dictionary {dictionary_id} deleted successfully")
```

## IPA Phonetic Guide

### Common IPA Symbols

| Symbol | Sound | Example |
|--------|-------|---------|
| æ | a in "cat" | cat /kæt/ |
| ə | a in "about" | about /əˈbaʊt/ |
| ɑː | a in "father" | father /ˈfɑːðər/ |
| ɪ | i in "kit" | kit /kɪt/ |
| iː | ee in "fleece" | fleece /fliːs/ |
| ʊ | oo in "foot" | foot /fʊt/ |
| uː | oo in "goose" | goose /ɡuːs/ |
| ɔː | or in "north" | north /nɔːrθ/ |
| ɛ | e in "dress" | dress /drɛs/ |
| ʌ | u in "strut" | strut /strʌt/ |
| θ | th in "think" | think /θɪŋk/ |
| ð | th in "this" | this /ðɪs/ |
| ʃ | sh in "ship" | ship /ʃɪp/ |
| ʒ | s in "measure" | measure /ˈmɛʒər/ |
| tʃ | ch in "chip" | chip /tʃɪp/ |
| dʒ | j in "judge" | judge /dʒʌdʒ/ |
| ŋ | ng in "sing" | sing /sɪŋ/ |
| ˈ | Primary stress | begin /bɪˈɡɪn/ |
| ˌ | Secondary stress | understand /ˌʌndərˈstænd/ |

### IPA Resources

- [IPA Chart](http://www.ipachart.com/)
- [IPA Phonetics](https://www.internationalphoneticalphabet.org/)
- [Cambridge Dictionary](https://dictionary.cambridge.org/) - Shows IPA for all words

## Best Practices

### 1. Test Pronunciations

Always test your pronunciation dictionaries with actual calls before deploying:
- Create a test assistant with your dictionary
- Make test calls and listen to the pronunciations
- Iterate on the phonetic spellings until they sound natural

### 2. Use Aliases for Acronyms

For acronyms, alias rules often work better than phonemes:
```yaml
# Good - sounds natural
- type: alias
  string: API
  alias: A P I

# Alternative - also good
- type: alias
  string: API
  alias: ay pee eye
```

### 3. Organize by Category

Create separate dictionaries for different categories:
- **Tech terms** - API, LLM, SDK, etc.
- **Brand names** - Company names, product names
- **Medical terms** - Medications, procedures
- **Industry jargon** - Domain-specific terminology

### 4. Keep Dictionaries Focused

Don't create one massive dictionary. Instead:
- Use multiple focused dictionaries
- Attach relevant dictionaries to specific assistants
- Makes maintenance and updates easier

### 5. Document Phonetic Choices

Add descriptions to your dictionaries explaining pronunciation decisions:
```python
dictionary = await service.create_dictionary(
    name="Brand Names",
    description="Standard US English pronunciations for major tech brands"
)
```

### 6. Handle Variations

For words with multiple pronunciations, choose the most common or appropriate for your audience:
```yaml
# US pronunciation
- type: phoneme
  string: schedule
  phoneme: ˈskedʒuːl
  alphabet: ipa

# UK pronunciation would be: ˈʃedjuːl
```

## Troubleshooting

### Dictionary Not Applied

**Issue:** Pronunciation dictionary doesn't seem to work

**Solutions:**
- Verify you're using ElevenLabs voice provider (`11labs`)
- Check that dictionary ID is correctly set in `pronunciationDictionaryIds`
- Ensure the word in your dictionary matches exactly (case-sensitive)
- Test with a simple example first

### Pronunciation Sounds Wrong

**Issue:** Custom pronunciation doesn't sound natural

**Solutions:**
- Try using alias rules instead of phoneme rules
- Verify IPA symbols are correct
- Test different phonetic spellings
- Consider using CMU Arpabet instead of IPA

### API Errors

**Issue:** Dictionary creation fails

**Solutions:**
- Check API key has correct permissions
- Verify JSON structure is correct
- Ensure provider is set to `11labs`
- Check rate limits

### Multiple Dictionaries Conflict

**Issue:** Rules from different dictionaries conflict

**Solutions:**
- Dictionary priority is based on order in `pronunciationDictionaryIds` array
- First matching rule wins
- Consolidate conflicting rules into one dictionary
- Use more specific word matches

## Deploying with vapi-manager

After configuring pronunciation dictionaries in your YAML:

```bash
# Create new assistant with pronunciation dictionary
vapi-manager assistant create your-assistant-name

# Update existing assistant with new dictionary
vapi-manager assistant update your-assistant-name --env production
```

The framework will automatically:
- Parse the `pronunciationDictionaryIds` from your YAML
- Include them in the voice configuration
- Send the correct API payload to Vapi

## Related Documentation

- [Vapi Pronunciation Dictionaries Official Docs](https://docs.vapi.ai/assistants/pronunciation-dictionaries)
- [ElevenLabs Voice Configuration](https://docs.vapi.ai/assistants/voice)
- [Background Speech Denoising Guide](./background-speech-denoising-guide.md)
- [Idle Messages Guide](./idle-messages-guide.md)
