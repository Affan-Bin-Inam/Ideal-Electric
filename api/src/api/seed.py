"""Seed placeholder catalogue data for Ideal Electric.

Run from the api folder:  uv run python -m api.seed
Safe to re-run: rows that already exist (matched by slug or key) are left untouched.
Everything seeded is flagged is_placeholder=True until replaced with real content.
"""
from __future__ import annotations

import asyncio
import re
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.db import async_session_factory, engine
from api.models import (
    AttributeDefinition,
    Brand,
    Category,
    CategoryAttribute,
    Industry,
    Product,
    ProductAttributeValue,
    ProductHighlight,
    ProductIndustry,
    RelatedProduct,
    Series,
)


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


# ---------------------------------------------------------------- reference data

SERIES = [
    "Libra Gold", "Delta Gold", "Yachica", "H-Series Delta", "Black Gold",
    "Delixi Gold", "Hybrid", "Omni", "Sphiro LED",
]

INDUSTRIES = [
    ("Residential", "Safe, dependable electrical components for homes and apartments."),
    ("Commercial", "Protection, lighting and cabling for shops, offices and buildings."),
    ("Industrial", "Switching and protection for plants, workshops and machinery."),
    ("Construction", "Supply for building projects, from first fix to finishing."),
    ("Electrical Contracting", "Dependable stock for contractors and installers."),
    ("Government & Public Sector", "Supply to public institutions and organisations."),
]

CATEGORIES = {
    "Circuit Protection": [
        "Miniature Circuit Breakers", "DC Power Circuit Breakers",
        "Safety Breakers", "Molded Case Circuit Breakers",
    ],
    "Switchgear & Control": ["Selector & Change-Over Switches", "Copper Bus Bars"],
    "Lighting Solutions": [
        "LED Strip Lights", "Sphiro LED Fixtures", "LED Panel Lights & Digital Lights",
    ],
    "Cables & Connectivity": ["Network Cables", "Coaxial Cables"],
    "Capacitors": [],
}

TOP_DESCRIPTIONS = {
    "Circuit Protection": "Miniature, DC and molded-case circuit breakers plus safety breakers, built to protect installations from overload and short circuits.",
    "Switchgear & Control": "Selector and change-over switches and copper bus bars for panels and three-phase systems.",
    "Lighting Solutions": "Sphiro LED lighting: panels, downlights, eyeball lights, strip lights and indicator lamps.",
    "Cables & Connectivity": "Network and coaxial cables for data, TV and communications.",
    "Capacitors": "AC capacitors in bakelite cases, designed for long life and stable operation.",
}

TOP_INDUSTRIES = {
    "Circuit Protection": [
        "Residential", "Commercial", "Industrial", "Construction",
        "Electrical Contracting", "Government & Public Sector",
    ],
    "Switchgear & Control": ["Industrial", "Commercial", "Electrical Contracting", "Construction"],
    "Lighting Solutions": ["Residential", "Commercial", "Construction", "Government & Public Sector"],
    "Cables & Connectivity": [
        "Commercial", "Residential", "Government & Public Sector", "Electrical Contracting",
    ],
    "Capacitors": ["Industrial", "Residential", "Electrical Contracting"],
}

CURRENT = ["2", "4", "6", "10", "15", "16", "20", "30", "32", "50", "60", "63",
           "75", "100", "125", "160", "200", "250"]
COLOURS = ["Red", "Green", "Yellow", "Blue", "White", "Grey", "Ice Blue", "Ice Green", "Purple"]
CORE = ["Bare Copper (BC)", "Copper Covered Aluminium (CCA)", "CCS"]


def attr(key, label, data_type, *, unit=None, choices=None, group=None,
         filterable=False, inquiry=False):
    return {
        "key": key, "label": label, "data_type": data_type, "unit": unit,
        "choices": choices, "group_name": group,
        "is_filterable": filterable, "is_inquiry_option": inquiry,
    }


ATTRIBUTES = [
    attr("current_ratings", "Current Ratings", "multi_choice", unit="A", choices=CURRENT,
         group="Electrical", filterable=True, inquiry=True),
    attr("poles", "Poles", "multi_choice", choices=["1", "2", "3", "4"],
         group="Electrical", filterable=True, inquiry=True),
    attr("switch_positions", "Switch Positions", "text", group="Electrical"),
    attr("capacitance", "Capacitance", "multi_choice", unit="µF",
         choices=["2.5", "3.5", "4.5", "6", "8", "10", "12", "16", "20", "25", "30"],
         group="Electrical", filterable=True, inquiry=True),
    attr("rated_voltage", "Rated Voltage / Frequency", "text", group="Electrical"),
    attr("core_material", "Core Material", "single_choice", choices=CORE,
         group="Construction", filterable=True),
    attr("cable_length", "Cable Length", "multi_choice", unit="m", choices=["100", "305"],
         group="Construction", inquiry=True),
    attr("coax_type", "Coaxial Type", "multi_choice", choices=["RG-6", "RG-7"],
         group="Construction", filterable=True, inquiry=True),
    attr("bar_length", "Bar Length", "multi_choice", unit="cm", choices=["50", "100"],
         group="Construction", inquiry=True),
    attr("colours", "Colours", "multi_choice", choices=COLOURS,
         group="Appearance", filterable=True, inquiry=True),
    attr("colour_temperature", "Colour Temperature", "multi_choice", unit="K",
         choices=["3000", "4000", "6500"], group="Lighting", filterable=True, inquiry=True),
    attr("strip_width", "Strip Width", "multi_choice", unit="mm",
         choices=["6", "6.8", "8", "10"], group="Lighting", filterable=True, inquiry=True),
    attr("led_chip", "LED Chip", "text", group="Lighting"),
]

CATEGORY_ATTRIBUTES = {
    "Miniature Circuit Breakers": ["current_ratings", "poles"],
    "DC Power Circuit Breakers": ["current_ratings"],
    "Safety Breakers": ["current_ratings"],
    "Molded Case Circuit Breakers": ["current_ratings", "poles"],
    "Selector & Change-Over Switches": ["current_ratings", "poles", "switch_positions"],
    "Copper Bus Bars": ["bar_length", "colours"],
    "LED Strip Lights": ["strip_width", "colour_temperature", "colours", "led_chip"],
    "LED Panel Lights & Digital Lights": ["colours"],
    "Network Cables": ["core_material", "cable_length"],
    "Coaxial Cables": ["core_material", "cable_length", "coax_type"],
    "Capacitors": ["capacitance", "rated_voltage"],
}


def product(name, category, summary, *, series=None, model=None, features=(),
            applications=(), attrs=None, featured=False):
    return {
        "name": name, "category": category, "summary": summary, "series": series,
        "model": model, "features": features, "applications": applications,
        "attrs": attrs or {}, "featured": featured,
    }


PRODUCTS = [
    product("Libra Gold MCB", "Miniature Circuit Breakers",
            "Miniature circuit breakers from the Ideal Libra Gold series, built for reliable, stable performance.",
            series="Libra Gold", featured=True,
            features=["Reliable, stable quality", "1, 2 and 3 pole versions", "Ratings from 2A to 63A"],
            applications=["Overload and short-circuit protection", "Distribution boards"],
            attrs={"current_ratings": ["2", "4", "6", "10", "16", "20", "32", "63"],
                   "poles": ["1", "2", "3"]}),
    product("Yachica MCB", "Miniature Circuit Breakers",
            "Cost-effective miniature circuit breakers from the Ideal Yachica series with stable quality performance.",
            series="Yachica", featured=True,
            features=["Same appearance at a lower cost", "1, 2 and 3 pole versions", "Ratings from 6A to 63A"],
            applications=["Overload and short-circuit protection", "Distribution boards"],
            attrs={"current_ratings": ["6", "10", "16", "20", "32", "63"], "poles": ["1", "2", "3"]}),
    product("Delta Gold MCB", "Miniature Circuit Breakers",
            "New-generation low-voltage miniature circuit breaker from Ideal Electric.",
            series="Delta Gold",
            features=["New-generation design"],
            applications=["Overload and short-circuit protection"]),
    product("DC Power Circuit Breaker", "DC Power Circuit Breakers",
            "Circuit breakers for DC power systems, in 32A, 63A and 125A ratings.",
            features=["Ratings: 32A, 63A and 125A", "Protector versions also available"],
            applications=["DC power distribution"],
            attrs={"current_ratings": ["32", "63", "125"]}),
    product("NT-50 Safety Breaker", "Safety Breakers",
            "Ideal NT-50 safety breaker, available in Gold and Yachica lines.",
            model="NT-50",
            features=["Ratings: 10, 15, 20 and 30A", "Gold and Yachica lines"],
            applications=["Final-circuit protection", "Homes and small commercial sites"],
            attrs={"current_ratings": ["10", "15", "20", "30"]}),
    product("MCCB TP Molded Case Circuit Breaker", "Molded Case Circuit Breakers",
            "Three-pole molded case circuit breakers from 30A to 250A.",
            features=["3 pole", "Ratings from 30A to 250A"],
            applications=["Main and sub-distribution panels", "Industrial feeders"],
            attrs={"current_ratings": ["30", "60", "100", "160", "200", "250"], "poles": ["3"]}),
    product("Yachica / CESCO Selector Switch", "Selector & Change-Over Switches",
            "Three-phase selector switch for reading linked and phase voltages or currents with a single meter.",
            series="Yachica",
            features=["Measures linked and phase voltages with one meter", "Positions 0-1-2-3-4",
                      "2 and 3 pole versions"],
            applications=["Three-phase monitoring", "Control panels"],
            attrs={"current_ratings": ["32", "50", "75"], "poles": ["2", "3"],
                   "switch_positions": "0-1-2-3-4"}),
    product("Yachica / CESCO Change-Over Switch", "Selector & Change-Over Switches",
            "Change-over switch for switching between two supplies, in 2, 3 and 4 pole versions.",
            series="Yachica",
            features=["Positions 1-0-2", "2, 3 and 4 pole versions", "Ratings from 32A to 100A"],
            applications=["Mains and generator change-over", "Control panels"],
            attrs={"current_ratings": ["32", "50", "75", "100"], "poles": ["2", "3", "4"],
                   "switch_positions": "1-0-2"}),
    product("H-Series Delta Selector & Change-Over Switch", "Selector & Change-Over Switches",
            "Combined selector and change-over switch from the H-Series Delta range, in 32A and 50A.",
            series="H-Series Delta",
            features=["Selector 0-4 and change-over 1-0-2", "2 pole", "32A and 50A"],
            applications=["Control panels", "Supply switching"],
            attrs={"current_ratings": ["32", "50"], "poles": ["2"],
                   "switch_positions": "Selector 0-4, change-over 1-0-2"}),
    product("Copper Bus Bar", "Copper Bus Bars",
            "Copper bus bars in blue, grey and white, in 50 cm and 100 cm lengths.",
            features=["Copper construction", "50 cm and 100 cm lengths"],
            applications=["Distribution boards", "Breaker interconnection"],
            attrs={"bar_length": ["50", "100"], "colours": ["Blue", "Grey", "White"]}),
    product("Sphiro LED Strip Light (Wire)", "LED Strip Lights",
            "Sphiro LED strip light with 2835 chips, in several widths, colours and colour temperatures.",
            series="Sphiro LED", featured=True,
            features=["2835 LED chips", "Widths: 6, 8 and 10 mm", "3000K, 4000K and 6500K"],
            applications=["Decorative and accent lighting", "Cove and ceiling lighting"],
            attrs={"strip_width": ["6", "8", "10"], "colour_temperature": ["3000", "4000", "6500"],
                   "colours": ["Blue", "Green", "Ice Blue", "Ice Green", "Purple", "Red"],
                   "led_chip": "2835"}),
    product("Sphiro LED Strip Light (Wireless)", "LED Strip Lights",
            "Sphiro LED strip light, wireless version, with 2835 chips.",
            series="Sphiro LED",
            features=["2835 LED chips", "Widths: 6.8 and 10 mm", "3000K, 4000K and 6500K"],
            applications=["Decorative and accent lighting"],
            attrs={"strip_width": ["6.8", "10"], "colour_temperature": ["3000", "4000", "6500"],
                   "colours": ["Blue", "Ice Blue", "Ice Green", "Purple"], "led_chip": "2835"}),
    product("Sphiro Open Panel Light", "Sphiro LED Fixtures",
            "Sphiro LED open panel light for ceilings and interiors.",
            series="Sphiro LED",
            features=["Part of the Sphiro LED range", "LED lighting"],
            applications=["Offices and shops", "Homes"]),
    product("Sphiro LED Down Light", "Sphiro LED Fixtures",
            "Sphiro LED down light for recessed ceiling installation.",
            series="Sphiro LED",
            features=["Part of the Sphiro LED range", "LED lighting"],
            applications=["Offices and shops", "Homes"]),
    product("Sphiro Eyeball LED Light", "Sphiro LED Fixtures",
            "Sphiro eyeball LED light with an adjustable head.",
            series="Sphiro LED",
            features=["Part of the Sphiro LED range", "LED lighting"],
            applications=["Display and accent lighting"]),
    product("LED Panel Light", "LED Panel Lights & Digital Lights",
            "Panel lights in five colours, in standard and digital versions.",
            features=["Red, green, yellow, blue and white", "Standard and digital versions"],
            applications=["Control panels", "Status indication"],
            attrs={"colours": ["Red", "Green", "Yellow", "Blue", "White"]}),
    product("Hybrid Network Cable CAT-6", "Network Cables",
            "CAT-6 UTP network cable from the Hybrid series, with a bare copper conductor.",
            series="Hybrid", featured=True,
            features=["Bare copper conductor", "CAT-6 UTP", "100 m and 305 m lengths"],
            applications=["Connecting network devices", "Structured cabling"],
            attrs={"core_material": "Bare Copper (BC)", "cable_length": ["100", "305"]}),
    product("Omni Network Cable CAT-6", "Network Cables",
            "CAT-6 UTP network cable from the Omni series, with a copper covered aluminium conductor.",
            series="Omni",
            features=["Copper covered aluminium conductor", "CAT-6 UTP", "100 m and 305 m lengths"],
            applications=["Connecting network devices", "Structured cabling"],
            attrs={"core_material": "Copper Covered Aluminium (CCA)", "cable_length": ["100", "305"]}),
    product("Coaxial Cable (RG-6 & RG-7)", "Coaxial Cables",
            "Coaxial cable in RG-6 and RG-7 types for cable TV, LED TV and data communications.",
            series="Delixi Gold",
            features=["RG-6 and RG-7 types", "100 m length"],
            applications=["Cable and LED TV", "Data communications"],
            attrs={"core_material": "CCS", "cable_length": ["100"], "coax_type": ["RG-6", "RG-7"]}),
    product("Black Gold CBB61 Capacitor", "Capacitors",
            "CBB61 capacitors from the Black Gold series, in 2.5 to 4.5 µF.",
            series="Black Gold", model="CBB61",
            features=["Bakelite plasticized case", "Good insulation resistance and sealing",
                      "Developed to American Electronics Association standard"],
            applications=["AC applications"],
            attrs={"capacitance": ["2.5", "3.5", "4.5"], "rated_voltage": "400 V, 50 Hz"}),
    product("Yachica CBB60 Capacitor", "Capacitors",
            "CBB60 capacitors from the Yachica series, in eleven ratings from 2.5 to 30 µF.",
            series="Yachica", model="CBB60", featured=True,
            features=["Bakelite plasticized case", "Eleven capacitance ratings",
                      "Developed to American Electronics Association standard"],
            applications=["AC applications"],
            attrs={"capacitance": ["2.5", "3.5", "4.5", "6", "8", "10", "12", "16", "20", "25", "30"],
                   "rated_voltage": "400 VAC, 50 Hz"}),
]


# ---------------------------------------------------------------- helpers

async def get_or_create(session: AsyncSession, model, lookup: dict, defaults: dict | None = None):
    result = await session.execute(select(model).filter_by(**lookup))
    obj = result.scalar_one_or_none()
    if obj is not None:
        return obj, False
    obj = model(**lookup, **(defaults or {}))
    session.add(obj)
    await session.flush()
    return obj, True


def value_columns(definition: AttributeDefinition, value) -> dict:
    """Map a Python value onto the right column, checking it against the definition."""
    if definition.data_type == "multi_choice":
        bad = [v for v in value if v not in definition.choices]
    elif definition.data_type == "single_choice":
        bad = [] if value in definition.choices else [value]
    else:
        bad = []
    if bad:
        raise ValueError(f"{definition.key}: {bad} not in choices {definition.choices}")
    if definition.data_type == "number":
        return {"value_number": Decimal(str(value))}
    if definition.data_type == "boolean":
        return {"value_bool": value}
    if definition.data_type == "multi_choice":
        return {"value_choices": list(value)}
    return {"value_text": value}  # text and single_choice


# ---------------------------------------------------------------- seeding

async def seed(session: AsyncSession) -> None:
    published = {"status": "published", "is_placeholder": True}

    brand, _ = await get_or_create(session, Brand, {"slug": "ideal-electric"}, {
        "name": "Ideal Electric",
        "description": "Importer and distributor of electrical and lighting products across Pakistan.",
        **published,
    })

    series = {}
    for i, name in enumerate(SERIES):
        series[name], _ = await get_or_create(
            session, Series, {"slug": slugify(name)},
            {"brand_id": brand.id, "name": name, "sort_order": i, **published},
        )

    industries = {}
    for i, (name, summary) in enumerate(INDUSTRIES):
        industries[name], _ = await get_or_create(
            session, Industry, {"slug": slugify(name)},
            {"name": name, "summary": summary, "sort_order": i, **published},
        )

    categories, top_level_of = {}, {}
    for i, (top_name, children) in enumerate(CATEGORIES.items()):
        top, _ = await get_or_create(session, Category, {"slug": slugify(top_name)}, {
            "name": top_name, "description": TOP_DESCRIPTIONS[top_name],
            "sort_order": i, **published,
        })
        categories[top_name] = top
        top_level_of[top_name] = top_name
        for j, child_name in enumerate(children):
            categories[child_name], _ = await get_or_create(
                session, Category, {"slug": slugify(child_name)},
                {"parent_id": top.id, "name": child_name,
                 "description": f"{child_name} from Ideal Electric.", "sort_order": j, **published},
            )
            top_level_of[child_name] = top_name

    attributes = {}
    for i, spec in enumerate(ATTRIBUTES):
        defaults = {k: v for k, v in spec.items() if k != "key"}
        attributes[spec["key"]], _ = await get_or_create(
            session, AttributeDefinition, {"key": spec["key"]}, {**defaults, "sort_order": i},
        )

    for category_name, keys in CATEGORY_ATTRIBUTES.items():
        for i, key in enumerate(keys):
            await get_or_create(
                session, CategoryAttribute,
                {"category_id": categories[category_name].id, "attribute_id": attributes[key].id},
                {"sort_order": i},
            )

    new_by_category: dict[str, list[Product]] = {}
    for i, spec in enumerate(PRODUCTS):
        series_obj = series[spec["series"]] if spec["series"] else None
        item, created = await get_or_create(session, Product, {"slug": slugify(spec["name"])}, {
            "category_id": categories[spec["category"]].id,
            "brand_id": brand.id,
            "series_id": series_obj.id if series_obj else None,
            "name": spec["name"],
            "model_code": spec["model"],
            "summary": spec["summary"],
            "description": f"{spec['summary']} Contact Ideal Electric for ratings, availability and pricing.",
            "is_featured": spec["featured"],
            "sort_order": i,
            **published,
        })
        if not created:
            continue

        for kind, texts in (("feature", spec["features"]), ("application", spec["applications"])):
            for j, text in enumerate(texts):
                session.add(ProductHighlight(product_id=item.id, kind=kind, text=text, sort_order=j))

        for key, value in spec["attrs"].items():
            definition = attributes[key]
            session.add(ProductAttributeValue(
                product_id=item.id, attribute_id=definition.id, **value_columns(definition, value),
            ))

        for industry_name in TOP_INDUSTRIES[top_level_of[spec["category"]]]:
            session.add(ProductIndustry(product_id=item.id, industry_id=industries[industry_name].id))

        new_by_category.setdefault(spec["category"], []).append(item)

    for group in new_by_category.values():
        for item in group:
            others = [o for o in group if o.id != item.id][:3]
            for j, other in enumerate(others):
                session.add(RelatedProduct(product_id=item.id, related_product_id=other.id, sort_order=j))

    print(f"Created {sum(len(g) for g in new_by_category.values())} new products.")


async def main() -> None:
    async with async_session_factory() as session:
        async with session.begin():
            await seed(session)
    await engine.dispose()
    print("Seed complete.")


if __name__ == "__main__":
    asyncio.run(main())