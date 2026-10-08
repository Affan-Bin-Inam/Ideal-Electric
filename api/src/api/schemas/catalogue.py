from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class AttributeOut(ORMModel):
    key: str
    label: str
    data_type: str
    unit: str | None
    choices: list[str] | None
    group_name: str | None
    is_filterable: bool
    is_inquiry_option: bool


class IndustryOut(ORMModel):
    id: int
    name: str
    slug: str
    summary: str | None
    description: str | None
    icon: str | None


class CategoryBrief(ORMModel):
    id: int
    name: str
    slug: str


class CategoryNode(ORMModel):
    id: int
    name: str
    slug: str
    description: str | None
    product_count: int = 0
    children: list[CategoryNode] = Field(default_factory=list)


class CategoryDetail(ORMModel):
    id: int
    name: str
    slug: str
    description: str | None
    seo_title: str | None
    seo_description: str | None
    product_count: int
    parent: CategoryBrief | None
    children: list[CategoryNode]
    attributes: list[AttributeOut]


class BrandBrief(ORMModel):
    name: str
    slug: str


class SeriesBrief(ORMModel):
    name: str
    slug: str


class ProductCard(ORMModel):
    id: int
    name: str
    slug: str
    model_code: str | None
    summary: str | None
    is_featured: bool
    category: CategoryBrief
    series: SeriesBrief | None


class ProductPage(BaseModel):
    items: list[ProductCard]
    total: int
    page: int
    page_size: int
    pages: int


class SpecOut(BaseModel):
    key: str
    label: str
    group_name: str | None
    unit: str | None
    data_type: str
    is_inquiry_option: bool
    value: str | bool | list[str]


class ProductDetail(ORMModel):
    id: int
    name: str
    slug: str
    model_code: str | None
    summary: str | None
    description: str | None
    is_featured: bool
    seo_title: str | None
    seo_description: str | None
    category: CategoryBrief
    parent_category: CategoryBrief | None
    brand: BrandBrief | None
    series: SeriesBrief | None
    features: list[str]
    applications: list[str]
    specifications: list[SpecOut]
    industries: list[IndustryOut]
    related: list[ProductCard]


class FacetOption(BaseModel):
    value: str
    count: int


class Facet(BaseModel):
    key: str
    label: str
    unit: str | None
    data_type: str
    options: list[FacetOption]


class SeriesFacet(BaseModel):
    name: str
    slug: str
    count: int


class FacetSet(BaseModel):
    total: int
    series: list[SeriesFacet]
    attributes: list[Facet]


class SuggestionOut(BaseModel):
    name: str
    slug: str
    category: str