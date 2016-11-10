import os
import hashlib
import json

def get_file_hash(path):
    hasher = hashlib.sha1()
    with open(path, mode="rb") as f:
        buf = f.read()
        hasher.update(buf)
    return hasher.hexdigest()

def is_matching_rule(filepath, rule):
    filepath = filepath.replace(os.sep, '/')
    rule = rule.replace(os.sep, '/')
    if filepath == '':
        if rule == '/':
            return True
        else:
            return False
    if rule.startswith('/'):
        if filepath.startswith(rule):
            return True
        else:
            return False
    if filepath.find(rule) != -1:
        return True
    else:
        return False

def is_excluded(filepath, ruleset = []):
    for rule in ruleset:
        if is_matching_rule(filepath, rule):
            return True
    return False

def get_filetree(path, exclude = []):
    treeroot = dict()
    path = path.rstrip(os.sep)
    pathstart = path.rfind(os.sep) + 1
    for rootdir, dirs, files in os.walk(path, topdown=True):
        relrootdir = rootdir.replace(path, "", 1)
        if is_excluded(relrootdir, exclude):
            dirs[:] = []
            continue
        goodfiles = [f for f in files if not is_excluded(relrootdir + os.sep + f, exclude)]
        currnode = dict.fromkeys(goodfiles)
        for it in goodfiles:
            currnode[it] = {}
            currnode[it]['#'] = get_file_hash(rootdir + os.sep + it)
        folders = relrootdir.split(os.sep)
        parentnode = treeroot
        for next in folders[:-1]:
            parentnode = parentnode[next]
        parentnode[folders[-1]] = currnode
    return treeroot['']

def save_filetree(filetree, path):
    with open(path, mode='w') as f:
        json.dump(filetree, f)

def load_filetree(path):
    with open(path, mode='r') as f:
        filetree = json.load(f)
        return filetree

def walk_filetree(filetreenode, dirfunc, filefunc, thispath = ''):
    if '*' in filetreenode:
        filefunc(thispath, filetreenode)
        return
    dirfunc(thispath, filetreenode)
    for name, node in filetreenode.items():
        walk_filetree(node, dirfunc, filefunc, thispath + '/' + name)
