from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import RedirectResponse
from anicli_api.source.yummy_anime import Extractor

app = FastAPI(title="Anime Stream API")


@app.get("/")
def read_root():
    return {
        "message": "Anime Stream API is running",
        "usage": "/stream?q=<title>&ep=<number>",
        "example": "/stream?q=naruto&ep=1"
    }


@app.get("/stream")
async def get_stream(
    q: str = Query(..., description="Anime title"),
    ep: int = Query(1, description="Episode number")
):
    """
    Resolves a direct stream URL for a given anime title and episode.
    """
    try:
        # 1. Search for the anime
        extractor = Extractor()
        search_results = await extractor.a_search(q)

        if not search_results:
            raise HTTPException(status_code=404, detail=f"Anime '{q}' not found.")

        # 2. Get the anime object and its episodes
        anime = await search_results[0].a_get_anime()
        episodes = await anime.a_get_episodes()

        if not episodes or ep > len(episodes):
            raise HTTPException(
                status_code=404,
                detail=f"Episode {ep} not found. Available episodes: {len(episodes)}"
            )

        # 3. Get the selected episode (adjust for 0-indexing)
        episode = episodes[ep - 1]

        # 4. Get the available sources (servers)
        sources = await episode.a_get_sources()

        if not sources:
            raise HTTPException(status_code=404, detail="No sources found for this episode.")

        # 5. Use the first source and extract the direct video link
        source = sources[0]
        videos = await source.a_get_videos()

        if not videos:
            raise HTTPException(status_code=404, detail="Could not extract video link.")

        # Return the highest quality video URL
        stream_url = videos[0].url

        # Build response with headers if available
        response = {
            "success": True,
            "title": anime.title,
            "episode": ep,
            "stream_url": stream_url
        }

        # Include headers if the video object has them
        if hasattr(videos[0], "headers") and videos[0].headers:
            response["headers"] = videos[0].headers

        return response

    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")


@app.get("/redirect")
async def redirect_stream(
    q: str = Query(..., description="Anime title"),
    ep: int = Query(1, description="Episode number")
):
    """
    Convenience endpoint that redirects the browser directly to the stream.
    """
    result = await get_stream(q, ep)
    if "stream_url" in result:
        return RedirectResponse(url=result["stream_url"])
    raise HTTPException(status_code=404, detail="Stream not found")
