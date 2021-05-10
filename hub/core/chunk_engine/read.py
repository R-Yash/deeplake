import os
import pickle
import numpy as np

from hub.core.storage import MemoryProvider

from .generator import unchunk
from .dummy_util import dummy_compression_map
from .meta import get_meta
from .index_map import get_index_map

from typing import Callable, List

# TODO change storage type to StorageProvider
# TODO: read with slice
def read_sample(
    key: str,
    index: int,
    storage,
) -> np.ndarray:
    """
    array <- bytes <- decompressor <- chunks <- storage
    """

    meta = get_meta(key, storage)

    # TODO: don't get entire index_map, instead read entries
    index_map = get_index_map(key, storage)

    compression = dummy_compression_map[meta["compression"]]
    dtype = meta["dtype"]
    length = meta["length"]

    samples = []
    all_same_shape = True
    last_shape = None

    for index in range(length):
        index_entry = index_map[index]

        # TODO: decode from array instead of dictionary
        chunk_names = index_entry["chunk_names"]
        incomplete_chunk_names = index_entry["incomplete_chunk_names"]
        shape = index_entry["shape"]
        start_byte, end_byte = index_entry["start_byte"], index_entry["end_byte"]

        # TODO: make this more concise
        if last_shape is not None and last_shape != shape:
            all_same_shape = False

        """
        b = bytearray()
        actual_start_byte = start_byte
        for chunk_local_index, chunk_name in enumerate(chunk_names):
            chunk_key = os.path.join(key, chunk_name)

            raw_chunk = storage[chunk_key]

            if compression.subject == "chunk":
                if chunk_name in incomplete_chunk_names:
                    chunk = raw_chunk
                else:
                    # TODO: different `meta["version"]`s may have different compressor maps
                    chunk = compression.decompress(raw_chunk)
            else:
                chunk = raw_chunk

            actual_end_byte = -1
            if chunk_local_index >= len(chunk_names) - 1:
                # last chunk will actually use `end_byte`
                actual_end_byte = end_byte

            b.extend(chunk[actual_start_byte:actual_end_byte])
            print(b)
            print(chunk_local_index, actual_start_byte, actual_end_byte)
            # `start_byte` should only be used for the first chunk
            actual_start_byte = 0
            """

        # TODO: put this in a separate function/class, ideally that caches decompressed chunks
        def decompressed_chunks_generator():
            for chunk_name in chunk_names:
                chunk_key = os.path.join(key, chunk_name)
                raw_chunk = storage[chunk_key]

                if compression.subject == "chunk":
                    if chunk_name in incomplete_chunk_names:
                        chunk = raw_chunk
                    else:
                        # TODO: different `meta["version"]`s may have different compressor maps
                        chunk = compression.decompress(raw_chunk)
                else:
                    chunk = raw_chunk

                yield chunk

        b = unchunk(list(decompressed_chunks_generator()), start_byte, end_byte)

        a = np.frombuffer(b, dtype=dtype)
        last_shape = shape
        samples.append(a.reshape(shape))

    if all_same_shape:
        return np.array(samples, dtype=dtype)

    return samples
