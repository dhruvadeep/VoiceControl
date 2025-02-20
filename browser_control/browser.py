from typing import Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from playwright.async_api import Browser, BrowserContext, Page, Playwright, async_playwright
from pydantic import BaseModel


class SearchQuery(BaseModel):
    query: str


APP = FastAPI()

APP.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


PLAYWRIGHT: Optional[Playwright] = None
BROWSER: Optional[Browser] = None
CONTEXT: Optional[BrowserContext] = None

SEARCH_URL = "https://www.bing.com/search?q="


@APP.on_event("startup")
async def startup() -> None:
    """
    On application startup:
      1. Launch async Playwright.
      2. Launch a Firefox browser (change to chromium or webkit if desired).
      3. Create a new browser context.
    """
    global PLAYWRIGHT, BROWSER, CONTEXT
    PLAYWRIGHT = await async_playwright().start()
    # NOTE: set `headless=False` to see the browser window, or True to run in the background
    BROWSER = await PLAYWRIGHT.firefox.launch(headless=False)
    CONTEXT = await BROWSER.new_context()


@APP.on_event("shutdown")
async def shutdown() -> None:
    """
    On application shutdown, close Playwright properly.
    """
    global PLAYWRIGHT
    if PLAYWRIGHT:
        await PLAYWRIGHT.stop()


@APP.post("/browser/new_window_and_search")
async def new_window_and_search(query: SearchQuery) -> dict:
    """
    Opens a new window and performs a search.
    """
    await open_new_window()
    return await search(query)


@APP.post("/browser/open_new_window")
async def open_new_window() -> dict:
    """
    Opens a new page (window) in the existing browser context,
    limited to 5 pages by default.
    """
    global CONTEXT
    if CONTEXT is None:
        return {"response": "Browser context is not initialized."}

    try:
        if len(CONTEXT.pages) >= 5:
            raise Exception("Cannot open more windows (limit reached).")
        await CONTEXT.new_page()
        return {"response": "Opened a new window."}
    except Exception as e:
        return {"response": str(e)}


@APP.post("/browser/search")
async def search(query: SearchQuery) -> dict:
    """
    Performs a search on the most recently opened page.
    If no pages are open, it will create a new one and perform the search.
    """
    global CONTEXT
    if CONTEXT is None:
        return {"response": "Browser context is not initialized."}

    if len(CONTEXT.pages) == 0:
        # If no pages exist, open a new window automatically
        await open_new_window()

    # Get the last page in the context
    page: Page = CONTEXT.pages[-1]
    await page.goto(SEARCH_URL + query.query)
    return {"response": f"Searching for {query.query}"}


@APP.post("/browser/close_current_window")
async def close_current_window() -> dict:
    """
    Closes the most recently opened window if any exist.
    """
    global CONTEXT
    if CONTEXT is None:
        return {"response": "Browser context is not initialized."}

    if len(CONTEXT.pages) == 0:
        return {"response": "No open windows to close."}

    await CONTEXT.pages[-1].close()
    return {"response": "Closed the current window."}


@APP.post("/browser/close_browser")
async def close_browser() -> dict:
    """
    Closes all open pages in the current context.
    (Does NOT close the entire Playwright instance;
     shutting down the entire app will do that.)
    """
    global CONTEXT
    if CONTEXT is None:
        return {"response": "Browser context is not initialized."}

    for page in CONTEXT.pages:
        await page.close()
    return {"response": "Closed all browser windows."}
