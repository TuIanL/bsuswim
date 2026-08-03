import asyncio
import os
import shutil
from pathlib import Path

from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from playwright.async_api import async_playwright

from app.core.config import get_settings


class PdfRenderError(Exception):
    """Raised when the print page is not rendered successfully, so export must abort."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


class PdfRenderTimeoutError(PdfRenderError):
    def __init__(self, message: str = "PDF rendering timed out"):
        super().__init__("PDF_RENDER_TIMEOUT", message)


def _browser_executable_path() -> str | None:
    configured = get_settings().pdf_browser_executable_path or os.getenv(
        "PDF_BROWSER_EXECUTABLE_PATH"
    )
    candidates = [configured] if configured else []
    candidates.extend(
        [
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "/Applications/Chromium.app/Contents/MacOS/Chromium",
            "/usr/bin/google-chrome",
            "/usr/bin/chromium",
            "/usr/bin/chromium-browser",
        ]
    )
    candidates.extend(
        executable
        for executable in (shutil.which("google-chrome"), shutil.which("chromium"))
        if executable
    )
    return next(
        (path for path in candidates if path and Path(path).is_file()),
        None,
    )


async def _assert_on_print_route(page, expected_url: str) -> None:
    """Abort if the page was redirected away from the print route (e.g. to /login)."""
    actual_path = page.url.split("?")[0].split("#")[0]
    expected_path = expected_url.split("?")[0].split("#")[0]
    if actual_path != expected_path:
        raise PdfRenderError(
            "PRINT_ROUTE_REDIRECTED",
            f"打印页被重定向（期望 {expected_path}，实际 {actual_path}），导出中止",
        )


async def render_pdf_from_url(url: str, timeout: int = 35000) -> bytes:
    async with async_playwright() as p:
        launch_options = {
            "headless": True,
            "args": ["--no-sandbox", "--disable-setuid-sandbox"],
        }
        executable_path = _browser_executable_path()
        if executable_path:
            launch_options["executable_path"] = executable_path

        browser = await p.chromium.launch(**launch_options)
        try:
            page = await browser.new_page(
                viewport={"width": 1440, "height": 1020},
                device_scale_factor=1,
            )

            await page.goto(url, wait_until="networkidle", timeout=timeout)
            await _assert_on_print_route(page, url)

            try:
                await page.wait_for_function(
                    "() => window.__REPORT_PRINT_READY__ === true",
                    timeout=timeout,
                )
            except (asyncio.TimeoutError, PlaywrightTimeoutError):
                page_error = await page.evaluate(
                    "() => window.__REPORT_PRINT_ERROR__ || null"
                )
                if page_error and page_error.get("code"):
                    raise PdfRenderError(
                        page_error.get("code", "PRINT_PAGE_ERROR"),
                        page_error.get("message", "打印页报告错误，导出中止"),
                    )
                raise PdfRenderError(
                    "PRINT_READY_TIMEOUT",
                    "打印页在限定时间内未就绪，导出中止",
                )

            pdf_bytes = await page.pdf(
                format="A4",
                landscape=True,
                print_background=True,
                margin={"top": "0mm", "right": "0mm", "bottom": "0mm", "left": "0mm"},
            )

            return pdf_bytes
        except (asyncio.TimeoutError, PlaywrightTimeoutError):
            raise PdfRenderTimeoutError("PDF rendering timed out")
        finally:
            await browser.close()
