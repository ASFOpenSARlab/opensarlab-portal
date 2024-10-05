from app.database import schema

#database.Base.metadata.drop_all(bind=engine)
schema.Base.metadata.create_all(bind=schema.engine)

# Dependency
def get_db():
    db = schema.SessionLocal()
    try:
        yield db
    finally:
        db.close()