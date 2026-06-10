from pathlib import Path

from brewconvert import detect_format, read_recipes, write_recipes

FIXTURES = Path(__file__).parent / "fixtures"


def test_detect_beerxml():
    assert detect_format(FIXTURES / "domo_before.xml") == "beerxml"


def test_read_beerxml():
    recipes = read_recipes(FIXTURES / "domo_before.xml")
    assert len(recipes) == 1
    recipe = recipes[0]
    assert "Domo Arigato" in recipe.name
    assert len(recipe.fermentables) == 2
    assert len(recipe.hops) == 5
    assert len(recipe.miscs) >= 3


def test_detect_bsmx():
    assert detect_format(FIXTURES / "domo_after.bsmx") == "beersmith-bsmx"


def test_read_bsmx():
    recipes = read_recipes(FIXTURES / "domo_after.bsmx")
    assert len(recipes) == 1
    assert "Domo Arigato" in recipes[0].name
    assert len(recipes[0].fermentables) == 2
    assert len(recipes[0].hops) == 5


def test_write_beerxml(tmp_path):
    recipes = read_recipes(FIXTURES / "domo_before.xml")
    out = tmp_path / "out.xml"
    write_recipes(recipes, out, format="beerxml")
    assert out.exists()
    assert detect_format(out) == "beerxml"
