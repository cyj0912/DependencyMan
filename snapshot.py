import os
import hashlib
from itertools import filterfalse

class Snapshot:
    def listdir(self, path):
        raise NotImplementedError()

    def get_hash(self, path):
        raise NotImplementedError()

    def is_dir(self, path):
        raise NotImplementedError()


class OSSnapshot(Snapshot):
    def __init__(self, root):
        self.root = root

    def listdir(self, path):
        return os.listdir(os.path.join(self.root, path))

    def get_hash(self, path):
        hasher = hashlib.sha1()
        with open(os.path.join(self.root, path), mode="rb") as f:
            buf = f.read()
            hasher.update(buf)
        return hasher.hexdigest()

    def is_dir(self, path):
        return os.path.isdir(os.path.join(self.root, path))


class SnapshotDirCmp:
    def __init__(self, a, asnap, b, bsnap):
        self.snapshot_left = asnap
        self.snapshot_right = bsnap
        self.left = a
        self.right = b

    def phase0(self):
        self.left_list = self.snapshot_left.listdir(self.left)
        self.right_list = self.snapshot_right.listdir(self.right)
        self.left_list.sort()
        self.right_list.sort()

    def phase1(self):
        a = dict(zip(map(os.path.normcase, self.left_list), self.left_list))
        b = dict(zip(map(os.path.normcase, self.right_list), self.right_list))
        self.common = list(map(a.__getitem__, filter(b.__contains__, a)))
        self.left_only = list(map(a.__getitem__, filterfalse(b.__contains__, a)))
        self.right_only = list(map(b.__getitem__, filterfalse(a.__contains__, b)))

    def phase2(self):
        self.common_dirs = []
        self.common_files = []
        self.common_funny = []
        for x in self.common:
            a_path = os.path.join(self.left, x)
            b_path = os.path.join(self.right, x)
            a_isdir = self.snapshot_left.is_dir(a_path)
            b_isdir = self.snapshot_right.is_dir(b_path)
            if a_isdir != b_isdir:
                self.common_funny.append(x)
            elif a_isdir:
                self.common_dirs.append(x)
            else:
                self.common_files.append(x)

    def phase3(self):
        self.same_files = []
        self.diff_files = []
        for x in self.common_files:
            a_path = os.path.join(self.left, x)
            b_path = os.path.join(self.right, x)
            a_hash = self.snapshot_left.get_hash(a_path)
            b_hash = self.snapshot_right.get_hash(b_path)
            if a_hash == b_hash:
                self.same_files.append(x)
            else:
                self.diff_files.append(x)
    
    def phase4(self):
        self.subdirs = {}
        for x in self.common_dirs:
            a_path = os.path.join(self.left, x)
            b_path = os.path.join(self.right, x)
            self.subdirs[x] = SnapshotDirCmp(a_path, self.snapshot_left, b_path, self.snapshot_right)

    methodmap = dict(subdirs = phase4,
                     same_files = phase3, diff_files = phase3,
                     common_dirs = phase2, common_files = phase2, common_funny = phase2,
                     common = phase1, left_only = phase1, right_only = phase1,
                     left_list = phase0, right_list = phase0)

    def __getattr__(self, attr):
        if attr not in self.methodmap:
            raise AttributeError(attr)
        self.methodmap[attr](self)
        return getattr(self, attr)


def test():
    a = OSSnapshot('E:\Dev\constructfield\DependencyMan')
    b = OSSnapshot('E:\Dev\constructfield')
    dircmp = SnapshotDirCmp('', a, '', b)
    print("Succeed")
    print(dircmp.subdirs)
    for x in dircmp.subdirs:
        print(dircmp.subdirs[x].common_files)
        print(dircmp.subdirs[x].common_dirs)

if __name__ == "__main__":
    test()
