import argparse

from dotenv import load_dotenv

load_dotenv()

from app.config.offer_types import (  # noqa: E402
    DEFAULT_OFFER_TYPE,
    normalize_offer_type,
    supported_values,
)
from app.config.type_registry import get_processor  # noqa: E402
from app.core.config import settings  # noqa: E402


def main(excel_path: str, offer_type: str | None = None) -> None:
    resolved = normalize_offer_type(offer_type)
    processor = get_processor(resolved)
    result = processor.process(excel_path)
    print(f"Type:   {resolved.value}")
    print(f"Source: {result.source_file}")
    for dealer in result.dealers:
        print(f"\n{dealer.dealer_id} - {dealer.dealer_name}")
        if dealer.zip_path:
            print(f"  zip: {dealer.zip_path}")
        if dealer.error_file_path:
            print(f"  error file: {dealer.error_file_path}")
        for key, count in dealer.offer_counts.items():
            note = dealer.errors.get(key)
            suffix = f" - {note}" if note else ""
            print(f"  {key}: {count}{suffix}")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Vehicle Offer Extraction — run a single offer type end to end."
    )
    parser.add_argument(
        "--type",
        default=None,
        help=(
            "Offer type to process. Defaults to "
            f"{DEFAULT_OFFER_TYPE.value}. Supported: {', '.join(supported_values())}."
        ),
    )
    parser.add_argument(
        "--path",
        default=None,
        help="Path to the dealer-URL Excel workbook.",
    )
    # Backwards-compatible positional path (old usage: `python main.py file.xlsx`).
    parser.add_argument(
        "path_positional", nargs="?", default=None, help=argparse.SUPPRESS
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    path = args.path or args.path_positional or settings.default_excel_path
    main(path, args.type)
