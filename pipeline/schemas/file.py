import enum
from typing import Optional

from .base import BaseModel


class FileFormat(str, enum.Enum):
    """Represents the different formats files can be uploaded in"""

    hex = "hex"
    binary = "binary"


class FileBase(BaseModel):
    name: str
    # hex is the default purely for backwards-compatability
    file_format: FileFormat = FileFormat.hex


class FileGet(FileBase):
    id: str
    path: str
    #: The data as hex-encoded bytes, if the data size is less than 20 kB
    data: Optional[str]
    #: The data size in bytes
    file_size: int


class FileCreate(FileBase):
    name: Optional[str]
    file_bytes: Optional[str]
