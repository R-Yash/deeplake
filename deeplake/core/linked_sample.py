from typing import Optional
from deeplake.constants import ALL_CLOUD_PREFIXES
from deeplake.util.path import get_path_type
import deeplake
import numpy as np


def convert_creds_key(creds_key: Optional[str], path: str):
    if creds_key is None and path.startswith(ALL_CLOUD_PREFIXES):
        creds_key = "ENV"
    elif creds_key == "ENV" and not path.startswith(ALL_CLOUD_PREFIXES):
        creds_key = None
    return creds_key


class LinkedSample:
    """Represents a sample that is initialized using external links. See :meth:`deeplake.link`."""

    def __init__(self, path: str, creds_key: Optional[str] = None):
        self.path = path
        self.creds_key = convert_creds_key(creds_key, path)

    @property
    def dtype(self) -> str:
        return np.array("").dtype.str


def read_linked_sample(
    sample_path: str, sample_creds_key: str, link_creds, verify: bool
):
    provider_type = get_path_type(sample_path)
    if provider_type == "local":
        return deeplake.read(sample_path, verify=verify)
    elif provider_type == "http":
        return _read_http_linked_sample(
            link_creds, sample_creds_key, sample_path, verify
        )
    else:
        return _read_cloud_linked_sample(
            link_creds, sample_creds_key, sample_path, provider_type, verify
        )


def retry_refresh_managed_creds(f):
    def wrapper(linked_creds, sample_creds_key, *args, **kwargs):
        try:
            return f(linked_creds, sample_creds_key, *args, **kwargs)
        except Exception as e:
            linked_creds.populate_all_managed_creds()
            return f(linked_creds, sample_creds_key, *args, **kwargs)

    return wrapper


@retry_refresh_managed_creds
def _read_cloud_linked_sample(
    link_creds,
    sample_creds_key: str,
    sample_path: str,
    provider_type: str,
    verify: bool,
):
    storage = link_creds.get_storage_provider(sample_creds_key, provider_type)
    return deeplake.read(sample_path, storage=storage, verify=verify)


@retry_refresh_managed_creds
def _read_http_linked_sample(
    link_creds, sample_creds_key: str, sample_path: str, verify: bool
):
    creds = link_creds.get_creds(sample_creds_key)
    return deeplake.read(sample_path, verify=verify, creds=creds)
