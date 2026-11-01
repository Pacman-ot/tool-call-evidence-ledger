from evidence_ledger.canonicalize import CanonicalizationError, canonicalize, canonicalize_bytes
from evidence_ledger.hashing import hash_payload, sha256_hex


def test_same_input_same_digest():
    payload = {"a": 1, "b": "x", "previous_hash": "GENESIS_V1"}
    assert hash_payload(payload) == hash_payload(dict(payload))


def test_key_order_does_not_matter():
    a = {"b": 2, "a": 1}
    b = {"a": 1, "b": 2}
    assert canonicalize(a) == canonicalize(b)
    assert hash_payload(a) == hash_payload(b)


def test_changed_payload_changes_digest():
    base = {"session_id": "s", "sequence_no": 1, "value": 1}
    other = {"session_id": "s", "sequence_no": 1, "value": 2}
    assert hash_payload(base) != hash_payload(other)


def test_changed_previous_hash_changes_digest():
    a = {"previous_hash": "GENESIS_V1", "x": 1}
    b = {"previous_hash": "deadbeef", "x": 1}
    assert hash_payload(a) != hash_payload(b)


def test_unicode_and_nulls():
    payload = {"msg": "नमस्ते", "empty": None, "arr": [1, "二", None]}
    digest = hash_payload(payload)
    assert len(digest) == 64
    assert canonicalize_bytes(payload).decode("utf-8").startswith("{")


def test_reject_nan():
    import math

    try:
        canonicalize(float("nan"))
        assert False, "expected CanonicalizationError"
    except CanonicalizationError:
        pass
    try:
        canonicalize(math.inf)
        assert False
    except CanonicalizationError:
        pass


def test_sha256_known_vector():
    # SHA256("") = e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
    assert sha256_hex(b"") == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
