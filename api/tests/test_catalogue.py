import pytest_asyncio
from sqlalchemy import text

from api.db import async_session_factory, engine
from api.seed import seed

SERIES = {
    "IDEAL", "Libra Gold", "Delta Gold", "Yachica", "Cesco", "H-Series Delta",
    "Black Gold", "Plazma", "Hybrid", "Omni", "Delixi Gold", "Sphiro LED",
}

CATEGORIES = {
    "Network Cables", "Coaxial Cables", "Capacitors", "Copper Bus Bars",
    "Miniature Circuit Breakers", "DC Power Circuit Breakers & Protectors", "Safety Breakers",
    "Molded Case Circuit Breakers", "Selector Switches", "Change-Over Switches",
    "LED Panel Lights & Digital Lights", "Colour Strip Lights", "Strip Light Adaptors",
    "LED Downlights", "Eyeball LED Lights", "Open Panel Lights", "Sensor Lamps",
    "Track Lights", "Purification Fixtures",
}

CCT = ["3000 K", "4000 K", "6500 K"]


@pytest_asyncio.fixture
async def catalogue():
    async with engine.begin() as conn:
        await conn.execute(
            text("TRUNCATE brands, categories, industries, attribute_definitions, products "
                 "RESTART IDENTITY CASCADE")
        )
    async with async_session_factory() as session:
        async with session.begin():
            await seed(session)
    return await snapshot()


async def snapshot() -> dict[str, dict]:
    sql = text(
        """
        SELECT p.name, s.name AS series, c.name AS category, a.key, v.value_text, v.value_choices
        FROM products p
        JOIN categories c ON c.id = p.category_id
        LEFT JOIN series s ON s.id = p.series_id
        LEFT JOIN product_attribute_values v ON v.product_id = p.id
        LEFT JOIN attribute_definitions a ON a.id = v.attribute_id
        """
    )
    async with engine.connect() as conn:
        rows = (await conn.execute(sql)).all()
    products: dict[str, dict] = {}
    for row in rows:
        entry = products.setdefault(
            row.name, {"series": row.series, "category": row.category, "attrs": {}}
        )
        if row.key is not None:
            entry["attrs"][row.key] = row.value_choices if row.value_choices is not None else row.value_text
    return products


def values(attrs: dict, key: str) -> set:
    value = attrs[key]
    return set(value) if isinstance(value, list) else {value}


def check_family(catalogue, expected: dict, *, ratings="current_ratings"):
    """expected: product name -> (series, poles, ratings)"""
    for name, (series, poles, ratings_list) in expected.items():
        assert name in catalogue, f"missing product: {name}"
        product = catalogue[name]
        assert product["series"] == series, name
        assert product["attrs"]["poles"] == poles, name
        assert values(product["attrs"], ratings) == set(ratings_list), name


async def test_catalogue_size_series_and_categories(catalogue):
    assert len(catalogue) == 51
    assert {p["series"] for p in catalogue.values()} == SERIES  # every product has a series
    assert {p["category"] for p in catalogue.values()} == CATEGORIES


async def test_mcb_configurations_are_exactly_as_specified(catalogue):
    check_family(catalogue, {
        "Libra Gold MCB, 1 Pole": ("Libra Gold", "1", ["2", "4", "6", "10", "16", "20", "32", "63"]),
        "Libra Gold MCB, 2 Pole": ("Libra Gold", "2", ["32", "63"]),
        "Libra Gold MCB, 3 Pole": ("Libra Gold", "3", ["32", "63"]),
        "Yachica MCB, 1 Pole": ("Yachica", "1", ["6", "10", "16", "20", "32", "63"]),
        "Yachica MCB, 2 Pole": ("Yachica", "2", ["32", "63"]),
        "Yachica MCB, 3 Pole": ("Yachica", "3", ["32", "63"]),
    })
    assert catalogue["Delta Gold MCB"]["series"] == "Delta Gold"
    assert catalogue["Delta Gold MCB"]["attrs"] == {}  # nothing invented


async def test_selector_and_change_over_configurations(catalogue):
    selector = {"2": ["32", "50", "75"], "3": ["32", "50"], "4": ["75"]}
    change_over = {"2": ["32", "50", "100"], "3": ["32", "50"], "4": ["32", "50", "75", "100"]}
    expected = {}
    for series in ("Yachica", "Cesco"):
        for poles, amps in selector.items():
            expected[f"{series} Selector Switch, {poles} Pole"] = (series, poles, amps)
        for poles, amps in change_over.items():
            expected[f"{series} Change-Over Switch, {poles} Pole"] = (series, poles, amps)
    expected["H-Series Delta Selector Switch, 2 Pole"] = ("H-Series Delta", "2", ["32"])
    expected["H-Series Delta Change-Over Switch, 2 Pole"] = ("H-Series Delta", "2", ["32"])
    check_family(catalogue, expected)

    assert catalogue["Yachica Selector Switch, 2 Pole"]["attrs"]["switch_positions"] == "0-1-2-3-4"
    assert catalogue["Cesco Change-Over Switch, 3 Pole"]["attrs"]["switch_positions"] == "0-1-2"


async def test_strip_light_options_match_the_invoice(catalogue):
    expected = {
        "Sphiro Colour Strip Light, Wire 6 mm":
            ("Wire", "6", CCT + ["Blue", "Green", "Ice Blue", "Purple", "Red"]),
        "Sphiro Colour Strip Light, Wire 8 mm": ("Wire", "8", CCT),
        "Sphiro Colour Strip Light, Wire 10 mm": ("Wire", "10", CCT + ["Ice Green", "Red"]),
        "Sphiro Colour Strip Light, Wire Less 6.8 mm":
            ("Wire Less", "6.8", CCT + ["Blue", "Ice Green", "Ice Blue", "Purple"]),
        "Sphiro Colour Strip Light, Wire Less 10 mm":
            ("Wire Less", "10", CCT + ["Blue", "Ice Green", "Ice Blue", "Purple"]),
        "Sphiro Colour Strip Light, Wireless Frosted 6.8 mm": ("Wireless Frosted", "6.8", CCT),
        "Sphiro Colour Strip Light, Wireless Frosted 8 mm": ("Wireless Frosted", "8", CCT),
    }
    for name, (construction, width, options) in expected.items():
        attrs = catalogue[name]["attrs"]
        assert attrs["strip_construction"] == construction, name
        assert attrs["strip_width"] == width, name
        assert values(attrs, "colour_options") == set(options), name
        assert attrs["led_chip"] == "2835" and attrs["led_notation"] == "120L", name


async def test_cables_and_capacitors(catalogue):
    cables = {
        "Hybrid Series UTP BC CAT 6": ("Hybrid", "CAT 6", ["100", "305"]),
        "Omni Series D/PVC CAT 6": ("Omni", "CAT 6", ["305"]),
        "Omni Series UTP CCA CAT 6": ("Omni", "CAT 6", ["100", "305"]),
        "Delixi Gold RG/6 + FPE CCS": ("Delixi Gold", "RG/6", ["100", "305"]),
        "Delixi Gold RG/7 + FPE CCS": ("Delixi Gold", "RG/7", ["100", "305"]),
    }
    for name, (series, standard, lengths) in cables.items():
        product = catalogue[name]
        assert product["series"] == series, name
        assert product["attrs"]["cable_standard"] == standard, name
        assert values(product["attrs"], "cable_length") == set(lengths), name

    black_gold = catalogue["Black Gold CBB61 Capacitor"]
    assert black_gold["series"] == "Black Gold"
    assert values(black_gold["attrs"], "capacitance") == {"2.5", "3.5", "4.5"}
    yachica = catalogue["Yachica CBB60 Capacitor"]
    assert values(yachica["attrs"], "capacitance") == {
        "2.5", "3.5", "4.5", "6", "8", "10", "12", "16", "20", "25", "30"}
    for capacitor in (black_gold, yachica):
        assert capacitor["attrs"]["rated_voltage"] == "400 VAC"
        assert capacitor["attrs"]["frequency"] == "50 Hz"


async def test_remaining_products(catalogue):
    nt50 = catalogue["Safety Breaker NT-50"]
    assert nt50["series"] == "Plazma"
    assert values(nt50["attrs"], "current_ratings") == {"10", "15", "20", "30"}

    mccb = catalogue["Circuit Breaker (TP) Molded Case"]
    assert mccb["series"] == "IDEAL" and mccb["attrs"]["poles"] == "3"
    assert values(mccb["attrs"], "current_ratings") == {"30", "60", "100", "160", "200", "250"}

    dc = catalogue["DC Power Circuit Breaker"]
    assert values(dc["attrs"], "current_ratings") == {"32", "63", "125"}
    assert catalogue["V+A+Kwh Protector"]["attrs"] == {}  # name kept exactly, nothing assumed

    bar = catalogue["Copper Bus Bar"]
    assert values(bar["attrs"], "bar_length") == {"50", "100"}
    assert values(bar["attrs"], "colours") == {"Blue", "Grey", "White"}

    for shape in ("Round", "Square"):
        panel = catalogue[f"Sphiro Open Panel Light, {shape}"]
        assert panel["attrs"]["shape"] == shape
        assert values(panel["attrs"], "wattage") == {"6", "12", "18", "24"}

    assert values(catalogue["Sphiro LED Downlight"]["attrs"], "wattage") == {"5", "7"}
    assert values(catalogue["Sphiro Eyeball LED Light"]["attrs"], "wattage") == {"3", "5"}
    assert values(catalogue["Sphiro Sensor Lamp"]["attrs"], "wattage") == {"12", "18"}
    assert values(catalogue["Sphiro Track Light"]["attrs"], "wattage") == {"20", "30"}
    assert values(catalogue["Sphiro Purification Fixture"]["attrs"], "wattage") == {"40"}
    assert values(catalogue["Sphiro Strip Light Adaptor (Driver)"]["attrs"], "driver_size") == {
        "6", "8", "10"}
    for label in ("Simple", "Digital"):
        lights = catalogue[f"{label} LED Panel Light"]
        assert lights["series"] == "IDEAL"
        assert values(lights["attrs"], "colours") == {"Red", "Green", "Yellow", "Blue", "White"}


async def test_siblings_are_linked_within_the_same_series_only(catalogue):
    sql = text(
        """
        SELECT o.name
        FROM related_products r
        JOIN products p ON p.id = r.product_id
        JOIN products o ON o.id = r.related_product_id
        WHERE p.name = 'Yachica Selector Switch, 2 Pole'
        """
    )
    async with engine.connect() as conn:
        names = {row.name for row in (await conn.execute(sql)).all()}
    assert names == {"Yachica Selector Switch, 3 Pole", "Yachica Selector Switch, 4 Pole"}


async def test_seeding_twice_adds_nothing(catalogue):
    async with async_session_factory() as session:
        async with session.begin():
            await seed(session)
    assert len(await snapshot()) == 51


async def test_the_old_combination_bug_is_gone_through_the_public_api(client, catalogue):
    listing = await client.get("/api/v1/products", params={"category": "selector-switches"})
    assert listing.json()["total"] == 7

    # No 75 A 3-pole selector exists, so this must find nothing.
    none = await client.get("/api/v1/products", params=[
        ("category", "selector-switches"), ("attr", "current_ratings:75"), ("attr", "poles:3")])
    assert none.json()["total"] == 0
    # No 2 A 3-pole MCB exists either.
    none = await client.get("/api/v1/products", params=[
        ("category", "miniature-circuit-breakers"), ("attr", "current_ratings:2"), ("attr", "poles:3")])
    assert none.json()["total"] == 0

    cesco = await client.get("/api/v1/products", params={"series": "cesco"})
    assert cesco.json()["total"] == 6

    facets = await client.get("/api/v1/products/facets", params={"category": "selector-switches"})
    counts = {f["key"]: {o["value"]: o["count"] for o in f["options"]}
              for f in facets.json()["attributes"]}
    assert counts["poles"] == {"2": 3, "3": 2, "4": 2}
    assert counts["current_ratings"] == {"32": 5, "50": 4, "75": 4}