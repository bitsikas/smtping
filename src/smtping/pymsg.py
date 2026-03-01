import email.message
import email.generator
import socket
import smtplib
import io

import click

click.Option


class TestSMTP(smtplib.SMTP):
    def __init__(
        self,
        host="",
        port=0,
        local_hostname=None,
        timeout=socket._GLOBAL_DEFAULT_TIMEOUT,
        source_address=None,
        proxy=None,
        quit_after=None,
        single_connection=False,
    ):
        self.quit_after = quit_after
        self.proxy = proxy
        super().__init__(host, port, local_hostname, timeout, source_address)

    def putcmd(self, cmd, args=""):
        self.command_encoding = "utf-8"
        super().putcmd(cmd, args)
        if cmd in ("rcpt", "mail"):
            subcmd, args = args.split(":", 1)
            cmd = f"{cmd.upper()} {subcmd.upper()}"
        click.echo(click.style(" 🡒 ", fg="yellow"), nl=False)
        click.echo(f"{cmd.upper()}: {args}")

    def docmd(self, cmd, args=""):
        """Send a command, and return its response code."""
        self.putcmd(cmd, args)
        reply = self.getreply()
        if self.quit_after and self.quit_after.upper() == cmd.upper():
            self.quit()
        return reply

    def getreply(self):
        reply = super().getreply()
        code, msg = reply
        msg = msg.decode()
        color = "green" if code < 400 else "red"
        for line in msg.splitlines():
            click.echo(click.style("🡐 ", fg=color), nl=False)
            click.echo(click.style(code, fg=color), nl=False)
            click.echo(f" {line}")
        return reply

    def _get_socket(self, host, port, timeout):
        # This makes it simpler for SMTP_SSL to use the SMTP connect code
        # and just alter the socket connection bit.
        if timeout is not None and not timeout:
            raise ValueError("Non-blocking socket (timeout=0) is not supported")

        if self.proxy:
            pass

        return socket.create_connection((host, port), timeout, self.source_address)

    def data(self, msg):
        self.putcmd("data")
        (code, repl) = self.getreply()
        if code != 354:
            raise smtplib.SMTPDataError(code, repl)
        else:
            if isinstance(msg, str):
                msg = smtplib._fix_eols(msg).encode("ascii")
            q = smtplib._quote_periods(msg)
            if q[-2:] != smtplib.bCRLF:
                q = q + smtplib.bCRLF
            q = q + b"." + smtplib.bCRLF
            self.send(q)
            for line in q.splitlines():
                click.echo(click.style(" 🡒 ", fg="yellow"), nl=False)
                click.echo(line.decode())
            (code, msg) = self.getreply()
            return (code, msg)


@click.command()
@click.option(
    "-s", "--server", "server", required=True, help="Send email from this adress"
)
@click.option(
    "-t", "--to", "recipients", multiple=True, help="Send email to these recipients"
)
@click.option(
    "-f",
    "--from",
    "sender",
    default=f"test@{socket.gethostname()}",
    help="Send email with this sender",
)
@click.option(
    "-c", "--count", "count", type=int, default=1, help="Number of messages to send"
)
@click.option(
    "--ssl/--no-ssl",
    "starttls",
    is_flag=True,
    default=True,
    help="Use starttls after helo/ehlo",
)
@click.option(
    "--single-connection/--multiple-connections",
    "single_connection",
    is_flag=True,
    default=False,
    help="Send messages in a single connection or in multiple connections",
)
@click.option("--quit-after", "quit_after", help="recipient")
@click.option("--smtputf8/--no-smtputf8", "smtputf8", is_flag=True, help="recipient")
@click.option(
    "--force-test-domains/--no-force-test-domains",
    "force_test_domains",
    is_flag=True,
    default=True,
    help="replace tld in domains in senders/recipients with .test tld",
)
def main(
    server, recipients, sender, count, single_connection, quit_after, smtputf8
) -> None:
    host, port = server.rsplit(":", 1)
    smtp = TestSMTP(
        host,
        int(port),
        proxy="",
        quit_after=quit_after,
        single_connection=single_connection,
    )
    msg = email.message.EmailMessage()
    msg["Subject"] = "This is a test email"
    msg["From"] = sender
    msg["To"] = recipients
    msg.set_content("Hi there,\n\nThis is a test email.")
    mail_options = []
    with io.BytesIO() as bytesmsg:
        if smtputf8:
            g = email.generator.BytesGenerator(
                bytesmsg, policy=msg.policy.clone(utf8=True)
            )
            mail_options = ("SMTPUTF8", "BODY=8BITMIME")
        else:
            g = email.generator.BytesGenerator(bytesmsg)
        g.flatten(msg, linesep="\r\n")
        flat_msg = bytesmsg.getvalue()

    for _ in range(count):
        try:
            smtp.sendmail(
                sender,
                recipients,
                flat_msg,
                mail_options=mail_options,
            )
        except Exception as e:
            import pdb

            pdb.set_trace()
            click.echo(click.style(e, fg="red"))
