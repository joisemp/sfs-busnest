from storages.backends.s3boto3 import S3Boto3Storage
from django.conf import settings

class StaticStorage(S3Boto3Storage):
    location = f"{settings.AWS_STORAGE_BUCKET_NAME}/static"
    default_acl = "public-read"

class MediaStorage(S3Boto3Storage):
    location = f"{settings.AWS_STORAGE_BUCKET_NAME}/media"
    default_acl = "private"
