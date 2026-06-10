from pathlib import Path

from brewconvert import detect_format, read_recipes, write_recipes

FIXTURES = Path(__file__).parent / "fixtures"


def test_detect_new_formats():
    assert detect_format(FIXTURES / "sample.beerjson") == "beerjson"
    assert detect_format(FIXTURES / "sample.brewfather.json") == "brewfather-json"
    assert detect_format(FIXTURES / "test.btp") == "beertools-btp"
    assert detect_format(FIXTURES / "sample.promash.txt") == "promash-text"


def test_read_beerjson():
    recipes = read_recipes(FIXTURES / "sample.beerjson")
    assert len(recipes) == 1
    assert recipes[0].name == "BeerJSON Pale Ale"
    assert len(recipes[0].fermentables) == 1
    assert len(recipes[0].hops) == 1
    assert len(recipes[0].yeasts) == 1
    assert len(recipes[0].mash_steps) == 1


def test_read_brewfather_json():
    recipes = read_recipes(FIXTURES / "sample.brewfather.json")
    assert len(recipes) == 1
    assert recipes[0].name == "Brewfather Pale Ale"
    assert recipes[0].batch_size_l == 20
    assert len(recipes[0].fermentables) == 1
    assert len(recipes[0].hops) == 1


def test_read_beertools_btp_sample():
    recipes = read_recipes(FIXTURES / "test.btp")
    assert len(recipes) == 1
    assert recipes[0].name
    assert len(recipes[0].fermentables) >= 1
    assert len(recipes[0].hops) >= 1
    assert len(recipes[0].yeasts) >= 1


def test_read_promash_text():
    recipes = read_recipes(FIXTURES / "sample.promash.txt")
    assert len(recipes) == 1
    assert recipes[0].name == "ProMash Pale Ale"
    assert len(recipes[0].fermentables) >= 1
    assert len(recipes[0].hops) >= 1
    assert len(recipes[0].mash_steps) >= 1


def test_write_new_formats_smoke(tmp_path):
    recipes = read_recipes(FIXTURES / "sample.beerjson")
    outputs = {
        "beerjson": tmp_path / "out.beerjson",
        "brewfather-json": tmp_path / "out.json",
        "beertools-btp": tmp_path / "out.btp",
        "promash-text": tmp_path / "out.promash.txt",
    }
    for fmt, out in outputs.items():
        write_recipes(recipes, out, format=fmt)
        assert out.exists()
        assert out.stat().st_size > 0
