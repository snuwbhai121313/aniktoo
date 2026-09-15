from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import RedirectResponse
from anicli_api.source.anikoto import Extractor  # Imports the Anikoto source
from anicli_api.player.megaplay import MegaPlay  # Imports the player for Anikoto's servers

app = FastAPI(title="Anikoto Stream API")

@app.get("/")
def read_root():
    return {"message": "Anikoto Stream API is running. Use /stream?q=<title>&ep=<number>"}

@app.get("/stream")
async def get_stream(q: str = Query(..., description="Anime title"), ep: int = Query(1, description="Episode number")):
    """
    Resolves a direct stream URL for a given anime title and episode.
    """
    try:
        # 1. Search for the anime using the Anikoto Extractor
        extractor = Extractor()
        search_results = await extractor.a_search(q)
        
        if not search_results:
            raise HTTPException(status_code=404, detail=f"Anime '{q}' not found.")

        # 2. Get the anime object and its episodes
        anime = await search_results[0].a_get_anime()
        episodes = await anime.a_get_episodes()

        if not episodes or ep > len(episodes):
            raise HTTPException(status_code=404, detail=f"Episode {ep} not found.")

        # 3. Get the selected episode
        episode = episodes[ep - 1] # Adjust for 0-indexing

        # 4. Get the available sources (servers)
        sources = await episode.a_get_sources()

        if not sources:
            raise HTTPException(status_code=404, detail="No sources found for this episode.")

        # 5. Use the first source and extract the direct video link
        # Anikoto typically uses MegaPlay as its player
        source = sources[0] 
        player = MegaPlay() 
        
        # The 'get_videos' method returns a list of Video objects
        videos = await player.a_get_videos(source) 
        
        if not videos:
            raise HTTPException(status_code=404, detail="Could not extract video link.")

        # Return the highest quality video URL
        # Sort by quality if needed, or just take the first
        stream_url = videos[0].url

        return {
            "success": True,
            "title": anime.title,
            "episode": ep,
            "stream_url": stream_url,
            "headers": videos[0].headers # Important for some players
        }

    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")

@app.get("/redirect")
async def redirect_stream(q: str = Query(...), ep: int = Query(1)):
    """
    A convenience endpoint that redirects the browser directly to the stream.
    """
    result = await get_stream(q, ep)
    if "stream_url" in result:
        return RedirectResponse(url=result["stream_url"])
    raise HTTPException(status_code=404, detail="Stream not found")
