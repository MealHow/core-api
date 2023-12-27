from aiohttp import ClientSession as Session
from gcloud.aio.storage import Storage

from src.core.config import get_settings

settings = get_settings()


class CloudStorage:
    storage: Storage = None

    def initialise(self, session: Session) -> None:
        if settings.GCLOUD_SERVICE_ACCOUNT:
            self.storage = Storage(
                service_file=settings.GCLOUD_SERVICE_ACCOUNT,
                session=session,
            )

    def __call__(self) -> Storage:
        assert self.storage is not None
        return self.storage
