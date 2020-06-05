from typing import (
    Any,
    Callable,
    Hashable,
    Optional,
    Tuple,
    Type,
    Union,
)


SerializableData = Any
SerializedData = Union[str, bytes]
PropertyValueType = Type[Any]
PropertyPathEntry = Tuple[Hashable, PropertyValueType]
PropertyPath = Tuple[PropertyPathEntry, ...]
PropertyMatcher = Callable[..., Optional[SerializableData]]
