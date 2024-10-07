from functools import lru_cache
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Any,
    Optional,
    Set,
    Type,
)

from syrupy.data import SnapshotCollection
from syrupy.exceptions import TaintedSnapshotError
from syrupy.extensions.base import AbstractSyrupyExtension

from .serializer import AmberDataSerializerSorted  # noqa: F401 # re-exported
from .serializer import AmberDataSerializer

if TYPE_CHECKING:
    from syrupy.types import SerializableData


class AmberSnapshotExtension(AbstractSyrupyExtension):
    """
    An amber snapshot file stores data in the following format:
    """

    _file_extension = "ambr"

    serializer_class: Type["AmberDataSerializer"] = AmberDataSerializer

    def serialize(self, data: "SerializableData", **kwargs: Any) -> str:
        """
        Returns the serialized form of 'data' to be compared
        with the snapshot data written to disk.
        """
        return self.serializer_class.serialize(data, **kwargs)

    def delete_snapshots(
        self, snapshot_location: str, snapshot_names: Set[str]
    ) -> None:
        snapshot_collection_to_update = AmberDataSerializer.read_file(snapshot_location)
        for snapshot_name in snapshot_names:
            snapshot_collection_to_update.remove(snapshot_name)

        if snapshot_collection_to_update.has_snapshots:
            self.serializer_class.write_file(snapshot_collection_to_update)
        else:
            Path(snapshot_location).unlink()

    def _read_snapshot_collection(
        self, snapshot_location: str, **kwargs: Any
    ) -> "SnapshotCollection":
        return self.serializer_class.read_file(snapshot_location)

    @classmethod
    @lru_cache()
    def __cacheable_read_snapshot(
        cls, snapshot_location: str, cache_key: str
    ) -> "SnapshotCollection":
        return cls.serializer_class.read_file(snapshot_location)

    def _read_snapshot_data_from_location(
        self, snapshot_location: str, snapshot_name: str, session_id: str
    ) -> Optional["SerializableData"]:
        snapshots = self.__cacheable_read_snapshot(
            snapshot_location=snapshot_location, cache_key=session_id
        )
        snapshot = snapshots.get(snapshot_name)
        tainted = bool(snapshots.tainted or (snapshot and snapshot.tainted))
        data = snapshot.data if snapshot else None
        if tainted:
            raise TaintedSnapshotError(snapshot_data=data)
        return data

    @classmethod
    def _write_snapshot_collection(
        cls, *, snapshot_collection: "SnapshotCollection", **kwargs: Any
    ) -> None:
        cls.serializer_class.write_file(snapshot_collection, merge=True)


__all__ = ["AmberSnapshotExtension", "AmberDataSerializer"]
