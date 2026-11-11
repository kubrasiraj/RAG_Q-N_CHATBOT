
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.models.user import User


class EmailAlreadyRegisteredError(Exception):
    """Raised when an email address is already registered."""


def get_user_by_email(
    db: Session,
    email: str,
) -> User | None:
    """Find a user by normalized email address."""

    normalized_email = email.strip().lower()

    statement = select(User).where(
        User.email == normalized_email
    )

    return db.scalar(statement)


def register_user(
    db: Session,
    email: str,
    password: str,
) -> User:
    """Register a new customer account."""

    normalized_email = email.strip().lower()

    existing_user = get_user_by_email(
        db,
        normalized_email,
    )

    if existing_user:
        raise EmailAlreadyRegisteredError(
            "An account with this email already exists."
        )

    user = User(
        email=normalized_email,
        hashed_password=hash_password(password),
        role="customer",
        is_active=True,
    )

    try:
        db.add(user)
        db.commit()
        db.refresh(user)

    except IntegrityError:
        db.rollback()

        # Handle a concurrent registration attempt.
        if get_user_by_email(db, normalized_email):
            raise EmailAlreadyRegisteredError(
                "An account with this email already exists."
            )

        raise

    return user


def authenticate_user(
    db: Session,
    email: str,
    password: str,
) -> User | None:
    """Authenticate a user using email and password."""

    user = get_user_by_email(db, email)

    if user is None:
        return None

    if not verify_password(password, user.hashed_password):
        return None

    if not user.is_active:
        return None

    return user
