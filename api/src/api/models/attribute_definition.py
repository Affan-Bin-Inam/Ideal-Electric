from __future__ import annotations

from sqlalchemy import CheckConstraint, String, Text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from api.base import Base, TimestampMixin


class AttributeDefinition(TimestampMixin, Base):
    __tablename__ = "attribute_definitions"
    __table_args__ = (
        CheckConstraint(
            "data_type IN ('text', 'number', 'boolean', 'single_choice', 'multi_choice')",
            name="data_type",
        ),
        CheckConstraint(
            "(data_type IN ('single_choice', 'multi_choice')) = (choices IS NOT NULL)",
            name="choices_match_type",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(60), unique=True)
    label: Mapped[str] = mapped_column(String(120))
    data_type: Mapped[str] = mapped_column(String(20))
    unit: Mapped[str | None] = mapped_column(String(20))
    choices: Mapped[list[str] | None] = mapped_column(ARRAY(Text))
    group_name: Mapped[str | None] = mapped_column(String(80))
    is_filterable: Mapped[bool] = mapped_column(default=False, server_default="false")
    is_inquiry_option: Mapped[bool] = mapped_column(default=False, server_default="false")
    sort_order: Mapped[int] = mapped_column(default=0, server_default="0")