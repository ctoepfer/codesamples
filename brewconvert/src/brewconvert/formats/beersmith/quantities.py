"""Conservative BSMX mappings, derived from the included paired exports.

F_M_UNITS=2 stores ounces. Other enum values are not established by the
fixture. Liquid F_Y_AMOUNT is interpreted as US fluid ounces (inferred).
BC_* fields are brewconvert extensions, NOT verified BeerSmith fields.
"""

from brewconvert.model.units import Quantity


def read_quantity(el, kind):
    extension = el.find("BC_QUANTITY")
    if extension is not None:
        return Quantity.from_measure(
            extension.text, extension.get("unit"), source_field="BC_QUANTITY"
        )
    field = "F_M_AMOUNT" if kind == "misc" else "F_Y_AMOUNT"
    value = el.findtext(field)
    if value is None:
        return None
    unit = None
    if (
        kind == "misc"
        and el.findtext("F_M_UNITS") == "2"
        and el.findtext("F_M_IMPORT_AS_WEIGHT") == "1"
    ):
        unit = "oz"
    elif kind == "yeast" and el.findtext("F_Y_FORM") == "1":
        unit = "US fl oz"
    return Quantity(
        value,
        unit,
        status="inferred",
        source_field=field,
        evidence={c.tag: c.text for c in el},
    )


def write_quantity(el, q, kind, add):
    if q is None or not q.valid or q.status == "ambiguous":
        return
    extension = add(el, "BC_QUANTITY", format(q.value, "f"))
    extension.set("unit", q.unit)
    if kind == "misc" and q.kind == "mass":
        add(el, "F_M_UNITS", 2)
        add(el, "F_M_AMOUNT", format(q.to("oz"), ".12f"))
        add(el, "F_M_IMPORT_AS_WEIGHT", 1)
    elif kind == "yeast" and q.kind == "volume":
        add(el, "F_Y_AMOUNT", format(q.to("US fl oz"), ".12f"))
