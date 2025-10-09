# create_categories_table.py
from app.database.connection import Base, engine
from app.models.category import Category

# Toto vytvorí ONLY categories tabuľku ak neexistuje
Category.__table__.create(bind=engine, checkfirst=True)
print("Categories table created or already exists!")