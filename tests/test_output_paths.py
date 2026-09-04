from pathlib import Path

from app.config.offer_types import OfferType
from app.utils.output_paths import (
    get_error_directory,
    get_output_directory,
    get_zip_directory,
)


def test_output_directories_are_type_scoped():
    zip_dir = get_zip_directory(OfferType.USED_INVENTORY)
    err_dir = get_error_directory(OfferType.USED_INVENTORY)
    base = get_output_directory(OfferType.USED_INVENTORY)

    assert zip_dir.parent == base
    assert err_dir.parent == base
    assert base.name == "used_inventory"
    assert zip_dir.name == "zip"
    assert err_dir.name == "errors"
    assert zip_dir.is_dir() and err_dir.is_dir()


def test_types_do_not_share_directories():
    sales_zip = get_zip_directory("sales_specials")
    service_zip = get_zip_directory("service_specials")
    assert sales_zip != service_zip
    assert Path(sales_zip).parent.name == "sales_specials"
    assert Path(service_zip).parent.name == "service_specials"
