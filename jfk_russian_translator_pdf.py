#!/usr/bin/env python3
"""
All code generate by Claude 4.5
PDF Translation Script using Claude API
Translates each page of a Russian PDF to English and saves to individual text files.
"""
import sys
import os
import base64
import time
import random
from pathlib import Path
import argparse
from typing import Optional
# Required libraries - install with:
# pip install anthropic pdf2image pillow
import anthropic
from pdf2image import convert_from_path
from PIL import Image
import io

def setup_client() -> anthropic.Anthropic:
    api_key = os.environ.get('ANTHROPIC_API_KEY')
    if not api_key:
        print("Error: ANTHROPIC_API_KEY environment variable not set.")
        sys.exit(1)
    return anthropic.Anthropic(api_key=api_key)
def pdf_page_to_base64(image: Image.Image, quality: int = 85) -> str:
    """
    Convert a PIL Image to base64 string for Claude API.
    Args:
        image: PIL Image object
        quality: JPEG compression quality (1-100)
    Returns:
        Base64 encoded string of the image
    """
    # Convert to RGB if necessary (PDFs might be in CMYK)
    if image.mode != 'RGB':
        image = image.convert('RGB')
    # Save image to bytes buffer
    buffer = io.BytesIO()
    image.save(buffer, format='JPEG', quality=quality)
    buffer.seek(0)
    # Encode to base64
    return base64.b64encode(buffer.getvalue()).decode('utf-8')
def translate_page(client: anthropic.Anthropic, image_base64: str, page_num: int) -> Optional[str]:
    """
    Send a page image to Claude API for translation.
    Args:
        client: Anthropic client instance
        image_base64: Base64 encoded image of the PDF page
        page_num: Page number (for error reporting)
    Returns:
        Translated text or None if error
    """
    prompt = """You are a professional translator. Your task is to translate the Russian text in this image to English.
CRITICAL INSTRUCTIONS:
1. Translate ALL text visible in the image from Russian to English
2. Maintain the original structure and formatting as much as possible in plain text
3. Do NOT add any commentary, explanations, or notes about the translation
4. Do NOT add phrases like "Here is the translation" or "The translated text is"
5. Output ONLY the English translation of the text, nothing else
6. If there are page numbers, headers, or footers, translate those too
7. If the page contains tables or special formatting, represent it as clearly as possible in plain text
Begin translation immediately:"""
    try:
        message = client.messages.create(
            model="claude-3-5-sonnet-20241022",  # You can change to claude-3-opus-20240229 if preferred
            max_tokens=4000,
            temperature=0,  # Use 0 for most consistent translations
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/jpeg",
                                "data": image_base64
                            }
                        },
                        {
                            "type": "text",
                            "text": prompt
                        }
                    ]
                }
            ]
        )
        return message.content[0].text
    except Exception as e:
        print(f"Error translating page {page_num}: {str(e)}")
        return None
def process_pdf(pdf_path: str, output_dir: str = None, delay_seconds: int = 30,
                start_page: int = 1, end_page: int = None):
    """
    Main function to process the PDF file.
    Args:
        pdf_path: Path to the input PDF file
        output_dir: Directory to save output files (default: same as PDF location)
        delay_seconds: Seconds to wait between processing each page
        start_page: Page number to start from (1-indexed)
        end_page: Page number to end at (inclusive, None for last page)
    """
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        print(f"Error: File '{pdf_path}' not found.")
        sys.exit(1)
    if not pdf_path.suffix.lower() == '.pdf':
        print(f"Error: File '{pdf_path}' is not a PDF file.")
        sys.exit(1)
    if output_dir:
        output_path = Path(output_dir)
    else:
        output_path = pdf_path.parent / f"{pdf_path.stem}_translations"
    output_path.mkdir(exist_ok=True)
    print(f"Output directory: {output_path}")
    print("Initializing Claude API client...")
    client = setup_client()
    print(f"Loading PDF: {pdf_path}")
    print("Converting PDF pages to images (this may take a moment for large files)...")
    try:
        images = convert_from_path(pdf_path, dpi=200)  # Higher DPI for better OCR
        total_pages = len(images)
        print(f"Successfully loaded {total_pages} pages")
        # Determine page range first (before calculating time estimate)
        actual_start = max(1, start_page)
        actual_end = min(total_pages, end_page) if end_page else total_pages
        if actual_start > total_pages:
            print(f"Error: Start page {actual_start} exceeds total pages {total_pages}")
            sys.exit(1)
        if actual_start > actual_end:
            print(f"Error: Start page {actual_start} is greater than end page {actual_end}")
            sys.exit(1)
        print(f"WTF before pages to process")
        pages_to_process = actual_end - actual_start + 1
        print(f"WTF after pages to process {pages_to_process}")
        print(f"\nWill process pages {actual_start} to {actual_end} ({pages_to_process} pages)")
        # Calculate and display time estimate
        avg_delay_with_jitter = delay_seconds * 1.1  # Account for average 10% jitter
        estimated_time = (pages_to_process * avg_delay_with_jitter) + (pages_to_process * 5)  # 5 seconds per page for API call
        hours = estimated_time // 3600
        minutes = (estimated_time % 3600) // 60
        print(f"\nDelay between pages: {delay_seconds} seconds (plus 0-20% random jitter)")
        print(f"Estimated total time: {hours:.0f} hours {minutes:.0f} minutes for {pages_to_process} pages")
        print(f"This helps stay within API rate limits and token quotas")
        print("-" * 50)
    except Exception as e:
        print(f"Error loading PDF: {str(e)}")
        sys.exit(1)
    # Process each page
    successful_pages = 0
    failed_pages = []
    start_time = time.time()
    for page_num, image in enumerate(images, start=1):
        # Skip pages outside the requested range
        if page_num < actual_start or page_num > actual_end:
            continue
        current_page_in_batch = page_num - actual_start + 1
        print(f"\nProcessing page {page_num} (batch {current_page_in_batch}/{pages_to_process})...")
        # Show progress percentage and time remaining
        progress_pct = (current_page_in_batch - 1) / pages_to_process * 100
        elapsed_time = time.time() - start_time
        if current_page_in_batch > 1:
            avg_time_per_page = elapsed_time / (current_page_in_batch - 1)
            remaining_pages = pages_to_process - current_page_in_batch + 1
            est_remaining = remaining_pages * avg_time_per_page
            remaining_hours = int(est_remaining // 3600)
            remaining_mins = int((est_remaining % 3600) // 60)
            print(f"  Progress: {progress_pct:.1f}% - Est. time remaining: {remaining_hours}h {remaining_mins}m")
        # Convert image to base64
        print(f"  Converting page {page_num} to base64...")
        image_base64 = pdf_page_to_base64(image)
        # Translate the page
        print(f"  Sending page {page_num} to Claude for translation...")
        translation = translate_page(client, image_base64, page_num)
        if translation:
            # Save translation to file
            output_file = output_path / f"page_{page_num:04d}.txt"
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(translation)
            print(f"  ✓ Saved translation to: {output_file.name}")
            successful_pages += 1
        else:
            print(f"  ✗ Failed to translate page {page_num}")
            failed_pages.append(page_num)
        # Add delay between pages (except for the last page)
        if page_num < actual_end:
            # Add 0-20% random jitter to the delay to avoid looking too robotic
            jitter = random.uniform(0, delay_seconds * 0.2)
            actual_delay = delay_seconds + jitter
            print(f"  Waiting {actual_delay:.1f} seconds before next page (rate limit protection)...")
            # Show countdown for longer delays
            if actual_delay > 5:
                for i in range(int(actual_delay), 0, -1):
                    print(f"    {i}...", end='\r')
                    time.sleep(1)
                # Sleep for the fractional part
                time.sleep(actual_delay - int(actual_delay))
                print(" " * 20, end='\r')  # Clear the countdown line
            else:
                time.sleep(actual_delay)
    # Summary
    total_time = time.time() - start_time
    total_hours = int(total_time // 3600)
    total_mins = int((total_time % 3600) // 60)
    print("\n" + "="*50)
    print("Translation Complete!")
    print(f"Processed pages {actual_start} to {actual_end}")
    print(f"Successfully translated: {successful_pages}/{pages_to_process} pages")
    print(f"Total time: {total_hours} hours {total_mins} minutes")
    if failed_pages:
        print(f"Failed pages: {', '.join(map(str, failed_pages))}")
        print("You can try running the script again for failed pages.")
    print(f"Translations saved in: {output_path}")
    print("="*50)
def main():
    """
    Parse command line arguments and run the translation process.
    """
    parser = argparse.ArgumentParser(
        description='Translate a Russian PDF to English using Claude API',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Example usage:
  python translate_pdf.py document.pdf
  python translate_pdf.py document.pdf --delay 30
  python translate_pdf.py document.pdf --output-dir ./translations --delay 60
Resume/partial processing:
  python translate_pdf.py document.pdf --start-page 50 --end-page 100
  python translate_pdf.py document.pdf --start-page 101  # Process from page 101 to end
Rate limit recommendations for 350-page document:
  --delay 15  : ~1.5 hours total (may hit rate limits)
  --delay 30  : ~3 hours total (balanced, recommended)
  --delay 45  : ~4.5 hours total (conservative)
  --delay 60  : ~6 hours total (very safe, best for token quota limits)
Note: Delays include 0-20% random jitter to appear more natural
Environment setup:
  export ANTHROPIC_API_KEY='your-api-key-here'
        """
    )
    parser.add_argument(
        'pdf_file',
        help='Path to the PDF file to translate'
    )
    parser.add_argument(
        '--output-dir',
        help='Directory to save translated text files (default: creates folder next to PDF)',
        default=None
    )
    parser.add_argument(
        '--delay',
        type=int,
        default=30,
        help='Seconds to wait between processing pages (default: 30, recommended for 350 pages)'
    )
    parser.add_argument(
        '--start-page',
        type=int,
        default=1,
        help='Page number to start from (default: 1)'
    )
    parser.add_argument(
        '--end-page',
        type=int,
        default=None,
        help='Page number to end at (default: last page)'
    )
    args = parser.parse_args()
    # Validate delay
    if args.delay < 0:
        print("Error: Delay must be a positive number")
        sys.exit(1)
    if args.delay < 10:
        print(f"Warning: A delay of {args.delay} seconds may be too short to avoid rate limits.")
        response = input("Continue anyway? (y/n): ")
        if response.lower() != 'y':
            print("Aborted.")
            sys.exit(0)
    # Validate page range
    if args.start_page < 1:
        print("Error: Start page must be 1 or greater")
        sys.exit(1)
    if args.end_page and args.end_page < args.start_page:
        print(f"Error: End page ({args.end_page}) cannot be less than start page ({args.start_page})")
        sys.exit(1)
    # Run the translation
    try:
        process_pdf(args.pdf_file, args.output_dir, args.delay, args.start_page, args.end_page)
    except KeyboardInterrupt:
        print("\n\nTranslation interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\nUnexpected error: {str(e)}")
        sys.exit(1)
if __name__ == "__main__":
    main()
