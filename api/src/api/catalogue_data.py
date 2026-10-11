"""Catalogue content for Ideal Electric.

Source: the owner's catalogue specification, checked against the rate-list photo, the flyer and
the Sphiro sheet. Nothing here is a price. Summaries and descriptions are placeholder wording
(everything is seeded with is_placeholder=True) until the owner reviews them.
"""
from __future__ import annotations

SERIES = [
    "IDEAL", "Libra Gold", "Delta Gold", "Yachica", "Cesco", "H-Series Delta",
    "Black Gold", "Plazma", "Hybrid", "Omni", "Delixi Gold", "Sphiro LED",
]

INDUSTRIES = [
    ("Residential", "Electrical components for homes and apartments."),
    ("Commercial", "Protection, lighting and cabling for shops, offices and buildings."),
    ("Industrial", "Switching and protection for plants, workshops and machinery."),
    ("Construction", "Supply for building projects."),
    ("Electrical Contracting", "Stock for contractors and installers."),
    ("Government & Public Sector", "Supply to public institutions and organisations."),
]

CATEGORIES = {
    "Circuit Protection": [
        "Miniature Circuit Breakers",
        "DC Power Circuit Breakers & Protectors",
        "Safety Breakers",
        "Molded Case Circuit Breakers",
    ],
    "Switchgear & Control": ["Selector Switches", "Change-Over Switches", "Copper Bus Bars"],
    "Lighting Solutions": [
        "LED Panel Lights & Digital Lights", "Colour Strip Lights", "Strip Light Adaptors",
        "LED Downlights", "Eyeball LED Lights", "Open Panel Lights", "Sensor Lamps",
        "Track Lights", "Purification Fixtures",
    ],
    "Cables & Connectivity": ["Network Cables", "Coaxial Cables"],
    "Capacitors": [],
}

TOP_DESCRIPTIONS = {
    "Circuit Protection": "Miniature, DC and molded-case circuit breakers, protectors and safety breakers.",
    "Switchgear & Control": "Selector and change-over switches and copper bus bars.",
    "Lighting Solutions": "Sphiro LED lighting and panel indicator lights.",
    "Cables & Connectivity": "Network and coaxial cables.",
    "Capacitors": "AC capacitors in bakelite cases.",
}

CURRENT = ["2", "4", "6", "10", "15", "16", "20", "30", "32", "50", "60", "63",
           "75", "100", "125", "160", "200", "250"]
COLOURS = ["Red", "Green", "Yellow", "Blue", "White", "Grey", "Ice Blue", "Ice Green", "Purple"]
CCT = ["3000 K", "4000 K", "6500 K"]
STRIP_OPTIONS = CCT + ["Blue", "Green", "Ice Blue", "Ice Green", "Purple", "Red"]
WATTS = ["3", "5", "6", "7", "12", "18", "20", "24", "30", "40"]


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
    attr("poles", "Poles", "single_choice", choices=["1", "2", "3", "4"],
         group="Electrical", filterable=True),
    attr("switch_positions", "Switch Positions", "text", group="Electrical"),
    attr("capacitance", "Capacitance", "multi_choice", unit="µF",
         choices=["2.5", "3.5", "4.5", "6", "8", "10", "12", "16", "20", "25", "30"],
         group="Electrical", filterable=True, inquiry=True),
    attr("rated_voltage", "Rated Voltage", "text", group="Electrical"),
    attr("frequency", "Frequency", "text", group="Electrical"),
    attr("cable_standard", "Cable Standard", "single_choice", choices=["CAT 6", "RG/6", "RG/7"],
         group="Construction", filterable=True),
    attr("cable_construction", "Construction", "text", group="Construction"),
    attr("cable_length", "Cable Length", "multi_choice", unit="m", choices=["100", "305"],
         group="Construction", filterable=True, inquiry=True),
    attr("material", "Material", "text", group="Construction"),
    attr("bar_length", "Bar Length", "multi_choice", unit="cm", choices=["50", "100"],
         group="Construction", inquiry=True),
    attr("colours", "Colours", "multi_choice", choices=COLOURS,
         group="Appearance", filterable=True, inquiry=True),
    attr("panel_light_type", "Type", "single_choice", choices=["Simple", "Digital"],
         group="Lighting", filterable=True),
    attr("strip_construction", "Construction", "single_choice",
         choices=["Wire", "Wire Less", "Wireless Frosted"], group="Lighting", filterable=True),
    attr("strip_width", "Strip Width", "single_choice", unit="mm",
         choices=["6", "6.8", "8", "10"], group="Lighting", filterable=True),
    attr("led_chip", "LED", "text", group="Lighting"),
    attr("led_notation", "LED Notation", "text", group="Lighting"),
    attr("colour_options", "Colour / Colour Temperature", "multi_choice", choices=STRIP_OPTIONS,
         group="Lighting", filterable=True, inquiry=True),
    attr("wattage", "Wattage", "multi_choice", unit="W", choices=WATTS,
         group="Lighting", filterable=True, inquiry=True),
    attr("shape", "Shape", "single_choice", choices=["Round", "Square"],
         group="Lighting", filterable=True),
    attr("driver_size", "Driver Size", "multi_choice", unit="mm", choices=["6", "8", "10"],
         group="Lighting", inquiry=True),
]

CATEGORY_ATTRIBUTES = {
    "Miniature Circuit Breakers": ["current_ratings", "poles"],
    "DC Power Circuit Breakers & Protectors": ["current_ratings"],
    "Safety Breakers": ["current_ratings"],
    "Molded Case Circuit Breakers": ["current_ratings", "poles"],
    "Selector Switches": ["current_ratings", "poles", "switch_positions"],
    "Change-Over Switches": ["current_ratings", "poles", "switch_positions"],
    "Copper Bus Bars": ["material", "bar_length", "colours"],
    "LED Panel Lights & Digital Lights": ["panel_light_type", "colours"],
    "Colour Strip Lights": ["strip_construction", "strip_width", "led_chip", "led_notation",
                            "colour_options"],
    "Strip Light Adaptors": ["driver_size"],
    "LED Downlights": ["wattage"],
    "Eyeball LED Lights": ["wattage"],
    "Open Panel Lights": ["shape", "wattage"],
    "Sensor Lamps": ["shape", "wattage"],
    "Track Lights": ["wattage"],
    "Purification Fixtures": ["wattage"],
    "Network Cables": ["cable_standard", "cable_construction", "cable_length"],
    "Coaxial Cables": ["cable_standard", "cable_construction", "cable_length"],
    "Capacitors": ["capacitance", "rated_voltage", "frequency"],
}

# Things the sources leave open. The seed prints these so they are not forgotten.
OPEN_ITEMS = [
    "H-Series Delta: the price-list photo seems to show 32 A and 50 A rows, with selector '0-4' "
    "combined with change-over; seeded per the specification (32 A, 2 pole, 0-1-2-3-4).",
    "Change-over positions: the specification says 0-1-2, the price-list photo reads 1-0-2; "
    "seeded per the specification.",
    "Libra Gold 1 pole 63 A: seeded per the specification; not visible in the price-list photo.",
    "Hybrid Series UTP BC CAT 6, 100 m: seeded per the specification; the photo is too small to verify.",
    "Cesco: the rate list and introductory letter print 'CESCO'; 'SESCO' was not found in them.",
    "Sphiro LED is treated as a series under Ideal Electric (not confirmed).",
    "Safety Breaker NT-50: series Plazma per the specification; the flyer text says 'Gold & Yachica'.",
    "DC items: two protectors plus one breaker family (32, 63, 125 A); names kept as listed, "
    "'V+A+Kwh' unverified.",
    "Black Gold capacitor voltage: the photo reads '400V'; seeded as 400 VAC per the specification.",
    "Delta Gold MCB: no ratings or poles in any source; seeded without specifications.",
    "Sphiro wattages, shapes and the purification fixture could not be cross-checked "
    "(only the strip-light sheet was readable).",
]


def product(name, category, summary, *, series="IDEAL", model=None, family=None,
            features=(), applications=(), attrs=None, featured=False):
    return {
        "name": name, "category": category, "summary": summary, "series": series,
        "model": model, "family": family, "features": features,
        "applications": applications, "attrs": attrs or {}, "featured": featured,
    }


PRODUCTS: list[dict] = []


def add(name, category, summary, **kwargs):
    PRODUCTS.append(product(name, category, summary, **kwargs))


def amps_text(values):
    return f"Ratings: {', '.join(values)} A"


def watts_text(values):
    return f"Wattages: {', '.join(values)} W"


# ---------------------------------------------------------------- cables

add("Hybrid Series UTP BC CAT 6", "Network Cables",
    "CAT 6 UTP network cable from the Hybrid series.",
    series="Hybrid", featured=True,
    features=["Bare copper (BC) conductor", "CAT 6, UTP construction", "Lengths: 100 m and 305 m"],
    applications=["Connecting network devices to one another"],
    attrs={"cable_standard": "CAT 6", "cable_construction": "UTP BC", "cable_length": ["100", "305"]})
add("Omni Series D/PVC CAT 6", "Network Cables",
    "CAT 6 network cable from the Omni series, listed as D/PVC.",
    series="Omni",
    features=["CAT 6", "Length: 305 m"],
    applications=["Connecting network devices to one another"],
    attrs={"cable_standard": "CAT 6", "cable_construction": "D/PVC", "cable_length": ["305"]})
add("Omni Series UTP CCA CAT 6", "Network Cables",
    "CAT 6 UTP network cable from the Omni series, with a copper-clad aluminium conductor.",
    series="Omni",
    features=["Copper-clad aluminium (CCA) conductor", "CAT 6, UTP construction",
              "Lengths: 100 m and 305 m"],
    applications=["Connecting network devices to one another"],
    attrs={"cable_standard": "CAT 6", "cable_construction": "UTP CCA", "cable_length": ["100", "305"]})
for rg in ("RG/6", "RG/7"):
    add(f"Delixi Gold {rg} + FPE CCS", "Coaxial Cables",
        f"Coaxial cable, {rg} with FPE CCS construction, from the Delixi Gold series.",
        series="Delixi Gold",
        features=[f"{rg} coaxial", "FPE CCS, as listed", "Lengths: 100 m and 305 m"],
        applications=["Cable TV and LED TV", "Data communications"],
        attrs={"cable_standard": rg, "cable_construction": "FPE CCS", "cable_length": ["100", "305"]})

# ---------------------------------------------------------------- capacitors

for series, model, values in (
    ("Black Gold", "CBB61", ["2.5", "3.5", "4.5"]),
    ("Yachica", "CBB60", ["2.5", "3.5", "4.5", "6", "8", "10", "12", "16", "20", "25", "30"]),
):
    add(f"{series} {model} Capacitor", "Capacitors",
        f"{model} capacitors from the {series} series, 400 VAC, 50 Hz.",
        series=series, model=model, featured=(model == "CBB60"),
        features=["Bakelite plasticized external case", f"Capacitance: {', '.join(values)} µF",
                  "400 VAC, 50 Hz"],
        applications=["AC applications"],
        attrs={"capacitance": values, "rated_voltage": "400 VAC", "frequency": "50 Hz"})

# ---------------------------------------------------------------- bus bar

add("Copper Bus Bar", "Copper Bus Bars",
    "Copper bus bar in blue, grey and white, in 50 cm and 100 cm lengths.",
    features=["Copper", "Lengths: 50 cm and 100 cm", "Colours: blue, grey, white"],
    attrs={"material": "Copper", "bar_length": ["50", "100"], "colours": ["Blue", "Grey", "White"]})

# ---------------------------------------------------------------- circuit breakers

MCB_CONFIGS = {
    "Libra Gold": {"1": ["2", "4", "6", "10", "16", "20", "32", "63"],
                   "2": ["32", "63"], "3": ["32", "63"]},
    "Yachica": {"1": ["6", "10", "16", "20", "32", "63"], "2": ["32", "63"], "3": ["32", "63"]},
}
MCB_NOTES = {
    "Libra Gold": "Reliable series with stable quality.",
    "Yachica": "Cost-saving series with the same appearance and stable quality performance.",
}
for series, configs in MCB_CONFIGS.items():
    for poles, values in configs.items():
        add(f"{series} MCB, {poles} Pole", "Miniature Circuit Breakers",
            f"{series} miniature circuit breaker, {poles} pole.",
            series=series, family=f"{series}-mcb", featured=(poles == "1"),
            features=[f"{poles} pole", amps_text(values), MCB_NOTES[series]],
            attrs={"poles": poles, "current_ratings": values})

add("Delta Gold MCB", "Miniature Circuit Breakers",
    "New-generation low-voltage miniature circuit breaker from Ideal Electric.",
    series="Delta Gold", features=["New-generation low-voltage design"])

add("V+A+Kwh Protector", "DC Power Circuit Breakers & Protectors",
    "Listed in the rate list as 'V+A+Kwh Protector'. No further specification is stated.")
add("AMP 2P/63 A Protector", "DC Power Circuit Breakers & Protectors",
    "Listed in the rate list as 'AMP 2P / 63 A Protector'. No further specification is stated.")
add("DC Power Circuit Breaker", "DC Power Circuit Breakers & Protectors",
    "DC power circuit breaker, listed as 32 Amp D.C., 63 Amp D.C. and 125 Amp D.C.",
    features=[amps_text(["32", "63", "125"])],
    attrs={"current_ratings": ["32", "63", "125"]})

add("Safety Breaker NT-50", "Safety Breakers",
    "Safety breaker NT-50 from the Plazma series.",
    series="Plazma", model="NT-50",
    features=[amps_text(["10", "15", "20", "30"])],
    attrs={"current_ratings": ["10", "15", "20", "30"]})

add("Circuit Breaker (TP) Molded Case", "Molded Case Circuit Breakers",
    "Three-pole molded case circuit breaker.",
    features=["3 pole", amps_text(["30", "60", "100", "160", "200", "250"])],
    attrs={"poles": "3", "current_ratings": ["30", "60", "100", "160", "200", "250"]})

# ---------------------------------------------------------------- selector and change-over switches

SWITCH_KINDS = {
    "Selector Switch": ("Selector Switches", "0-1-2-3-4",
                        {"2": ["32", "50", "75"], "3": ["32", "50"], "4": ["75"]}),
    "Change-Over Switch": ("Change-Over Switches", "0-1-2",
                           {"2": ["32", "50", "100"], "3": ["32", "50"],
                            "4": ["32", "50", "75", "100"]}),
}
for kind, (category, positions, configs) in SWITCH_KINDS.items():
    for series in ("Yachica", "Cesco"):
        for poles, values in configs.items():
            add(f"{series} {kind}, {poles} Pole", category,
                f"{series} {kind.lower()}, {poles} pole, positions {positions}.",
                series=series, family=f"{series}-{kind}",
                features=[f"{poles} pole", amps_text(values), f"Positions {positions}"],
                attrs={"poles": poles, "current_ratings": values, "switch_positions": positions})
    add(f"H-Series Delta {kind}, 2 Pole", category,
        f"H-Series Delta {kind.lower()}, 2 pole, positions {positions}.",
        series="H-Series Delta", family=f"H-Series Delta-{kind}",
        features=["2 pole", amps_text(["32"]), f"Positions {positions}"],
        attrs={"poles": "2", "current_ratings": ["32"], "switch_positions": positions})

# ---------------------------------------------------------------- lighting

for label, suffix in (("Simple", "S"), ("Digital", "D")):
    add(f"{label} LED Panel Light", "LED Panel Lights & Digital Lights",
        f"{label} LED panel light in five colours, listed in the rate list as 'LED Panel Light ({suffix})'.",
        family="indicator-lights",
        features=["Colours: red, green, yellow, blue, white"],
        attrs={"panel_light_type": label, "colours": ["Red", "Green", "Yellow", "Blue", "White"]})

STRIPS = [
    ("Wire", "6", CCT + ["Blue", "Green", "Ice Blue", "Purple", "Red"]),
    ("Wire", "8", CCT),
    ("Wire", "10", CCT + ["Ice Green", "Red"]),
    ("Wire Less", "6.8", CCT + ["Blue", "Ice Green", "Ice Blue", "Purple"]),
    ("Wire Less", "10", CCT + ["Blue", "Ice Green", "Ice Blue", "Purple"]),
    ("Wireless Frosted", "6.8", CCT),
    ("Wireless Frosted", "8", CCT),
]
for construction, width, options in STRIPS:
    add(f"Sphiro Colour Strip Light, {construction} {width} mm", "Colour Strip Lights",
        f"Sphiro colour strip light, {construction}, 2835 / {width} mm, 120L.",
        series="Sphiro LED", family=f"strip-{construction}",
        featured=(construction == "Wire" and width == "6"),
        features=["2835 LED", f"{width} mm width", "120L (source notation)",
                  f"Colour options: {', '.join(options)}"],
        attrs={"strip_construction": construction, "strip_width": width, "led_chip": "2835",
               "led_notation": "120L", "colour_options": options})

add("Sphiro Strip Light Adaptor (Driver)", "Strip Light Adaptors",
    "Driver for Sphiro strip lights, in 6, 8 and 10 mm sizes.",
    series="Sphiro LED", features=["Driver sizes: 6, 8 and 10 mm"],
    attrs={"driver_size": ["6", "8", "10"]})
add("Sphiro LED Downlight", "LED Downlights", "Sphiro LED downlight in 5 W and 7 W.",
    series="Sphiro LED", features=[watts_text(["5", "7"])], attrs={"wattage": ["5", "7"]})
add("Sphiro Eyeball LED Light", "Eyeball LED Lights", "Sphiro eyeball LED light in 3 W and 5 W.",
    series="Sphiro LED", features=[watts_text(["3", "5"])], attrs={"wattage": ["3", "5"]})
for shape in ("Round", "Square"):
    add(f"Sphiro Open Panel Light, {shape}", "Open Panel Lights",
        f"Sphiro open panel light, {shape.lower()}, in 6, 12, 18 and 24 W.",
        series="Sphiro LED", family="open-panel",
        features=[shape, watts_text(["6", "12", "18", "24"])],
        attrs={"shape": shape, "wattage": ["6", "12", "18", "24"]})
add("Sphiro Purification Fixture", "Purification Fixtures",
    "Sphiro purification fixture, listed as 'Light, 40 W'.",
    series="Sphiro LED", features=["40 W"], attrs={"wattage": ["40"]})
add("Sphiro Sensor Lamp", "Sensor Lamps",
    "Sphiro sensor lamp, round, in 12 W and 18 W (printed 'Censor Lamp' in the brochure).",
    series="Sphiro LED", features=["Round", watts_text(["12", "18"])],
    attrs={"shape": "Round", "wattage": ["12", "18"]})
add("Sphiro Track Light", "Track Lights", "Sphiro track light in 20 W and 30 W.",
    series="Sphiro LED", features=[watts_text(["20", "30"])], attrs={"wattage": ["20", "30"]})