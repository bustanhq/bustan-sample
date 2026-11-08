import asyncio
import json
import logging

import pytest

from bustan_sample.platform.mail import LogMailer
from bustan_sample.platform.mail.log_mailer import mask_address


def test_the_record_masks_the_recipient_and_has_no_body(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.INFO, logger="bustan"):
        asyncio.run(LogMailer().send("ada@example.com", "Hello", "a secret link"))
    [record] = [json.loads(r.getMessage()) for r in caplog.records]
    assert record["to"] == "a***@example.com"
    assert record["subject"] == "Hello"
    assert "a secret link" not in json.dumps(record)


@pytest.mark.parametrize(
    ("address", "masked"),
    [
        ("ada@example.com", "a***@example.com"),
        ("x@y.org", "x***@y.org"),
        ("no-at", "***"),
    ],
)
def test_mask_address(address: str, masked: str) -> None:
    assert mask_address(address) == masked
