from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Boolean,
    DateTime,
    Text
)
from sqlalchemy.sql import func

from database import Base


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)

    # Product ownership
    owner_id = Column(Integer, nullable=False, index=True)

    # Product details
    name = Column(String(200), nullable=False, index=True)
    description = Column(Text, nullable=True)

    # Pricing & inventory
    price = Column(Float, nullable=False)
    stock = Column(Integer, default=0)

    # Classification
    category = Column(String(100), nullable=True, index=True)

    # Soft delete support
    is_active = Column(Boolean, default=True, nullable=False)

    # Audit fields
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )

    def __repr__(self):
        return (
            f"<Product "
            f"id={self.id} "
            f"name='{self.name}' "
            f"owner_id={self.owner_id}>"
        )