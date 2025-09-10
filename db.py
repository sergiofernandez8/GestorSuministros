from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, declarative_base

# Ruta completa para asegurar conexión
engine = create_engine('sqlite:///database/suministrosbbdd.db')

# Activa las claves foraneas de SQLite, ya que SQLite por defecto vienen desacrivadas
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

Base = declarative_base()

Session = sessionmaker(bind=engine)
session = Session()
