import asyncio
import signal
from playwright.async_api import async_playwright, TimeoutError
from rich import print as rich_print
from src.selector_factory import SelectorFactory


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()

        try:
            # Navigate to the website with increased timeout
            print("Attempting to navigate to the website...")
            await page.goto("https://app.bacprep.ro")  # 30 second timeout
            print("Successfully loaded the website!")

            html_content = await page.content()
            rich_print("HTML Content:\n")
            rich_print(html_content)

            full_xpath: str = "/html/body/div[1]/div/div[1]/div/div[2]/div[2]/form/button"

            selector_factory = SelectorFactory(html_content=html_content)

            relative_xpath_selector: str = selector_factory.generate_relative_xpath_from_full_xpath(
                full_xpath=full_xpath
            )

            # rich_print("\nRelative XPath Selector:\n")
            # rich_print(relative_xpath_selector)

        except TimeoutError:
            print(
                "\nError: The website took too long to load. Please check if the URL is correct and your internet connection is working."
            )
        except KeyboardInterrupt:
            print("\nReceived Control+C. Closing browser...")
        except Exception as e:
            print(f"\nAn error occurred: {e}")
            print("This might be due to:")
            print("1. The website URL is incorrect")
            print("2. Your internet connection is not working")
            print("3. The website is down")
            # Print HTML content if the page is still available

        await browser.close()


def signal_handler(signum, frame):
    raise KeyboardInterrupt()


if __name__ == "__main__":
    # Set up signal handler for Control+C
    signal.signal(signal.SIGINT, signal_handler)

    # Run the async main function
    asyncio.run(main())
