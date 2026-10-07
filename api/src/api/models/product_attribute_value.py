from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, Index, Numeric, String, Text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.base import Base, TimestampMixin

if TYPE_CHECKING:
    from api.models.attribute_definition import AttributeDefinition
    from api.models.product import Product


class ProductAttributeValue(TimestampMixin, Base):
    __tablename__ = "product_attribute_values"
    __table_args__ = (
        CheckConstraint(
            "num_nonnulls(value_text, value_number, value_bool, value_choices) = 1",
            name="exactly_one_value",
        ),
        Index("ix_product_attribute_values_attr_number", "attribute_id", "value_number"),
        Index("ix_product_attribute_values_attr_text", "attribute_id", "value_text"),
        Index("ix_product_attribute_values_choices", "value_choices", postgresql_using="gin"),
    )

    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), primary_key=True
    )
    attribute_id: Mapped[int] = mapped_column(
        ForeignKey("attribute_definitions.id", ondelete="RESTRICT"), primary_key=True
    )
    value_text: Mapped[str | None] = mapped_column(String(200))
    value_number: Mapped[Decimal | None] = mapped_column(Numeric(12, 3))
    value_bool: Mapped[bool | None] = mapped_column()
    value_choices: Mapped[list[str] | None] = mapped_column(ARRAY(Text))

    product: Mapped["Product"] = relationship(back_populates="attribute_values")
    attribute: Mapped["AttributeDefinition"] = relationship()