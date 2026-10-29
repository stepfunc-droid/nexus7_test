#!/usr/bin/env python3
"""Minimal dependency-free read-only ext4 resolver for Phase6 host tracing.

Scope is intentionally narrow: normal ext4 images using extents, directories,
and fast/extent-backed symlinks.  It never writes the image.
"""

from __future__ import annotations

import os
import posixpath
import struct
from dataclasses import dataclass
from pathlib import Path

EXT4_SUPER_MAGIC = 0xEF53
EXT4_EXTENTS_FL = 0x00080000
EXT4_EXT_MAGIC = 0xF30A
S_IFMT = 0xF000
S_IFREG = 0x8000
S_IFDIR = 0x4000
S_IFLNK = 0xA000
ROOT_INO = 2


class Ext4Error(RuntimeError):
    pass


def u16(data: bytes, off: int) -> int:
    return struct.unpack_from("<H", data, off)[0]


def u32(data: bytes, off: int) -> int:
    return struct.unpack_from("<I", data, off)[0]


@dataclass(frozen=True)
class Extent:
    logical_block: int
    physical_block: int
    blocks: int
    unwritten: bool = False


@dataclass(frozen=True)
class Inode:
    number: int
    mode: int
    size: int
    flags: int
    block: bytes

    @property
    def kind(self) -> int:
        return self.mode & S_IFMT


class Ext4Image:
    def __init__(self, path: Path | str):
        self.path = Path(path)
        self.fd = os.open(self.path, os.O_RDONLY)
        try:
            sb = os.pread(self.fd, 1024, 1024)
            if len(sb) != 1024:
                raise Ext4Error("short ext4 superblock")
            if u16(sb, 0x38) != EXT4_SUPER_MAGIC:
                raise Ext4Error(f"not ext4: {self.path}")
            self.block_size = 1024 << u32(sb, 0x18)
            self.blocks_per_group = u32(sb, 0x20)
            self.inodes_per_group = u32(sb, 0x28)
            self.inode_size = u16(sb, 0x58) or 128
            desc_size = u16(sb, 0xFE)
            self.desc_size = max(32, desc_size or 32)
            if self.block_size < 1024 or self.block_size & (self.block_size - 1):
                raise Ext4Error(f"invalid block size {self.block_size}")
            if self.inodes_per_group <= 0 or self.inode_size < 128:
                raise Ext4Error("invalid ext4 inode geometry")
            self.gdt_offset = (2 if self.block_size == 1024 else 1) * self.block_size
        except Exception:
            os.close(self.fd)
            raise

    def close(self) -> None:
        if self.fd >= 0:
            os.close(self.fd)
            self.fd = -1

    def __enter__(self) -> "Ext4Image":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def pread(self, size: int, offset: int) -> bytes:
        data = os.pread(self.fd, size, offset)
        if len(data) != size:
            raise Ext4Error(f"short read offset={offset} size={size}")
        return data

    def _inode_table_block(self, group: int) -> int:
        gd = self.pread(self.desc_size, self.gdt_offset + group * self.desc_size)
        lo = u32(gd, 0x08)
        hi = u32(gd, 0x28) if self.desc_size >= 64 else 0
        return lo | (hi << 32)

    def inode(self, ino: int) -> Inode:
        if ino <= 0:
            raise Ext4Error(f"invalid inode {ino}")
        group = (ino - 1) // self.inodes_per_group
        index = (ino - 1) % self.inodes_per_group
        table = self._inode_table_block(group)
        raw = self.pread(
            self.inode_size,
            table * self.block_size + index * self.inode_size,
        )
        mode = u16(raw, 0x00)
        size_lo = u32(raw, 0x04)
        flags = u32(raw, 0x20)
        # ext4 stores i_size_high in i_dir_acl only for regular files.  For
        # directories/symlinks that field has other semantics, so never fold it
        # into their size.
        size_hi = u32(raw, 0x6C) if (mode & S_IFMT) == S_IFREG and len(raw) >= 0x70 else 0
        size = size_lo | (size_hi << 32)
        return Inode(ino, mode, size, flags, raw[0x28:0x28 + 60])

    def _extent_node(self, raw: bytes, expected_depth: int | None = None) -> list[Extent]:
        if len(raw) < 12 or u16(raw, 0) != EXT4_EXT_MAGIC:
            raise Ext4Error("inode/file does not contain a valid extent tree")
        entries = u16(raw, 2)
        maximum = u16(raw, 4)
        depth = u16(raw, 6)
        if expected_depth is not None and depth != expected_depth:
            raise Ext4Error(f"extent depth mismatch {depth} != {expected_depth}")
        if entries > maximum or 12 + entries * 12 > len(raw):
            raise Ext4Error("invalid extent header")

        out: list[Extent] = []
        if depth == 0:
            for i in range(entries):
                off = 12 + i * 12
                logical = u32(raw, off)
                raw_len = u16(raw, off + 4)
                start_hi = u16(raw, off + 6)
                start_lo = u32(raw, off + 8)
                unwritten = raw_len > 0x8000
                blocks = raw_len - 0x8000 if unwritten else raw_len
                if blocks == 0:
                    blocks = 0x8000
                if blocks <= 0:
                    raise Ext4Error("zero-length extent")
                physical = start_lo | (start_hi << 32)
                out.append(Extent(logical, physical, blocks, unwritten))
            return out

        for i in range(entries):
            off = 12 + i * 12
            leaf_lo = u32(raw, off + 4)
            leaf_hi = u16(raw, off + 8)
            leaf = leaf_lo | (leaf_hi << 32)
            child = self.pread(self.block_size, leaf * self.block_size)
            out.extend(self._extent_node(child, depth - 1))
        return out

    def extents(self, inode: Inode) -> list[Extent]:
        if not (inode.flags & EXT4_EXTENTS_FL) and u16(inode.block, 0) != EXT4_EXT_MAGIC:
            raise Ext4Error(f"inode {inode.number} does not use extents")
        extents = self._extent_node(inode.block)
        extents.sort(key=lambda x: x.logical_block)
        return extents

    def read_inode(self, inode: Inode) -> bytes:
        if inode.size == 0:
            return b""
        if inode.kind == S_IFLNK and inode.size <= len(inode.block) and not (inode.flags & EXT4_EXTENTS_FL):
            return inode.block[:inode.size]
        out = bytearray(inode.size)
        for ex in self.extents(inode):
            logical_off = ex.logical_block * self.block_size
            if logical_off >= inode.size:
                continue
            span = min(ex.blocks * self.block_size, inode.size - logical_off)
            if ex.unwritten:
                continue
            data = self.pread(span, ex.physical_block * self.block_size)
            out[logical_off:logical_off + span] = data
        return bytes(out)

    def file_ranges(self, inode: Inode) -> list[dict[str, int]]:
        """Map file logical bytes to byte ranges in this filesystem image."""
        ranges: list[dict[str, int]] = []
        for ex in self.extents(inode):
            if ex.unwritten:
                continue
            file_off = ex.logical_block * self.block_size
            if file_off >= inode.size:
                continue
            length = min(ex.blocks * self.block_size, inode.size - file_off)
            ranges.append({
                "file_offset": file_off,
                "image_offset": ex.physical_block * self.block_size,
                "length": length,
            })
        return ranges

    def _dir_lookup(self, dir_inode: Inode, name: str) -> int:
        if dir_inode.kind != S_IFDIR:
            raise Ext4Error(f"inode {dir_inode.number} is not a directory")
        data = self.read_inode(dir_inode)
        off = 0
        target = name.encode()
        while off + 8 <= len(data):
            ino = u32(data, off)
            rec_len = u16(data, off + 4)
            name_len = data[off + 6]
            if rec_len < 8 or off + rec_len > len(data):
                raise Ext4Error(f"bad directory record in inode {dir_inode.number}")
            if ino and 8 + name_len <= rec_len:
                entry_name = data[off + 8:off + 8 + name_len]
                if entry_name == target:
                    return ino
            off += rec_len
        raise FileNotFoundError(name)

    def read_symlink(self, inode: Inode) -> str:
        if inode.kind != S_IFLNK:
            raise Ext4Error("not a symlink")
        return self.read_inode(inode).decode("utf-8", "surrogateescape")

    def resolve(self, path: str, *, follow_final: bool = True, _depth: int = 0) -> Inode:
        if _depth > 16:
            raise Ext4Error("too many symlinks")
        if not path.startswith("/"):
            path = "/" + path
        path = posixpath.normpath(path)
        parts = [p for p in path.split("/") if p]
        current = self.inode(ROOT_INO)
        resolved: list[str] = []

        for i, part in enumerate(parts):
            child_ino = self._dir_lookup(current, part)
            child = self.inode(child_ino)
            is_final = i == len(parts) - 1
            if child.kind == S_IFLNK and (follow_final or not is_final):
                target = self.read_symlink(child)
                remaining = parts[i + 1:]
                if target.startswith("/"):
                    new_path = target
                else:
                    base = "/" + "/".join(resolved)
                    new_path = posixpath.join(base, target)
                if remaining:
                    new_path = posixpath.join(new_path, *remaining)
                return self.resolve(new_path, follow_final=follow_final, _depth=_depth + 1)
            current = child
            resolved.append(part)
        return current

    def first_existing(self, candidates: list[str]) -> tuple[str, Inode]:
        errors = []
        for path in candidates:
            try:
                return path, self.resolve(path)
            except (FileNotFoundError, Ext4Error) as exc:
                errors.append(f"{path}: {exc}")
        raise Ext4Error("none of the candidate paths resolved: " + "; ".join(errors))
