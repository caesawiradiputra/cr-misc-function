"""Realistic random values: the `fake` library and the rules that pick a call."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent / "support"))

from bruno_loader import load  # noqa: E402

needs_node = pytest.mark.skipif(
    shutil.which("node") is None, reason="node is not installed"
)


@pytest.fixture()
def fk():
    return load("bruno_fake")


@pytest.fixture()
def disc():
    return load("bruno_discover")


@pytest.fixture()
def vals():
    return load("bruno_values")


@pytest.mark.parametrize(
    ("path", "example", "expected"),
    [
        ("request_id", "266ea41d-adf5-480b-af50-15b940c2b846", "fake.uuid()"),
        # a schema typo (11 characters in the last group) is still a uuid
        (
            "customer.org.customer_cif_id",
            "f100a6ee-d2c3-4e26-bff3-d5da4ddc789",
            "fake.uuid()",
        ),
        ("customer.ktp.id", "3509212345678001", "fake.ktp()"),
        ("customer.spouse.id", "3509212345678001", "fake.ktp()"),
        ("customer.ktp.dob", "2006-01-02", "fake.dob()"),
        ("application.some_day", "2006-01-02", "fake.date()"),
        ("application.date", "2019-08-24T14:15:22Z", "fake.datetime()"),
        ("customer.contact.email", "email@example.com", "fake.email()"),
        ("customer.contact.phone", "+62-81938808888", "fake.phone()"),
        ("customer.ktp.name", "PRAPTO PRAWIRODIRJO", "fake.name()"),
        ("customer.personal.mother_name", "SAMPLE VALUE", "fake.name()"),
        ("customer.employment.company_name", "SOME SAMPLE NAME", "fake.company()"),
        ("customer.ktp.city", "NAMA KOTA", "fake.city()"),
        ("customer.ktp.address", "Jln. Kenangan No. 69", "fake.address()"),
        ("customer.ktp.province_id", "36", "fake.provinceId()"),
        ("vehicles.license_plate", "ABC12345ABC", "fake.plate()"),
        ("origin.network.ip", "10.0.0.1", "fake.ip()"),
        ("customer.address.zip_code", "123456", 'fake.like("123456")'),
        ("customer.ktp.city_id", "36.74", 'fake.like("36.74")'),
        ("area.area_id", "IDX12345IDX", 'fake.like("IDX12345IDX")'),
        # one digit is a code from a closed list, so it stays as it is
        ("vehicles.bpkb_ownership", "2", '"2"'),
        # a short code keeps its example; a dotted code with letters too
        ("customer.bank_account.bank_code", "CIMB", '"CIMB"'),
        ("vehicles.variant_code", "MTRHONDA.PCX.150", '"MTRHONDA.PCX.150"'),
        ("customer.ktp.occupation", "KARYAWAN SWASTA", 'fake.sp("KARYAWAN SWASTA")'),
    ],
)
def test_call_is_picked_from_the_example_and_the_field_name(
    fk, path, example, expected
):
    assert fk.fake_expr(path, example) == expected


def test_a_placeholder_example_never_gives_two_words(fk):
    # A space in a value that the receiver forwards and signs as it is made the HMAC
    # signature fail (tested on a dev service: 'SUDIRMAN KENANGA' failed, 'SUDIRMAN' passed).
    assert (
        fk.fake_expr("customer.personal.home_ownership", "SAMPLE VALUE")
        == "fake.word()"
    )
    assert fk.fake_expr("product.product_name", "SOME SAMPLE NAME") == "fake.word()"
    assert fk.fake_expr("application.lead_id", "SOME-IDENTIFIER") == "fake.uuid()"
    assert fk.fake_expr("agent.marketing_id", "MARKETING_ID") == "fake.uuid()"


def test_no_example_keeps_the_marker_fallback(fk):
    assert fk.fake_expr("type", None) is None
    assert fk.fake_expr("type", "") is None
    assert fk.int_expr("limit", None) is None


def test_integer_and_float_hints(fk):
    assert fk.int_expr("vehicles.manufacturing_year", 2021) == "rnd(2012, 2025)"
    assert fk.int_expr("application.tenure_month", 6) == "rnd(3, 12)"
    assert "Math.round" in fk.int_expr("application.loan_amount", 3000000)
    assert fk.int_expr("x", True) is None
    assert fk.float_expr("origin.geo_location.latitude") == "fake.latitude()"
    assert fk.float_expr("origin.geo_location.longitude") == "fake.longitude()"
    assert fk.float_expr("price") is None


def test_generator_uses_the_library_but_keeps_a_field_limit(disc, vals):
    F, M = disc.FieldSpec, disc.ModelSpec
    model = M(
        "B",
        [
            F("ktp", "str", True, None, {}, "3509212345678001"),
            F("limited", "str", True, None, {"max_length": 5}, "3509212345678001"),
            F("noexample", "str", True),
        ],
        disc.Source("a.py", 1),
    )
    script = vals.random_js(model, central=True).script
    assert '"ktp": fake.ktp()' in script
    limited = script[script.index('"limited"') :]
    assert '"limited": "TEST_"' in limited
    assert "fake.ktp()" not in limited
    assert '"noexample": "TEST_"' in script
    assert "const { rnd, pick, chars, ALNUM, fake } = globalThis.__lib;" in script


def test_inline_script_carries_the_library_only_when_it_uses_it(disc, vals):
    F, M = disc.FieldSpec, disc.ModelSpec
    used = M(
        "B",
        [F("id", "str", True, None, {}, "3509212345678001")],
        disc.Source("a.py", 1),
    )
    plain = M("B", [F("note", "str", True)], disc.Source("a.py", 1))
    assert "const fake = (() => {" in vals.random_js(used, central=False).script
    assert "const fake" not in vals.random_js(plain, central=False).script


@needs_node
def test_library_output_has_the_right_formats(vals, fk):
    script = (
        vals.PRELUDE + fk.FAKE_JS + "const out = [];\n"
        "for (let i = 0; i < 300; i++) out.push({\n"
        "  uuid: fake.uuid(), ktp: fake.ktp(), name: fake.name(), phone: fake.phone(),\n"
        "  email: fake.email(), dob: fake.dob(), date: fake.date(), dt: fake.datetime(),\n"
        "  plate: fake.plate(), lat: fake.latitude(), lng: fake.longitude(),\n"
        '  like: fake.like("IDX12345IDX"), ip: fake.ip(), word: fake.word(),\n'
        "});\n"
        "fake.opts.spaces = false;\n"
        "const flat = Array.from({ length: 50 }, () => [fake.name(), fake.address(), fake.city(), fake.plate()]);\n"
        "console.log(JSON.stringify({ out, flat }));\n"
    )
    run = subprocess.run(
        ["node", "-e", script], capture_output=True, text=True, timeout=30, check=True
    )
    data = json.loads(run.stdout)
    import re

    for r in data["out"]:
        # the first 5 characters are "bruno", so a Bruno call is told apart from a real request
        assert re.fullmatch(
            r"bruno[0-9a-f]{3}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}",
            r["uuid"],
        )
        assert re.fullmatch(r"\d{16}", r["ktp"])
        assert 1 <= int(r["ktp"][6:8]) % 40 <= 31 and 1 <= int(r["ktp"][8:10]) <= 12
        assert re.fullmatch(r"[A-Z][a-z]+ [A-Z][a-z]+", r["name"])
        assert re.fullmatch(r"\+62-8\d{10}", r["phone"])
        assert re.fullmatch(r"[a-z.]+\d+@example\.com", r["email"])
        assert re.fullmatch(r"(19[7-9]\d|200\d)-\d{2}-\d{2}", r["dob"])
        assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", r["date"])
        assert re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", r["dt"])
        assert re.fullmatch(r"[A-Z]{1,2} \d{1,4} [A-Z]{1,3}", r["plate"])
        assert -10 <= r["lat"] <= 5 and 95 <= r["lng"] <= 141
        assert re.fullmatch(r"[A-Z]{3}\d{5}[A-Z]{3}", r["like"])
        assert re.fullmatch(r"\d+\.\d+\.\d+\.\d+", r["ip"])
        assert re.fullmatch(r"[A-Z]+", r["word"])
    # spaces=false removes every space from names, addresses, places and plates
    assert all(" " not in v for row in data["flat"] for v in row)
