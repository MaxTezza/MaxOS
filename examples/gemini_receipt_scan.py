"""Example: Receipt scanning with Gemini multimodal capabilities.

This demonstrates how to use Gemini to extract structured data from receipt images.
"""

import asyncio
import json
from pathlib import Path

from max_os.core.gemini_client import GeminiClient
from max_os.core.multimodal_handler import MultimodalHandler


async def scan_receipt(image_path: str) -> dict:
    """Scan a receipt and extract structured data.

    Args:
        image_path: Path to receipt image

    Returns:
        Extracted receipt data as dictionary
    """
    # Initialize Gemini client
    gemini = GeminiClient(user_id="demo_user")

    # Validate image
    handler = MultimodalHandler()
    if not handler.validate_file(image_path, "image"):
        raise ValueError(f"Invalid image file: {image_path}")

    # Scan receipt
    prompt = """Extract all items, quantities, and prices from this receipt.
Return a JSON object with the following structure:
{
  "store": "store name",
  "date": "YYYY-MM-DD",
  "items": [
    {"name": "item name", "quantity": 1, "price": 0.00}
  ],
  "total": 0.00
}"""

    response = await gemini.process(text=prompt, image=image_path)

    # Parse JSON response
    try:
        # Extract JSON from response (Gemini might wrap it in markdown)
        json_start = response.find("{")
        json_end = response.rfind("}") + 1
        if json_start >= 0 and json_end > json_start:
            json_str = response[json_start:json_end]
            receipt_data = json.loads(json_str)
        else:
            receipt_data = json.loads(response)
    except json.JSONDecodeError:
        print(f"Could not parse JSON response:\n{response}")
        receipt_data = {"raw_response": response}

    return receipt_data


async def main():
    """Main function."""
    # Example usage
    print("Gemini Receipt Scanning Demo")
    print("=" * 50)

    # You would replace this with an actual receipt image path
    receipt_path = "grocery_receipt.jpg"

    if Path(receipt_path).exists():
        print(f"\nScanning receipt: {receipt_path}")
        receipt_data = await scan_receipt(receipt_path)

        print("\nExtracted Data:")
        print(json.dumps(receipt_data, indent=2))

        # Add items to pantry
        if "items" in receipt_data:
            print("\nItems to add to pantry:")
            for item in receipt_data["items"]:
                print(f"  - {item.get('name', 'Unknown')} (qty: {item.get('quantity', 1)})")
    else:
        print(f"\nReceipt image not found: {receipt_path}")
        print("This is a demo. To use this example:")
        print("1. Place a receipt image in the current directory")
        print("2. Update the 'receipt_path' variable")
        print("3. Set GOOGLE_API_KEY environment variable")
        print("4. Run this script again")


if __name__ == "__main__":
    asyncio.run(main())
