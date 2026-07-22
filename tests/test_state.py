from app.api.schemas import JobRequest


def test_idempotency_id_stable():
    a = JobRequest(topic="terremoto venezuela 2026", formats=["9:16", "16:9"])
    b = JobRequest(topic="terremoto venezuela 2026", formats=["16:9", "9:16"])
    # mesma intenção, ordem de formato diferente -> mesmo id (idempotente)
    assert a.idempotency_id() == b.idempotency_id()


def test_idempotency_id_changes_with_topic():
    a = JobRequest(topic="terremoto venezuela")
    b = JobRequest(topic="enchente rio grande do sul")
    assert a.idempotency_id() != b.idempotency_id()
