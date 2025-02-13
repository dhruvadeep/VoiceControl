from playwright.sync_api import sync_playwright
from time import sleep
from models import SearchQuery
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

APP = FastAPI()
APP.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Change to specific domains in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


playwright = sync_playwright().start()
browser = playwright.firefox.launch(headless=False)
context = browser.new_context()
SEARCH_URL = "https://www.bing.com/search?q="

@APP.post("/browser/new_window_and_search")
def new_window_and_search(query: SearchQuery):
    context.new_page()
    return search(query)

@APP.post("/browser/search")
def search(query: SearchQuery):
    if len(context.pages) == 0:
        return new_window_and_search()
    else:
        query = query.query
        context.pages[-1].goto(SEARCH_URL+query)
        return {"response": f"searching for {query.query}"}
    
@APP.post("/browser/close_current_window")
def close_current_window():
    if len(context.pages) == 0:
        return 
    context.pages[-1].close()
    context.pages.pop()
    return {"response": "closed current window"}

@APP.post("/browser/close_browser")
def close_browser():
    for page in context.pages:
        page.close()
    return {"response": "closed the browser"}


if __name__ == "__main__":
    uvicorn.run("__main__:APP", host="localhost", port=8001, reload=True)