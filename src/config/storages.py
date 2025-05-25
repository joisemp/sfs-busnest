from storages.backends.s3boto3 import S3Boto3Storage
from django.conf import settings

class StaticStorage(S3Boto3Storage):
    """
    StaticStorage is a custom storage class that inherits from S3Boto3Storage.
    It is used to manage static files in an S3 bucket.

    Attributes:
        location (str): The folder name in the S3 bucket where static files are stored.
        default_acl (str): The default access control list for the files, set to "public-read".
    """
    location = "static"
    default_acl = "public-read"

class MediaStorage(S3Boto3Storage):
    """
    MediaStorage is a custom storage class that extends S3Boto3Storage to handle
    media file storage in an S3 bucket.

    Attributes:
        location (str): The directory within the S3 bucket where media files will
            be stored. Defaults to "media".
        default_acl (str): The default access control list for stored files.
            Defaults to "private", ensuring that files are not publicly accessible
            by default.
    """
    location = "media"
    default_acl = "private"
