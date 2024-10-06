import collections
import inspect
import os
from collections import OrderedDict
from types import (
    FunctionType,
    GeneratorType,
    MappingProxyType,
)
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    Generator,
    Iterable,
    NamedTuple,
    Optional,
    Set,
    Tuple,
    Union,
)

from syrupy.constants import (
    SYMBOL_ELLIPSIS,
    TEXT_ENCODING,
)
from syrupy.data import (
    Snapshot,
    SnapshotCollection,
)

if TYPE_CHECKING:
    from syrupy.types import (
        PropertyFilter,
        PropertyMatcher,
        PropertyName,
        PropertyPath,
        SerializableData,
    )

    PropertyValueFilter = Callable[["PropertyName"], bool]
    PropertyValueGetter = Callable[
        ["SerializableData", "PropertyName"], "SerializableData"
    ]
    IterableEntries = Tuple[
        Iterable["PropertyName"],
        "PropertyValueGetter",
        Optional["PropertyValueFilter"],
    ]


class Repr:
    def __init__(self, _repr: str):
        self._repr = _repr

    def __repr__(self) -> str:
        return self._repr


def attr_getter(o: "SerializableData", p: "PropertyName") -> "SerializableData":
    return getattr(o, str(p))


def item_getter(o: "SerializableData", p: "PropertyName") -> "SerializableData":
    return o[p]


class MalformedAmberFile(Exception):
    """
    The Amber file is malformed. It should be deleted and regenerated.
    """


class MissingVersionError(Exception):
    """
    Missing Amber version marker.
    """


class AmberDataSerializer:
    """
    If extending the serializer, change the VERSION property to some unique value
    for your iteration of the serializer so as to force invalidation of existing
    snapshots.
    """

    VERSION = "1"

    _indent: str = "  "
    _max_depth: int = 99
    _marker_prefix = "# "

    class Marker:
        Version = "serializer version"
        Name = "name"
        Divider = "---"

    @classmethod
    def _snapshot_sort_key(cls, snapshot: "Snapshot") -> Any:
        return snapshot.name

    @classmethod
    def write_file(
        cls, snapshot_collection: "SnapshotCollection", merge: bool = False
    ) -> None:
        """
        Writes the snapshot data into the snapshot file that can be read later.
        """
        filepath = snapshot_collection.location
        if merge:
            base_snapshot = cls.read_file(filepath)
            base_snapshot.merge(snapshot_collection)
            snapshot_collection = base_snapshot

        with open(filepath, "w", encoding=TEXT_ENCODING, newline=None) as f:
            f.write(f"{cls._marker_prefix}{cls.Marker.Version}: {cls.VERSION}\n")
            for snapshot in sorted(
                snapshot_collection,
                key=cls._snapshot_sort_key,  # noqa: E501
            ):
                snapshot_data = str(snapshot.data)
                if snapshot_data is not None:
                    f.write(f"{cls._marker_prefix}{cls.Marker.Name}: {snapshot.name}\n")
                    for data_line in snapshot_data.splitlines(keepends=True):
                        f.write(cls.with_indent(data_line, 1))
                    f.write(f"\n{cls._marker_prefix}{cls.Marker.Divider}\n")

    @classmethod
    def __read_file_with_markers(
        cls, filepath: str
    ) -> Generator["Snapshot", None, None]:
        marker_offset = len(cls._marker_prefix)
        indent_len = len(cls._indent)

        test_name = None
        snapshot_data = ""
        tainted = False
        missing_version = True

        try:
            with open(filepath, encoding=TEXT_ENCODING, newline=None) as f:
                for line_no, line in enumerate(f):
                    if line.startswith(cls._marker_prefix):
                        marker_key, *marker_rest = line[marker_offset:].split(
                            ":", maxsplit=1
                        )
                        marker_key = marker_key.rstrip(" \r\n")
                        marker_value = marker_rest[0].strip() if marker_rest else None

                        if marker_key == cls.Marker.Version:
                            if line_no:
                                raise MalformedAmberFile(
                                    "Version must be specified at the top of the file."
                                )
                            if not marker_value or marker_value != cls.VERSION:
                                tainted = True
                                continue
                            missing_version = False

                        if marker_key == cls.Marker.Name:
                            if not marker_value:
                                raise MalformedAmberFile("Missing snapshot name.")

                            test_name = marker_value.strip(" \r\n")
                            continue
                        if marker_key == cls.Marker.Divider:
                            if test_name and snapshot_data:
                                yield Snapshot(
                                    name=test_name,
                                    data=snapshot_data.rstrip(os.linesep),
                                    tainted=tainted,
                                )
                            test_name = None
                            snapshot_data = ""
                    elif test_name is not None and line.startswith(cls._indent):
                        snapshot_data += line[indent_len:]
        except FileNotFoundError:
            pass
        else:
            if missing_version:
                raise MissingVersionError

    @classmethod
    def read_file(cls, filepath: str) -> "SnapshotCollection":
        """
        Read the raw snapshot data (str) from the snapshot file into a dict
        of snapshot name to raw data. This does not attempt any deserialization
        of the snapshot data.
        """
        snapshot_collection = SnapshotCollection(location=filepath)
        try:
            for snapshot in cls.__read_file_with_markers(filepath):
                if snapshot.tainted:
                    snapshot_collection.tainted = True
                snapshot_collection.add(snapshot)
        except MissingVersionError:
            snapshot_collection.tainted = True

        return snapshot_collection

    @classmethod
    def serialize(
        cls,
        data: "SerializableData",
        *,
        exclude: Optional["PropertyFilter"] = None,
        include: Optional["PropertyFilter"] = None,
        matcher: Optional["PropertyMatcher"] = None,
    ) -> str:
        """
        After serializing, new line control characters are normalised. This is needed
        for interoperablity of snapshot matching between systems that do not use the
        same new line control characters. Example snapshots generated on windows os
        should not break when running the tests on a unix based system and vice versa.
        """
        serialized = cls._serialize(
            data, exclude=exclude, include=include, matcher=matcher
        )
        return serialized.replace("\r\n", "\n").replace("\r", "\n")

    @classmethod
    def _serialize(
        cls,
        data: "SerializableData",
        *,
        depth: int = 0,
        exclude: Optional["PropertyFilter"] = None,
        include: Optional["PropertyFilter"] = None,
        matcher: Optional["PropertyMatcher"] = None,
        path: "PropertyPath" = (),
        visited: Optional[Set[Any]] = None,
    ) -> str:
        visited = set() if visited is None else visited
        data_id = id(data)
        if depth > cls._max_depth or data_id in visited:
            data = Repr(SYMBOL_ELLIPSIS)
        elif matcher:
            data = matcher(data=data, path=path)
        serialize_kwargs = {
            "data": data,
            "depth": depth,
            "exclude": exclude,
            "include": include,
            "matcher": matcher,
            "path": path,
            "visited": {*visited, data_id},
        }
        serialize_method = cls.serialize_unknown
        if isinstance(data, str):
            serialize_method = cls.serialize_string
        elif isinstance(data, (int, float)):
            serialize_method = cls.serialize_number
        elif isinstance(data, (set, frozenset)):
            serialize_method = cls.serialize_set
        elif isinstance(data, (dict, MappingProxyType)):
            serialize_method = cls.serialize_dict
        elif cls.__is_namedtuple(data):
            serialize_method = cls.serialize_namedtuple
        elif isinstance(data, (list, tuple, GeneratorType)):
            serialize_method = cls.serialize_iterable
        elif isinstance(data, FunctionType):
            serialize_method = cls.serialize_function
        return serialize_method(**serialize_kwargs)

    @classmethod
    def serialize_number(
        cls, data: Union[int, float], *, depth: int = 0, **kwargs: Any
    ) -> str:
        return cls.__serialize_plain(data=data, depth=depth)

    @classmethod
    def serialize_string(cls, data: str, *, depth: int = 0, **kwargs: Any) -> str:
        if all(c not in data for c in "\r\n"):
            return cls.__serialize_plain(data=data, depth=depth)

        return cls.__serialize_lines(
            data=data,
            lines=(
                cls.with_indent(line, depth + 1 if depth else depth)
                for line in str(data).splitlines(keepends=True)
            ),
            depth=depth,
            open_tag="'''",
            close_tag="'''",
            include_type=False,
            ends="",
        )

    @classmethod
    def serialize_iterable(
        cls, data: Iterable["SerializableData"], **kwargs: Any
    ) -> str:
        open_paren, close_paren = (None, None)
        if isinstance(data, list):
            open_paren, close_paren = ("[", "]")

        values = list(data)
        return cls.serialize_custom_iterable(
            data=data,
            resolve_entries=(range(len(values)), item_getter, None),
            open_paren=open_paren,
            close_paren=close_paren,
            **kwargs,
        )

    @classmethod
    def serialize_set(cls, data: Set["SerializableData"], **kwargs: Any) -> str:
        return cls.serialize_custom_iterable(
            data=data,
            resolve_entries=(cls.sort(data), lambda _, p: p, None),
            open_paren="{",
            close_paren="}",
            **kwargs,
        )

    @classmethod
    def serialize_namedtuple(cls, data: NamedTuple, **kwargs: Any) -> str:
        return cls.serialize_custom_iterable(
            data=data,
            resolve_entries=(cls.sort(data._fields), attr_getter, None),
            separator="=",
            **kwargs,
        )

    @classmethod
    def serialize_dict(
        cls, data: Dict["PropertyName", "SerializableData"], **kwargs: Any
    ) -> str:
        keys = (
            data.keys() if isinstance(data, (OrderedDict,)) else cls.sort(data.keys())
        )

        return cls.serialize_custom_iterable(
            data=data,
            resolve_entries=(keys, item_getter, None),
            open_paren="{",
            close_paren="}",
            separator=": ",
            serialize_key=True,
            **kwargs,
        )

    @classmethod
    def serialize_function(
        cls, data: FunctionType, *, depth: int = 0, **kwargs: Any
    ) -> str:
        return cls.__serialize_plain(
            data=f"{data.__qualname__}{str(inspect.signature(data))}", depth=depth
        )

    @classmethod
    def serialize_unknown(cls, data: Any, *, depth: int = 0, **kwargs: Any) -> str:
        if data.__class__.__repr__ != object.__repr__:
            return cls.__serialize_plain(data=data, depth=depth)

        return cls.serialize_custom_iterable(
            data=data,
            resolve_entries=(
                cls.sort(cls.object_attrs(data)),
                attr_getter,
                lambda v: not callable(v),
            ),
            depth=depth,
            separator="=",
            **kwargs,
        )

    @classmethod
    def object_attrs(cls, data: Any) -> "Iterable[str]":
        return (name for name in dir(data) if not name.startswith("_"))

    @classmethod
    def object_as_named_tuple(cls, data: Any) -> "tuple[Any, ...]":
        attr_names = list(cls.object_attrs(data))
        return collections.namedtuple(data.__class__.__name__, attr_names)(
            **{prop: getattr(data, prop) for prop in attr_names}
        )

    @classmethod
    def with_indent(cls, string: str, depth: int) -> str:
        return f"{cls._indent * depth}{string}"

    @classmethod
    def sort(cls, iterable: Iterable[Any]) -> Iterable[Any]:
        try:
            return sorted(iterable)
        except TypeError:
            return sorted(iterable, key=cls._serialize)

    @classmethod
    def object_type(cls, data: "SerializableData") -> str:
        return f"{data.__class__.__name__}"

    @classmethod
    def __is_namedtuple(cls, obj: Any) -> bool:
        return isinstance(obj, tuple) and all(
            isinstance(n, (str,)) for n in getattr(obj, "_fields", [None])
        )

    @classmethod
    def __serialize_plain(
        cls,
        *,
        data: "SerializableData",
        depth: int = 0,
    ) -> str:
        return cls.with_indent(repr(data), depth)

    @classmethod
    def serialize_custom_iterable(
        cls,
        *,
        data: "SerializableData",
        resolve_entries: "IterableEntries",
        open_paren: Optional[str] = None,
        close_paren: Optional[str] = None,
        depth: int = 0,
        exclude: Optional["PropertyFilter"] = None,
        include: Optional["PropertyFilter"] = None,
        path: "PropertyPath" = (),
        separator: Optional[str] = None,
        serialize_key: bool = False,
        **kwargs: Any,
    ) -> str:
        """
        Utility to serialize a custom iterable.
        """
        kwargs["depth"] = depth + 1

        keys, get_value, include_value = resolve_entries
        key_values = (
            (key, get_value(data, key))
            for key in keys
            if (not exclude or not exclude(prop=key, path=path))
            and (not include or include(prop=key, path=path))
        )
        entries = (
            entry
            for entry in key_values
            if not include_value or include_value(entry[1])
        )

        def key_str(key: "PropertyName") -> str:
            if separator is None:
                return ""
            return (
                cls._serialize(data=key, **kwargs)
                if serialize_key
                else cls.with_indent(str(key), depth=depth + 1)
            ) + separator

        def value_str(key: "PropertyName", value: "SerializableData") -> str:
            serialized = cls._serialize(
                data=value,
                exclude=exclude,
                include=include,
                path=(*path, (key, type(value))),
                **kwargs,
            )
            return serialized if separator is None else serialized.lstrip(cls._indent)

        return cls.__serialize_lines(
            data=data,
            lines=(f"{key_str(key)}{value_str(key, value)}," for key, value in entries),
            depth=depth,
            open_tag=f"({open_paren or ''}",
            close_tag=f"{close_paren or ''})",
        )

    @classmethod
    def __serialize_lines(
        cls,
        *,
        data: "SerializableData",
        lines: Iterable[str],
        open_tag: str,
        close_tag: str,
        depth: int = 0,
        include_type: bool = True,
        ends: str = "\n",
    ) -> str:
        lines = ends.join(lines)
        lines_end = "\n" if lines else ""
        maybe_obj_type = f"{cls.object_type(data)}" if include_type else ""
        formatted_open_tag = cls.with_indent(f"{maybe_obj_type}{open_tag}", depth)
        formatted_close_tag = cls.with_indent(close_tag, depth)
        return f"{formatted_open_tag}\n{lines}{lines_end}{formatted_close_tag}"


class AmberDataSerializerSorted(AmberDataSerializer):
    """
    This is an experimental serializer with known performance issues.
    """

    VERSION = f"{AmberDataSerializer.VERSION}-sorted"

    @classmethod
    def __maybe_int(cls, part: str) -> Tuple[int, Union[str, int]]:
        try:
            # cast to int only if the string is the exact representation of the int
            # for example, '012' != str(int('012'))
            i = int(part)
            if str(i) == part:
                return (1, i)
            return (0, part)
        except ValueError:
            # the nested tuple is to prevent comparing a str to an int
            return (0, part)

    @classmethod
    def _snapshot_sort_key(cls, snapshot: "Snapshot") -> Any:
        return [cls.__maybe_int(part) for part in snapshot.name.split(".")]
