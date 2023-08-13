from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from logger import log


class POODatabase:
    db_engine = None
    sessionmaker = None
    base = declarative_base()

    def __init__(self, path_database=None):
        url = "sqlite:///poo.db" if path_database is None else f"sqlite:///{path_database}"
        log.info(f"POODatabase - Initialised database session with {url}")
        self.db_engine = create_engine(url)
        self.sessionmaker = sessionmaker(autocommit=False, autoflush=False, bind=self.db_engine)
