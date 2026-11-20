"""
Facts about the request being handled, kept on the request's database
session so the services and the audit log can read them without passing
them through every function:

- the signed-in user (for the audit log)
- the closing password the user typed (to save a change in a closed period)

The session belongs to one request only, so values never leak between requests.
(Context variables would not work here: FastAPI runs dependencies in other threads.)
"""

from sqlalchemy.orm import Session

USER_ID = "current_user_id"
CLOSING_PASSWORD = "closing_password"


def remember_request(session: Session, user_id: int, closing_password: str | None) -> None:
    session.info[USER_ID] = user_id
    session.info[CLOSING_PASSWORD] = closing_password


def current_user_id(session: Session) -> int | None:
    return session.info.get(USER_ID)


def typed_closing_password(session: Session) -> str | None:
    return session.info.get(CLOSING_PASSWORD)
