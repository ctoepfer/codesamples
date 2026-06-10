KG_TO_OZ = 35.27396194958
OZ_TO_KG = 1 / KG_TO_OZ
L_TO_FLOZ = 33.8140227018
FLOZ_TO_L = 1 / L_TO_FLOZ

def kg_to_oz(value: float | None) -> float | None:
    return None if value is None else value * KG_TO_OZ

def oz_to_kg(value: float | None) -> float | None:
    return None if value is None else value * OZ_TO_KG

def l_to_floz(value: float | None) -> float | None:
    return None if value is None else value * L_TO_FLOZ

def floz_to_l(value: float | None) -> float | None:
    return None if value is None else value * FLOZ_TO_L

def c_to_f(value: float | None) -> float | None:
    return None if value is None else value * 9 / 5 + 32

def f_to_c(value: float | None) -> float | None:
    return None if value is None else (value - 32) * 5 / 9
