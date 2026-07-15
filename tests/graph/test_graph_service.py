from backend.app.core.graph.repositories.graph_repository import GraphRepository
from backend.app.core.graph.services.graph_service import GraphService
from helpers import make_case, make_store


def test_get_crime_summary():
    cases = [
        make_case(),
        make_case(),
        make_case(),
    ]

    store = make_store(cases, [])
    repo = GraphRepository(store)
    service = GraphService(repo)

    result = service.get_crime_summary()

    assert isinstance(result, dict)

    # At minimum, verify it isn't empty.
    assert len(result) > 0