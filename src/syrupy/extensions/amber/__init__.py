from functools import lru_cache
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Any,
    Optional,
    Set,
)

from syrupy.data import SnapshotCollection
from syrupy.extensions.base import AbstractSyrupyExtension

from .serializer import DataSerializer

if TYPE_CHECKING:
    from syrupy.types import SerializableData


class AmberSnapshotExtension(AbstractSyrupyExtension):
    """
    An amber snapshot file stores data in the following format:
    """

    _file_extension = "ambr"

    def serialize(self, data: "SerializableData", **kwargs: Any) -> str:
        """
        Returns the serialized form of 'data' to be compared
        with the snapshot data written to disk.
        """
        return DataSerializer.serialize(data, **kwargs)

    def delete_snapshots(
        self, snapshot_location: str, snapshot_names: Set[str]
    ) -> None:
        snapshot_collection_to_update = DataSerializer.read_file(snapshot_location)
        for snapshot_name in snapshot_names:
            snapshot_collection_to_update.remove(snapshot_name)

        if snapshot_collection_to_update.has_snapshots:
            DataSerializer.write_file(snapshot_collection_to_update)
        else:
            Path(snapshot_location).unlink()

    def _read_snapshot_collection(self, snapshot_location: str) -> "SnapshotCollection":
        return DataSerializer.read_file(snapshot_location)

    @staticmethod
    @lru_cache()
    def __cacheable_read_snapshot(
        snapshot_location: str, cache_key: str
    ) -> "SnapshotCollection":
        return DataSerializer.read_file(snapshot_location)

    def _read_snapshot_data_from_location(
        self, snapshot_location: str, snapshot_name: str, session_id: str
    ) -> Optional["SerializableData"]:
        snapshots = self.__cacheable_read_snapshot(
            snapshot_location=snapshot_location, cache_key=session_id
        )
        snapshot = snapshots.get(snapshot_name)
        return snapshot.data if snapshot else None

    @classmethod
    def _write_snapshot_collection(
        cls, *, snapshot_collection: "SnapshotCollection"
    ) -> None:
        DataSerializer.write_file(snapshot_collection, merge=True)


__all__ = ["AmberSnapshotExtension", "DataSerializer"]
