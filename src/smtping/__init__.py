import enum
import socket
import signal
import asyncio
import functools
from aiosmtpd.controller import Controller
from typing import Awaitable


class Action(enum.StrEnum):
    ACCEPT = enum.auto()
    REJECT = enum.auto()
    DROP = enum.auto()
    SLEEP = enum.auto()


async def handle_action(action, params):
    if action.startswith(Action.SLEEP):
        await asyncio.sleep(int(params[0]) if params else 1)
    if action.endswith(Action.ACCEPT):
        return f"250 OK {params[0]}".strip() if params else "250 OK"
    if action.endswith(Action.REJECT):
        return f"550 SHOO {params[0]}".strip() if params else "550 SHOO"

    return "250 OK"


class PongHandler:
    async def handle_MAIL(self, server, session, envelope, address, mail_options):
        mail_from_id, *rest = address.rsplit("@", 1)[0].split("+")

        envelope.mail_from = address
        action = Action.ACCEPT
        params = []
        if rest:
            action, *params = rest
        return await handle_action(action, params)

    async def handle_RCPT(self, server, session, envelope, address, rcpt_options):
        rcpt_id, *rest = address.rsplit("@", 1)[0].split("+")

        envelope.rcpt_tos.append(address)
        action = Action.ACCEPT
        params = []
        if rest:
            action, *params = rest
        return await handle_action(action, params)


class SystemDController(Controller):
    def _create_server(self) -> Awaitable[asyncio.AbstractServer]:
        """
        Creates a 'server task' that listens on an INET host:port.
        Does NOT actually start the protocol object itself;
        _factory_invoker() is only called upon fist connection attempt.
        """
        sock = socket.fromfd(3, socket.AF_INET, socket.SOCK_STREAM)
        return self.loop.create_server(
            self._factory_invoker,
            ssl=self.ssl_context,
            sock=sock,
        )

    def _trigger_server(self):
        pass


def _handle_sigterm(sig, frame, controller=None):
    print("Exiting...")
    controller.stop()


async def amain() -> None:
    handler = PongHandler()
    controller = SystemDController(handler)
    stop = functools.partial(_handle_sigterm, controller=controller)
    signal.signal(signal.SIGTERM, stop)
    print("Starting...")

    controller.start()

    try:
        await asyncio.Event().wait()  # Keep the server running
    except KeyboardInterrupt:
        print("Stopping SMTP server...")
    finally:
        controller.stop()


def main() -> None:
    asyncio.run(amain())
