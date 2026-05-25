from collections.abc import Iterator

from fastapi import Depends
from sqlalchemy.orm import Session

from app.db import get_session


def db_session() -> Iterator[Session]:
    yield from get_session()


SessionDep = Depends(db_session)
