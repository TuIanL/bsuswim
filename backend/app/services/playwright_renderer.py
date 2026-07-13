import asyncio

from playwright.async_api import async_playwright


class PdfRenderTimeoutError(Exception):
    pass


async def render_pdf_from_url(url: str, timeout: int = 35000) -> bytes:
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox"],
        )
        try:
            page = await browser.new_page(
                viewport={"width": 1440, "height": 1020},
                device_scale_factor=1,
            )

            await page.goto(url, wait_until="networkidle", timeout=timeout)

            try:
                await page.wait_for_function(
                    "() => window.__REPORT_PRINT_READY__ === true",
                    timeout=timeout,
                )
            except asyncio.TimeoutError:
                pass

            pdf_bytes = await page.pdf(
                format="A4",
                landscape=True,
                print_background=True,
                margin={"top": "0mm", "right": "0mm", "bottom": "0mm", "left": "0mm"},
            )

            return pdf_bytes
        except asyncio.TimeoutError:
            raise PdfRenderTimeoutError("PDF rendering timed out")
        finally:
            await browser.close()
