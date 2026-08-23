import pytest

from brain.developmental.consolidation import SleepConsolidationService


def test_dream_outputs_are_simulated() -> None:
    service = SleepConsolidationService()
    memory = service.add_memory(
        content="buyer replied after licensing signal",
        salience=0.8,
        source_refs=["source:email-outcome"],
    )
    dream = service.dream([memory.id], proposal="try licensing-signal outreach variant")

    assert dream.simulated is True
    assert dream.source_memory_ids == [memory.id]


def test_dream_cannot_execute_external_action() -> None:
    service = SleepConsolidationService()
    memory = service.add_memory(
        content="simulated opportunity",
        salience=0.7,
        source_refs=["source:simulation"],
    )
    dream = service.dream([memory.id], proposal="simulate external outreach")

    assert dream.can_execute_external_action is False


def test_consolidation_preserves_provenance() -> None:
    service = SleepConsolidationService()
    first = service.add_memory(content="a", salience=0.6, source_refs=["source:a"])
    second = service.add_memory(content="b", salience=0.5, source_refs=["source:b"])
    service.dream([first.id, second.id], proposal="rewire common pattern")
    record = service.consolidate([first.id, second.id], compressed_summary="a/b pattern")

    assert record.preserved_source_refs == ["source:a", "source:b"]
    assert len(record.rewire_proposal_ids) == 1


def test_compression_does_not_delete_source_evidence() -> None:
    service = SleepConsolidationService()
    memory = service.add_memory(
        content="long source trace",
        salience=0.4,
        source_refs=["source:raw-transcript", "source:outcome"],
    )
    record = service.consolidate([memory.id], compressed_summary="compressed")

    assert "source:raw-transcript" in record.preserved_source_refs
    assert "source:outcome" in record.preserved_source_refs


def test_dream_requires_known_memory() -> None:
    service = SleepConsolidationService()
    with pytest.raises(ValueError, match="dream_requires_memories"):
        service.dream([], proposal="none")
