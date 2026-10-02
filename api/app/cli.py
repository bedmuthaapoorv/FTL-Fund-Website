"""Operator commands. Run from api/:  .venv/bin/python -m app.cli <command>"""

import argparse
import sys

from sqlalchemy import select

from .accounts import issue_invite
from .audit import audit
from .db import SessionLocal
from .models import User


def create_admin(email: str) -> None:
    email = email.strip().lower()
    with SessionLocal() as db:
        if db.scalar(select(User).where(User.email == email)):
            sys.exit(f"User {email} already exists. Use `invite` to issue a fresh link.")
        user = User(email=email, role="admin", status="invited")
        db.add(user)
        db.flush()
        link = issue_invite(db, user)
        audit(db, None, "cli.admin_created", None, target=email)
        db.commit()
    print(f"Admin created. Open this link to set a password and MFA (valid 72h):\n{link}")


def reinvite(email: str) -> None:
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == email.strip().lower()))
        if not user:
            sys.exit("No such user.")
        link = issue_invite(db, user)
        audit(db, None, "cli.reinvite", None, target=user.email)
        db.commit()
    print(link)


def main() -> None:
    p = argparse.ArgumentParser(prog="app.cli")
    sub = p.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("create-admin", help="Create the admin account and print its invite link")
    a.add_argument("email")
    r = sub.add_parser("invite", help="Issue a fresh invite link for an existing user (resets password + MFA on use)")
    r.add_argument("email")
    sub.add_parser("seed", help="DEV ONLY: load fake investors and fund data")
    args = p.parse_args()

    if args.cmd == "create-admin":
        create_admin(args.email)
    elif args.cmd == "invite":
        reinvite(args.email)
    elif args.cmd == "seed":
        from .seed import seed
        seed()


if __name__ == "__main__":
    main()
