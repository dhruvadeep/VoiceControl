from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from playwright.async_api import Browser, BrowserContext, Page, Playwright, async_playwright
from models import SearchQuery
import httpx
import toml
class BrowserWindowLimitReachedError(Exception):
    """Exception raised when the browser window limit is reached."""


APP = FastAPI()

APP.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


PLAYWRIGHT: Playwright | None = None
BROWSER: Browser | None = None
CONTEXT: BrowserContext | None = None

SEARCH_URL = "https://www.bing.com/search?q="
MAX_WINDOWS = 5

def logger_info(message:str):
    "Log message in a server."
    url = toml.load("log_config.toml")["url"]+"/log"
    httpx.request(method="POST", url=url, json={"message":message})

@APP.on_event("startup")
async def startup() -> None:
    """On application startup.

    1. Launch async Playwright.
    2. Launch a Firefox browser (change to chromium or webkit if desired).
    3. Create a new browser context.
    """
    global PLAYWRIGHT, BROWSER, CONTEXT
    logger_info("starting browser")
    PLAYWRIGHT = await async_playwright().start()
    # NOTE: set `headless=False` to see the browser window, or True to run in the background
    BROWSER = await PLAYWRIGHT.firefox.launch(headless=False)
    CONTEXT = await BROWSER.new_context()


@APP.on_event("shutdown")
async def shutdown() -> None:
    """On application shutdown, close Playwright properly."""
    if PLAYWRIGHT:
        logger_info("shutting down playwright")
        await PLAYWRIGHT.stop()


@APP.post("/browser/new_window_and_search")
async def new_window_and_search(query: SearchQuery) -> dict:
    """Open a new window and perform a search."""
    await open_new_window()
    return await search(query)


@APP.post("/browser/open_new_window")
async def open_new_window() -> dict:
    """Open a new window in the existing browser context.

    Limited to 5 pages by default.
    """
    logger_info("opening new window")
    if CONTEXT is None:
        return {"response": "Browser context is not initialized."}

    try:
        if len(CONTEXT.pages) >= MAX_WINDOWS:

            def raise_window_limit_error() -> None:
                """Error to indicate that the maximum number of browser windows has been reached.

                Raises:
                    BrowserWindowLimitReachedError: Exception indicating the browser window limit has been reached.

                """
                raise BrowserWindowLimitReachedError

            raise_window_limit_error()
        else:
            await CONTEXT.new_page()
            return {"response": "Opened a new window."}
    except BrowserWindowLimitReachedError as e:
        return {"response": str(e)}


@APP.post("/browser/search")
async def search(query: SearchQuery) -> dict:
    """Perform a search on the most recently opened page.

    Args:
        query (SearchQuery): The search query to be performed.

    Returns:
        dict: A dictionary containing the response message.

    """
    logger_info("searching for query: "+query.query)
    if CONTEXT is None:
        return {"response": "Browser context is not initialized."}

    if len(CONTEXT.pages) == 0:
        # If no pages exist, open a new window automatically
        await open_new_window()

    # Get the last page in the context
    page: Page = CONTEXT.pages[-1]
    await page.goto(SEARCH_URL + query.query)
    results = await page.locator("h2 a").all_text_contents()
    return {"response": f"Searching for {query.query}. Top results are : {results[:5]}"}


@APP.post("/browser/close_current_window")
async def close_current_window() -> dict:
    """Close the most recently opened window if any exist."""
    logger_info("closing current window")
    if CONTEXT is None:
        return {"response": "Browser context is not initialized."}

    if len(CONTEXT.pages) == 0:
        return {"response": "No open windows to close."}

    await CONTEXT.pages[-1].close()
    return {"response": "Closed the current window."}


@APP.post("/browser/close_browser")
async def close_browser() -> dict:
    """Close all open pages in the current context.

    (Does NOT close the entire Playwright instance;
     shutting down the entire app will do that.).
    """
    if CONTEXT is None:
        logger_info("the browser is not even initialized")
        return {"response": "Browser context is not initialized."}

    for page in CONTEXT.pages:
        await page.close()
    logger_info("closing browser")
    return {"response": "Closed all browser windows."}
