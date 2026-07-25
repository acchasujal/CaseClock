from backend.app.ai.prompt_manager import PromptManager
from backend.app.ai.quickml_client import QuickMLClient
from backend.app.ai.quickml_service import QuickMLService
from backend.app.db.catalyst import CatalystRestDatastore


def get_quickml_service() -> QuickMLService:
    """Construct a fully configured QuickMLService."""

    datastore = CatalystRestDatastore.from_env()

    client = QuickMLClient(
        datastore=datastore,
    )

    prompt_manager = PromptManager()

    return QuickMLService(
        client=client,
        prompt_manager=prompt_manager,
    )