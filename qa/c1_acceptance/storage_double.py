"""Synthetic IStorage surface for existing parser tests, with no real COM.

This deliberately does not validate native CFB/OLE storage serialization. The
existing record/image parser assertions still run against their original data.
"""
import base64
import json
from unittest.mock import patch

MAGIC = bytes.fromhex('D0CF11E0A1B11AE1') + b'C1_TEST_STORAGE\x00'


def encode(value):
    if isinstance(value, bytes):
        return {'bytes': base64.b64encode(value).decode('ascii')}
    return {name: encode(child) for name, child in value.items()}


def decode(value):
    if set(value) == {'bytes'}:
        return base64.b64decode(value['bytes'])
    return {name: decode(child) for name, child in value.items()}


class Memory:
    def __init__(self):
        self.tree = None
        self.data = b''

    def WriteAt(self, offset, data):
        self.data = self.data[:offset] + data

    def ReadAt(self, offset, size):
        data = MAGIC + json.dumps(encode(self.tree)).encode() if self.tree is not None else self.data
        return data[offset:offset + size]

    def Stat(self, flags):
        return None, None, len(self.ReadAt(0, 2**31))


class Stream:
    def __init__(self, tree, name):
        self.tree, self.name = tree, name

    def Write(self, data):
        self.tree[self.name] = data

    def Commit(self, flags):
        pass

    def Stat(self):
        return None, None, len(self.tree[self.name])

    def Read(self, size):
        return self.tree[self.name][:size]


class Storage:
    def __init__(self, tree):
        self.tree = tree

    def CreateStream(self, name, mode):
        self.tree[name] = b''
        return Stream(self.tree, name)

    def OpenStream(self, name, reserved, mode):
        return Stream(self.tree, name)

    def CreateStorage(self, name, mode, reserved):
        self.tree[name] = {}
        return Storage(self.tree[name])

    def OpenStorage(self, name, reserved, mode):
        return Storage(self.tree[name])

    def EnumElements(self):
        return [(name, 2 if isinstance(value, bytes) else 1) for name, value in self.tree.items()]

    def Commit(self, flags):
        pass


def create(memory, *args):
    memory.tree = {}
    return Storage(memory.tree)


def open_storage(memory, *args):
    if not memory.data.startswith(MAGIC):
        raise ValueError('Not a synthetic storage fixture')
    return Storage(decode(json.loads(memory.data[len(MAGIC):])))


def install(stack):
    replacements = {'CoInitialize': lambda: None, 'CoUninitialize': lambda: None,
                    'CreateILockBytesOnHGlobal': Memory,
                    'StgCreateDocfileOnILockBytes': create,
                    'StgOpenStorageOnILockBytes': open_storage}
    for name, replacement in replacements.items():
        stack.enter_context(patch('pythoncom.' + name, new=replacement))
