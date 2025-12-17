import pytest
from aiosmtpd.smtp import Envelope

import smtping


pytestmark = pytest.mark.anyio


@pytest.mark.parametrize(
    "domain",
    [
        "test.test",
        "test+test.test",
        "test+test.test+test",
    ],
)
@pytest.mark.parametrize(
    "rcpt",
    [
        "id",
        "id+accept",
        "id+accept+mymessage",
    ],
)
async def test_handle_rcpt_with_accept(rcpt, domain):
    envelope = Envelope()
    response = await smtping.PongHandler().handle_RCPT(
        server=None,
        session=None,
        envelope=envelope,
        address=f"{rcpt}@{domain}",
        rcpt_options=None,
    )
    _, *rest = rcpt.rsplit("+")
    if len(rest) < 2:
        message = ""
    else:
        message = f" {rest[-1]}"
    assert envelope.rcpt_tos == [f"{rcpt}@{domain}"]
    assert response == f"250 OK{message}"


@pytest.mark.parametrize(
    "domain",
    [
        "test.test",
        "test+test.test",
        "test+test.test+test",
    ],
)
@pytest.mark.parametrize(
    "rcpt",
    [
        "id+reject",
        "id+reject+mymessage",
    ],
)
async def test_handle_rcpt_with_reject(rcpt, domain):
    envelope = Envelope()
    response = await smtping.PongHandler().handle_RCPT(
        server=None,
        session=None,
        envelope=envelope,
        address=f"{rcpt}@{domain}",
        rcpt_options=None,
    )
    _, *rest = rcpt.rsplit("+")
    if len(rest) < 2:
        message = ""
    else:
        message = f" {rest[-1]}"

    assert envelope.rcpt_tos == [f"{rcpt}@{domain}"]
    assert response == f"550 SHOO{message}"


@pytest.mark.parametrize(
    "domain",
    [
        "test.test",
        "test+test.test",
        "test+test.test+test",
    ],
)
@pytest.mark.parametrize(
    "rcpt",
    [
        "id",
        "id+accept",
        "id+accept+mymessage",
    ],
)
async def test_handle_mail_with_accept(rcpt, domain):
    envelope = Envelope()
    response = await smtping.PongHandler().handle_MAIL(
        server=None,
        session=None,
        envelope=envelope,
        address=f"{rcpt}@{domain}",
        mail_options=None,
    )
    _, *rest = rcpt.rsplit("+")
    if len(rest) < 2:
        message = ""
    else:
        message = f" {rest[-1]}"
    assert envelope.mail_from == f"{rcpt}@{domain}"
    assert response == f"250 OK{message}"


@pytest.mark.parametrize(
    "domain",
    [
        "test.test",
        "test+test.test",
        "test+test.test+test",
    ],
)
@pytest.mark.parametrize(
    "rcpt",
    [
        "id+reject",
        "id+reject+mymessage",
    ],
)
async def test_handle_mail_with_reject(rcpt, domain):
    envelope = Envelope()
    response = await smtping.PongHandler().handle_MAIL(
        server=None,
        session=None,
        envelope=envelope,
        address=f"{rcpt}@{domain}",
        mail_options=None,
    )
    _, *rest = rcpt.rsplit("+")
    if len(rest) < 2:
        message = ""
    else:
        message = f" {rest[-1]}"

    assert envelope.mail_from == f"{rcpt}@{domain}"
    assert response == f"550 SHOO{message}"
