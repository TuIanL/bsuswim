from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.config import get_settings
from app.models import VideoFile
from app.schemas import VideoFileRead, VideoUploadResponse
from app.services.media_probe import probe_video_metadata
from app.services.storage import StorageService, UploadTooLargeError, playback_url

router = APIRouter()


@router.post("/upload", response_model=VideoUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_video(file: UploadFile = File(...), db: Session = Depends(get_db)) -> VideoUploadResponse:
    if not (file.content_type or "").startswith("video/"):
        raise HTTPException(status_code=400, detail="请上传视频文件")

    try:
        saved = await StorageService().save_upload(
            file,
            max_bytes=get_settings().video_upload_max_bytes,
        )
    except UploadTooLargeError as exc:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail={
                "code": "UPLOAD_TOO_LARGE",
                "message": "视频文件超过开发环境上传大小限制",
                "max_bytes": exc.max_bytes,
            },
        ) from exc
    video = VideoFile(**saved)
    db.add(video)
    db.commit()
    db.refresh(video)

    probe = probe_video_metadata(video.storage_path)
    return VideoUploadResponse(
        video=_read_video(video),
        probed_fps=probe["fps"],
        resolution=probe["resolution"],
        metadata_source="ffprobe" if probe["verified"] else None,
        fps_verified=probe["verified"],
    )


@router.get("/{video_id}", response_model=VideoFileRead)
def get_video(video_id: int, db: Session = Depends(get_db)) -> VideoFileRead:
    video = db.get(VideoFile, video_id)
    if not video:
        raise HTTPException(status_code=404, detail="视频不存在")
    return _read_video(video)


def _read_video(video: VideoFile) -> VideoFileRead:
    return VideoFileRead.model_validate(
        {
            **video.__dict__,
            "playback_url": playback_url(video.stored_filename),
        }
    )
