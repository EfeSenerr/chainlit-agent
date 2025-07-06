from fastapi import FastAPI, Query
from pydantic import BaseModel
from duckduckgo_search import DDGS

app = FastAPI()

class SearchResult(BaseModel):
    title: str
    snippet: str
    url: str

@app.get("/search", response_model=list[SearchResult])
def search(query: str = Query(..., description="The web search query")):
    results = []
    with DDGS() as ddgs:
        for r in ddgs.text(query, region="wt-wt", safesearch="off"):
            results.append(SearchResult(
                title=r.get("title", ""),
                snippet=r.get("body", ""),
                url=r.get("href", "")
            ))
            if len(results) >= 5:
                break
    return results