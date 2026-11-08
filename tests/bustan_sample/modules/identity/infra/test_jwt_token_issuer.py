from datetime import timedelta
from uuid import uuid4

import jwt
from bustan import ConfigService

from bustan_sample.modules.identity.infra.jwt_token_issuer import JwtTokenIssuer
from bustan_sample.platform.clock import FixedClock

SECRET = "a-test-secret-that-is-longer-than-32-characters"


def _issuer(**settings: object) -> JwtTokenIssuer:
    values: dict[str, object] = {
        "IDENTITY_JWT_SECRET": SECRET,
        "IDENTITY_TOKEN_TTL_MINUTES": 15,
    }
    values.update(settings)
    return JwtTokenIssuer(ConfigService(values))


def test_a_token_reads_back_with_the_same_claims() -> None:
    issuer, clock, user_id = _issuer(), FixedClock(), uuid4()
    token = issuer.issue(user_id, clock.now())
    claims = issuer.read(token.value, clock.now())
    assert claims is not None
    assert (claims.user_id, claims.token_id) == (user_id, token.token_id)
    assert claims.expires_at == token.expires_at == clock.now() + timedelta(minutes=15)


def test_each_token_has_a_unique_id() -> None:
    issuer, clock, user_id = _issuer(), FixedClock(), uuid4()
    first = issuer.issue(user_id, clock.now())
    second = issuer.issue(user_id, clock.now())
    assert first.token_id != second.token_id


def test_an_expired_token_is_refused() -> None:
    issuer, clock = _issuer(), FixedClock()
    token = issuer.issue(uuid4(), clock.now())
    clock.advance(timedelta(minutes=15))
    assert issuer.read(token.value, clock.now()) is None


def test_a_token_from_a_different_secret_or_issuer_is_refused() -> None:
    clock = FixedClock()
    token = _issuer().issue(uuid4(), clock.now())
    other_secret = _issuer(IDENTITY_JWT_SECRET="x" * 40)
    other_issuer = _issuer(IDENTITY_JWT_ISSUER="somebody-else")
    assert other_secret.read(token.value, clock.now()) is None
    assert other_issuer.read(token.value, clock.now()) is None


def test_an_unsigned_or_damaged_token_is_refused() -> None:
    issuer, clock = _issuer(), FixedClock()
    token = issuer.issue(uuid4(), clock.now()).value
    claims = jwt.decode(token, options={"verify_signature": False})
    unsigned = jwt.encode(claims, key=None, algorithm="none")
    assert issuer.read(unsigned, clock.now()) is None
    assert issuer.read(token[:-2] + "xx", clock.now()) is None
    assert issuer.read("not a token", clock.now()) is None


def test_a_token_without_a_required_claim_is_refused() -> None:
    issuer, clock = _issuer(), FixedClock()
    without_jti = jwt.encode(
        {"iss": "bustan-sample", "sub": str(uuid4()), "iat": 0, "exp": 2**40},
        SECRET,
        algorithm="HS256",
    )
    assert issuer.read(without_jti, clock.now()) is None
