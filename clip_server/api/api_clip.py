from fastapi import Request, HTTPException, APIRouter, Response, Query
router = APIRouter()



@router.get("/list-phrase")
def get_rate(request: Request,
             limit: int = 20,
             offset: int = 0):
    clip_server = request.app.clip_server

    phrase_list = clip_server.get_phrase_list(offset, limit)

    return phrase_list