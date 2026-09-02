import sys

from dotenv import load_dotenv

load_dotenv()

from app.service.offer_generation_service import OfferGenerationService


def main(excel_path: str) -> None:
    service = OfferGenerationService()
    result = service.generate_from_excel(excel_path)
    print(f"Source: {result.source_file}")
    for dealer in result.dealers:
        print(f"\n{dealer.dealer_id} - {dealer.dealer_name}")
        if dealer.zip_path:
            print(f"  zip: {dealer.zip_path}")
        if dealer.error_file_path:
            print(f"  error file: {dealer.error_file_path}")
        for oem, count in dealer.offer_counts.items():
            note = dealer.errors.get(oem)
            suffix = f" - {note}" if note else ""
            print(f"  {oem}: {count} offers{suffix}")


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "offers/MWK00012GMC_Dealership_URLs.xlsx"
    main(path)