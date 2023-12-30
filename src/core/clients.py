from google import pubsub_v1
from google.cloud import ndb
from mealhow_sdk.clients import CloudStorage

from core.config import get_settings

settings = get_settings()

cloud_storage_session = CloudStorage()
pubsub_publisher = pubsub_v1.PublisherClient()
ndb_client = ndb.Client(project=settings.PROJECT_ID, database=settings.DATASTORE_DB)
