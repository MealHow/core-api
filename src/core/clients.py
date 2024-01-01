from google.cloud import ndb, pubsub_v1
from mealhow_sdk.clients import CloudStorage

from core.config import get_settings

settings = get_settings()

cloud_storage_session = CloudStorage()
pubsub_publisher = pubsub_v1.PublisherClient()
ndb_client = ndb.Client(project=settings.PROJECT_ID)
