from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum
import requests
import re
import urllib.parse
import html
from typing import Optional

app = FastAPI(
    title="Instagram Downloader API",
    description="API to download Instagram reels and posts",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {
        "message": "Instagram Downloader API",
        "version": "1.0.0",
        "endpoints": {
            "download": "/api/download?url=<instagram_url>",
            "health": "/api/health",
            "docs": "/api/docs"
        }
    }

@app.get("/api/download")
async def download_instagram_content(url: str = Query(..., description="Instagram URL to download")):
    """
    Download Instagram reel/post content
    
    Args:
        url: Instagram URL (required)
        
    Returns:
        JSON response with video URL, thumbnail, and status
    """
    
    # Step 1: Validate Input
    if not url or url.strip() == "":
        raise HTTPException(status_code=400, detail="Missing Instagram URL")
    
    # Basic URL validation
    if not ("instagram.com" in url or "instagr.am" in url):
        raise HTTPException(status_code=400, detail="Invalid Instagram URL")
    
    try:
        # Step 2: Prepare request to snapdownloader
        encoded_url = urllib.parse.quote(url, safe='')
        target_url = f"https://snapdownloader.com/tools/instagram-reels-downloader/download?url={encoded_url}"
        
        # Step 3: Make request with proper headers
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
        
        response = requests.get(target_url, headers=headers, allow_redirects=True, timeout=25)
        response.raise_for_status()
        
        # Step 4: Extract video URL
        video_pattern = r'<a[^>]+href="([^"]+\.mp4[^"]*)"[^>]*>'
        video_match = re.search(video_pattern, response.text)
        video_url = html.unescape(video_match.group(1)) if video_match else ""
        
        # Step 5: Extract image thumbnail (try multiple methods)
        # Method 1: from base64 image
        thumb_base64_pattern = r'<img[^>]+src="data:image\/jpg;base64,([^"]+)"'
        thumb_base64_match = re.search(thumb_base64_pattern, response.text)
        thumb_base64 = thumb_base64_match.group(1) if thumb_base64_match else None
        
        # Method 2: from external jpg link
        thumb_pattern = r'<a[^>]+href="([^"]+\.jpg[^"]*)"[^>]*>'
        thumb_match = re.search(thumb_pattern, response.text)
        thumb_url = html.unescape(thumb_match.group(1)) if thumb_match else ""
        
        # Method 3: Try alternative thumbnail patterns
        if not thumb_url:
            alt_thumb_pattern = r'<img[^>]+src="([^"]+\.jpg[^"]*)"[^>]*>'
            alt_thumb_match = re.search(alt_thumb_pattern, response.text)
            thumb_url = html.unescape(alt_thumb_match.group(1)) if alt_thumb_match else ""
        
        # Step 6: Return clean JSON
        if video_url:
            return JSONResponse(
                content={
                    "status": "success",
                    "data": {
                        "video_url": video_url,
                        "thumbnail_url": thumb_url,
                        "thumbnail_base64": f"data:image/jpg;base64,{thumb_base64}" if thumb_base64 else None,
                        "original_url": url
                    },
                    "message": "Video extracted successfully"
                },
                status_code=200
            )
        else:
            return JSONResponse(
                content={
                    "status": "error",
                    "message": "Unable to extract video from the provided URL",
                    "data": None
                },
                status_code=404
            )
    
    except requests.exceptions.Timeout:
        raise HTTPException(status_code=408, detail="Request timeout - the external service took too long to respond")
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch data: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "message": "Instagram Downloader API is running",
        "timestamp": "2024-01-01T00:00:00Z"
    }

@app.post("/api/download")
async def download_instagram_content_post(request_data: dict):
    """
    Download Instagram content via POST request
    
    Args:
        request_data: JSON with 'url' field
        
    Returns:
        JSON response with video URL, thumbnail, and status
    """
    url = request_data.get('url')
    if not url:
        raise HTTPException(status_code=400, detail="Missing 'url' field in request body")
    
    # Reuse the same logic as GET endpoint
    return await download_instagram_content(url)

# This is the handler that Vercel will use
handler = Mangum(app)
