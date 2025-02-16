from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from playwright.async_api import Browser, BrowserContext, Page, async_playwright
from pydantic import BaseModel


class SearchQuery(BaseModel):
    query: str


APP = FastAPI()

APP.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "*"
    ],  # For production, specify your allowed domain(s) instead of "*"
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

PLAYWRIGHT = None
BROWSER: Browser = None
CONTEXT: BrowserContext = None

SEARCH_URL = "https://www.bing.com/search?q="


@APP.on_event("startup")
async def startup():
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
async def shutdown():
    """
    On application shutdown, close Playwright properly.
    """
    global PLAYWRIGHT
    if PLAYWRIGHT:
        await PLAYWRIGHT.stop()


@APP.post("/browser/new_window_and_search")
async def new_window_and_search(query: SearchQuery):
    await open_new_window()
    return await search(query)


@APP.post("/browser/open_new_window")
async def open_new_window():
    """
    Opens a new page (window) in the existing browser context,
    limited to 5 pages by default.
    """
    global CONTEXT
    try:
        if len(CONTEXT.pages) >= 5:
            raise Exception("Cannot open more windows (limit reached).")
        await CONTEXT.new_page()
        return {"response": "Opened a new window."}
    except Exception as e:
        return {"response": str(e)}


@APP.post("/browser/search")
async def search(query: SearchQuery):
    """
    Performs a search on the most recently opened page.
    If no pages are open, it will create a new one and perform the search.
    """
    global CONTEXT
    if len(CONTEXT.pages) == 0:
        # If no pages exist, open a new window automatically
        await open_new_window()

    # Get the last page in the context
    page: Page = CONTEXT.pages[-1]
    await page.goto(SEARCH_URL + query.query)
    return {"response": f"Searching for {query.query}"}


@APP.post("/browser/close_current_window")
async def close_current_window():
    """
    Closes the most recently opened window if any exist.
    """
    global CONTEXT
    if len(CONTEXT.pages) == 0:
        return {"response": "No open windows to close."}

    await CONTEXT.pages[-1].close()
    return {"response": "Closed the current window."}


@APP.post("/browser/close_browser")
async def close_browser():
    """
    Closes all open pages in the current context.
    (Does NOT close the entire Playwright instance,
    but you can shut down the entire app to do that.)
    """
    global CONTEXT
    for page in CONTEXT.pages:
        await page.close()
    return {"response": "Closed all browser windows."}


# Run with: uvicorn this_file_name:APP --host 0.0.0.0 --port 8000 --reload
