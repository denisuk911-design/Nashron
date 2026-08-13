from pathlib import Path

from core.asset_manifest_validator import validate_product_assets


def test_product_asset_manifest_is_package_ready():
    root = Path(__file__).resolve().parents[1]

    result = validate_product_assets(root)

    assert result.ok, result.errors
