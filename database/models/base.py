from sqlalchemy.orm import declarative_base

# The declarative base class is the foundation of all our database models.
# Every table we create (Students, Teachers, Fees, etc.) will inherit from this Base.
# By defining it here in its own file, we ensure all models share the exact same 
# metadata registry, which mathematically prevents circular import crashes.

Base = declarative_base()