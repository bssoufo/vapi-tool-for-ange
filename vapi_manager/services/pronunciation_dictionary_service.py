"""Service for managing pronunciation dictionaries (ElevenLabs provider)."""

from typing import List, Optional, Dict, Any
from ..core.models.assistant import PronunciationDictionary, PhonemeRule, AliasRule
from ..core.exceptions.vapi_exceptions import VAPIAPIError
from .vapi_client import VAPIClient


class PronunciationDictionaryService:
    """Service for managing pronunciation dictionaries for ElevenLabs voices."""

    def __init__(self, client: Optional[VAPIClient] = None, verbose: bool = False):
        self.client = client or VAPIClient(verbose=verbose)

    async def create_dictionary(
        self,
        name: str,
        rules: List[Dict[str, Any]],
        description: Optional[str] = None
    ) -> PronunciationDictionary:
        """
        Create a new pronunciation dictionary for ElevenLabs voices.

        Args:
            name: Dictionary name
            rules: List of pronunciation rules (phoneme or alias)
            description: Optional description

        Returns:
            Created PronunciationDictionary

        Example:
            rules = [
                {
                    "type": "phoneme",
                    "string": "Anthropic",
                    "phoneme": "ænˈθɹɑpɪk",
                    "alphabet": "ipa"
                },
                {
                    "type": "alias",
                    "string": "UN",
                    "alias": "United Nations"
                }
            ]
            dictionary = await service.create_dictionary("My Dictionary", rules)
        """
        try:
            data = {
                "name": name,
                "rules": rules
            }
            if description:
                data["description"] = description

            response = await self.client.post("provider/11labs/pronunciation-dictionary", data)
            return PronunciationDictionary.model_validate(response)
        except VAPIAPIError as e:
            raise VAPIAPIError(f"Failed to create pronunciation dictionary: {e}") from e

    async def get_dictionary(self, dictionary_id: str) -> PronunciationDictionary:
        """
        Get a pronunciation dictionary by ID.

        Args:
            dictionary_id: Dictionary ID

        Returns:
            PronunciationDictionary
        """
        try:
            response = await self.client.get(f"provider/11labs/pronunciation-dictionary/{dictionary_id}")
            return PronunciationDictionary.model_validate(response)
        except VAPIAPIError as e:
            raise VAPIAPIError(f"Failed to get pronunciation dictionary {dictionary_id}: {e}") from e

    async def list_dictionaries(self) -> List[PronunciationDictionary]:
        """
        List all pronunciation dictionaries.

        Returns:
            List of PronunciationDictionary objects
        """
        try:
            response = await self.client.get("provider/11labs/pronunciation-dictionary")

            # Handle both paginated and direct list responses
            if isinstance(response, dict) and "data" in response:
                dictionaries_data = response["data"]
            else:
                dictionaries_data = response

            return [PronunciationDictionary.model_validate(d) for d in dictionaries_data]
        except VAPIAPIError as e:
            raise VAPIAPIError(f"Failed to list pronunciation dictionaries: {e}") from e

    async def update_dictionary(
        self,
        dictionary_id: str,
        name: Optional[str] = None,
        rules: Optional[List[Dict[str, Any]]] = None,
        description: Optional[str] = None
    ) -> PronunciationDictionary:
        """
        Update an existing pronunciation dictionary.

        Args:
            dictionary_id: Dictionary ID
            name: Optional new name
            rules: Optional new rules list
            description: Optional new description

        Returns:
            Updated PronunciationDictionary
        """
        try:
            data = {}
            if name is not None:
                data["name"] = name
            if rules is not None:
                data["rules"] = rules
            if description is not None:
                data["description"] = description

            response = await self.client.patch(
                f"provider/11labs/pronunciation-dictionary/{dictionary_id}",
                data
            )
            return PronunciationDictionary.model_validate(response)
        except VAPIAPIError as e:
            raise VAPIAPIError(f"Failed to update pronunciation dictionary {dictionary_id}: {e}") from e

    async def delete_dictionary(self, dictionary_id: str) -> bool:
        """
        Delete a pronunciation dictionary.

        Args:
            dictionary_id: Dictionary ID

        Returns:
            True if successful
        """
        try:
            await self.client.delete(f"provider/11labs/pronunciation-dictionary/{dictionary_id}")
            return True
        except VAPIAPIError as e:
            raise VAPIAPIError(f"Failed to delete pronunciation dictionary {dictionary_id}: {e}") from e
