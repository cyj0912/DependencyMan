import os
import hashlib
import pathspec

import config

def get_file_hash(path):
    hasher = hashlib.sha1()
    with open(path, mode="rb") as f:
        buf = f.read()
        hasher.update(buf)
    return hasher.hexdigest()


class FileEntryLV1:
    def __init__(self, p, h = None):
        self.path = p
        if(h == None):
            self.hash = get_file_hash(config.reporoot + os.sep + p)
        else:
            self.hash = h

    def __str__(self):
        return str(self.__dict__)

    def __eq__(self, value):
        return self.path == value.path

    def __ge__(self, value):
        return self.path >= value.path

    def __gt__(self, value):
        return self.path > value.path


class ManifestLV1:
    def __init__(self):
        self.version = -1
        self.format = 'LV1'
        self.list = []
    
    def get_upload_dict(self):
        res = dict()
        for f in self.list:
            res[f.hash] = f.path
        return res

    def exists(self, path):
        tempfile = FileEntryLV1(path, '')
        return tempfile in self.list

    def walk_subdirectory(self, subpath, ignorerules = []):
        res = []
        spec = pathspec.PathSpec.from_lines(pathspec.patterns.GitWildMatchPattern, ignorerules)

        walkroot = config.reporoot + os.sep + subpath
        walkroot = os.path.abspath(walkroot)
        for rootdir, dirs, files in os.walk(walkroot):
            h = len(config.reporoot)
            prefix = rootdir[h + 1:]
            if(len(prefix) != 0):
                prefix = prefix + os.sep

            dirs[:] = [d for d in dirs if not spec.match_file(prefix + d)]
            filelist = [(prefix + f).replace(os.sep, '/') for f in files if not spec.match_file(prefix + f)]
            fileentries = [FileEntryLV1(f) for f in filelist]
            res.extend(fileentries)
        self.list = res

    def add_file(self, subpath, ignorerules = []):
        filepath = os.path.abspath(subpath)
        h = len(config.reporoot)
        if os.path.isfile(filepath):
            entry = FileEntryLV1(filepath[h + 1:].replace(os.sep, '/'))
            if entry not in self.list:
                self.list.append(entry)
            self.list = sorted(self.list)
            return

    def add_subdirectory(self, subpath, ignorerules = []):
        res = []
        spec = pathspec.PathSpec.from_lines(pathspec.patterns.GitWildMatchPattern, ignorerules)

        walkroot = os.path.abspath(subpath)
        for rootdir, dirs, files in os.walk(walkroot):
            h = len(config.reporoot)
            prefix = rootdir[h + 1:]
            if(len(prefix) != 0):
                prefix = prefix + os.sep

            dirs[:] = [d for d in dirs if not spec.match_file(prefix + d)]
            filelist = [(prefix + f).replace(os.sep, '/') for f in files if not spec.match_file(prefix + f)]
            fileentries = [FileEntryLV1(f) for f in filelist if not self.exists(f)]
            res.extend(fileentries)
        self.list.extend(res)
        self.list = sorted(self.list)

    def dumps(self):
        res = '{0}\n{1}\n'.format(self.version, self.format)
        for entry in self.list:
            res = res + entry.path + ' ' + entry.hash + '\n'
        return res

    def loads(self, s):
        self.list = []
        slines = s.splitlines()
        self.version = int(slines[0])
        self.format = slines[1]
        if self.format != 'LV1':
            return False
        for ln in slines[2:]:
            parts = ln.split(' ')
            self.list.append(FileEntryLV1(parts[0], parts[1]))


#dd = ManifestLV1()
#dd.walk_subdirectory('requests')
#print(dd.dumps())

#ff = FileEntry('.git')
#print(json.dumps(ff.__dict__))
