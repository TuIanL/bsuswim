from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import VideoFile
from app.schemas import VideoFileRead, VideoUploadResponse
from app.services.storage import StorageService, playback_url

router = APIRouter()


@router.post("", response_model=VideoUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_video(file: UploadFile = File(...), db: Session = Depends(get_db)) -> VideoUploadResponse:
    if not (file.content_type or "").startswith("video/"):
        raise HTTPException(status_code=400, detail="请上传视频文件")

    saved = await StorageService().save_upload(file)
    video = VideoFile(**saved)
    db.add(video)
    db.commit()
    db.refresh(video)
    return VideoUploadResponse(video=_read_video(video))


def _read_video(video: VideoFile) -> VideoFileRead:
    return VideoFileRead.model_validate(
        {
            **video.__dict__,
            "playback_url": playback_url(video.stored_filename),
        }
    )
