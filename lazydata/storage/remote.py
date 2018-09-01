"""
Remote storage backend implementation

"""

import lazy_import
from boto3.s3.transfer import S3Transfer
from pathlib import PurePosixPath

import os, threading, sys

from botocore.exceptions import ClientError

from lazydata.config.config import Config
from lazydata.storage.local import LocalStorage

boto3 = lazy_import.lazy_module("boto3")
botocore = lazy_import.lazy_module("botocore")
from urllib.parse import urlparse

import logging
logging.getLogger('boto3').setLevel(logging.CRITICAL)
logging.getLogger('botocore').setLevel(logging.CRITICAL)

class RemoteStorage:
    """
    A storage backend abstraction layer
    """

    @staticmethod
    def get_from_url(remote_url:str):
        if remote_url.startswith("s3://"):
            return AWSRemoteStorage(remote_url)
        else:
            raise RuntimeError("Url `%s` is not supported as a remote storage backend" % remote_url)

    @staticmethod
    def get_from_config(config:Config):
        if "remote" in config.config:
            return RemoteStorage.get_from_url(config.config["remote"])
        else:
            raise RuntimeError("Remote storage backend not configured for this lazydata project.")


    def check_storage_exists(self):
        """
        Check if the storage backend location exists and is valid

        :return:
        """
        raise NotImplementedError("Not implemented for this storage backend.")

    def upload(self, local:LocalStorage, config:Config):
        """
        Upload the local storage cache for a config file

        :param local:
        :param config:
        :return:
        """
        raise NotImplementedError("Not implemented for this storage backend.")


class AWSRemoteStorage(RemoteStorage):

    def __init__(self, remote_url):
        if not remote_url.startswith("s3://"):
            raise RuntimeError("AWSRemoteStorage URL needs to start with s3://")

        # parse the URL
        self.url = remote_url
        p = urlparse(self.url)
        self.bucket_name = p.netloc
        self.path_prefix = p.path.strip()
        if self.path_prefix.startswith("/"):
            self.path_prefix = self.path_prefix[1:]
        # get the reusable clients and resources
        self.s3 = boto3.resource('s3')
        self.client = boto3.client('s3')

    def check_storage_exists(self):
        exists = True
        try:
            self.s3.meta.client.head_bucket(Bucket=self.bucket_name)
        except botocore.exceptions.ClientError as e:
            # If a client error is thrown, then check that it was a 404 error.
            # If it was a 404 error, then the bucket does not exist.
            error_code = int(e.response['Error']['Code'])
            if error_code == 404:
                exists = False

        return exists

    def upload(self, local: LocalStorage, config: Config):
        transfer = S3Transfer(self.client)

        # look for all hashes in the config file and upload
        all_sha256 = [e["hash"] for e in config.config["files"]]

        for sha256 in all_sha256:
            local_path = local.hash_to_file(sha256)
            remote_path = local.hash_to_remote_path(sha256)
            s3_key = str(PurePosixPath(self.path_prefix, remote_path))

            # check if the remote location already exists
            exists = True
            try:
                self.client.head_object(Bucket=self.bucket_name, Key=s3_key)
            except botocore.exceptions.ClientError as e:
                error_code = int(e.response['Error']['Code'])
                if error_code == 404:
                    exists = False

            if not exists:
                transfer.upload_file(str(local_path),
                                     self.bucket_name,
                                     s3_key,
                                     callback=S3ProgressPercentage(str(local_path)))


class S3ProgressPercentage:
    def __init__(self, filename):
        self._filename = filename
        self._size = float(os.path.getsize(filename))
        self._seen_so_far = 0
        self._lock = threading.Lock()

    def __call__(self, bytes_amount):
        with self._lock:
            self._seen_so_far += bytes_amount
            percentage = (self._seen_so_far / self._size) * 100
            sys.stdout.write(
                "\r Uploading %s  %s / %s  (%.2f%%)" % (
                    self._filename, self._seen_so_far, self._size,
                    percentage))
            sys.stdout.flush()