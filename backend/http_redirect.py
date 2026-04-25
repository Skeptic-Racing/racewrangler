from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse

app = FastAPI(title="RaceWrangler HTTP Redirect", version="0.1.0")


@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"])
async def redirect_to_https(request: Request, path: str):
    host = request.headers.get("host", "racewrangler.local").split(":", 1)[0]
    url = f"https://{host}/{path}" if path else f"https://{host}/"
    if request.url.query:
        url = f"{url}?{request.url.query}"
    return RedirectResponse(url=url, status_code=308)
