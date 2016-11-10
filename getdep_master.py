#!/usr/bin/env python3

import os
import json
import hashlib
import requests
import argparse
import lzma
from multiprocessing import Pool


class StorageProvider:
    def __init__(self):
        pass

    upload_queue = []

    def upload(self, filepath, fileprop):
        self.upload_queue.append((filepath, fileprop['#']))

    def upload_worker(self, fileobj):
        r = requests.get('http://upback.azurewebsites.net/exists/' + fileobj[1])
        if r.text == '0':
            print('Uploading:', fileobj[0])
            with open(fileobj[0], mode='rb') as f:
                compressed = lzma.compress(f.read())
                r = requests.put('http://upback.azurewebsites.net/upload/' + fileobj[1], data=compressed)
                print(r.text)

    #Just in case you want to process files in batch
    #This is called after upload
    def process_upload(self):
        p = Pool(10)
        p.map(self.upload_worker, self.upload_queue)
        self.upload_queue = []

    download_queue = []

    def download(self, filepath, fileprop):
        self.download_queue.append((filepath, fileprop['#']))

    def download_worker(obj, fileobj):
        print("Downloading:", fileobj[0], fileobj[1])
        r = requests.get('http://upback.azurewebsites.net/upload/' + fileobj[1])
        if r.status_code != 404:
            data = lzma.decompress(r.content)
            if not os.path.exists(os.path.dirname(fileobj[0])):
                os.makedirs(os.path.dirname(fileobj[0]))
            with open(fileobj[0], mode="wb") as f:
                f.write(data)

    #Just in case you want to process files in batch
    #This is called after download
    def process_download(self):
        p = Pool(10)
        p.map(self.download_worker, self.download_queue)
        self.download_queue = []


def insert_file(treeRef, relpathList):
    if relpathList == []:
        treeRef['@'] = 'File'
    else:
        key = relpathList.pop(0)
        if key == '.':
            insert_file(treeRef, relpathList)
        else:
            if key not in treeRef:
                treeRef[key] = dict()
            insert_file(treeRef[key], relpathList)


def foreach_file(ref, path='.'):
    if '@' in ref and ref['@'] == 'File':
        yield (path, ref)
    else: # ref is Dir, ref HAS TO be a Dir!!! Not checked
        for i in ref:
            yield from foreach_file(ref[i], path + '/' + i)


def create_snapshot():
    dir_whitelist = ['Source/Thirdparty']

    # Check current dir
    if not os.path.isdir('Source'):
        raise NameError('Not in correct dir')

    snapshot = dict()

    for rootdir, dirs, files in os.walk('.'):
        skip_subdirs = True
        skip_files = True
        for targetDir in dir_whitelist:
            relpath = os.path.relpath(targetDir, start=rootdir)
            if not relpath.startswith('..') or relpath.endswith('..'):
                skip_subdirs = False
            if relpath.endswith('..') or relpath == '.':
                skip_files = False
        if skip_subdirs:
            continue

        if skip_files:
            continue
        for f in files:
            fpath = os.path.join(rootdir, f)
            fpath_list = []
            fpath, lname = os.path.split(fpath)
            while lname != '':
                fpath_list.append(lname)
                fpath, lname = os.path.split(fpath)
            fpath_list.reverse()
            insert_file(snapshot, fpath_list)

    for fpath, fprop in foreach_file(snapshot):
        hasher = hashlib.sha1()
        with open(fpath, mode='rb') as f:
            buf = f.read()
            hasher.update(buf)
        fprop['#'] = hasher.hexdigest()
        print(fpath, fprop)

    with open('dependency_manifest.json', mode='w') as f:
        json.dump(snapshot, f)
    return snapshot


def hash_file(fpath):
    hasher = hashlib.sha1()
    with open(fpath, mode='rb') as f:
        buf = f.read()
        hasher.update(buf)
    return hasher.hexdigest()


class EntryPoint:
    def __init__(self):
        parser = argparse.ArgumentParser(usage="""getdep command [-h]

Dependency Manager 1.0 for construct3

most common commands:
  snapshot    Create a snapshot
  upload      Upload all files
  download    Download all files
  verify      Verify your local copy""")
        parser.add_argument("command", help="subcommand to run")
        args = parser.parse_args()
        if not hasattr(self, args.command):
            print("Unrecognized command")
            parser.print_help()
            exit(1)
        getattr(self, args.command)()

    def snapshot(self):
        create_snapshot()

    def upload(self):
        if not os.path.exists("dependency_manifest.json"):
            print("No manifest found")
            exit(1)
        with open("dependency_manifest.json", mode="r") as f:
            snapshot = json.load(f)
        file_count = 0
        for fpath, fprop in foreach_file(snapshot):
            file_count = file_count + 1
            if not os.path.exists(fpath):
                print("Missing file:", fpath)
                print("Manifest might be outdated")
                exit(1)
            if hash_file(fpath) != fprop['#']:
                print("Corrupted file:", fpath)
                print("Manifest might be outdated")
                exit(1)
        print("Total files to upload:", file_count)
        uploader = StorageProvider()
        uploaded_count = 0
        for fpath, fprop in foreach_file(snapshot):
            uploader.upload(fpath, fprop)
            uploaded_count = uploaded_count + 1
            print(uploaded_count)
        uploader.process_upload()

    def download(self):
        if not os.path.exists("dependency_manifest.json"):
            print("No manifest found")
            exit(1)
        with open("dependency_manifest.json", mode="r") as f:
            snapshot = json.load(f)
        file_count = 0
        for fpath, fprop in foreach_file(snapshot):
            if not os.path.exists(fpath):
                file_count = file_count + 1
        print("Total files to download:", file_count)
        downloader = StorageProvider()
        downloaded_count = 0
        for fpath, fprop in foreach_file(snapshot):
            if not os.path.exists(fpath):
                if not os.path.exists(os.path.dirname(fpath)):
                    os.makedirs(os.path.dirname(fpath))
                downloader.download(fpath, fprop)
                downloaded_count = downloaded_count + 1
                print(downloaded_count)
            else:
                if hash_file(fpath) != fprop['#']:
                    os.remove(fpath)
                    downloader.download(fpath, fprop)
                    downloaded_count = downloaded_count + 1
                    print(downloaded_count, "Force override")

        downloader.process_download()
        print("Finished!")

    def verify(self):
        if not os.path.exists("dependency_manifest.json"):
            print("No manifest found")
            exit(1)
        with open("dependency_manifest.json", mode="r") as f:
            snapshot = json.load(f)
        good = 0
        bad = 0
        for fpath, fprop in foreach_file(snapshot):
            hasher = hashlib.sha1()
            badfile = False
            try:
                with open(fpath, mode='rb') as f:
                    buf = f.read()
                    hasher.update(buf)
            except IOError:
                badfile = True
            if fprop['#'] != hasher.hexdigest() or badfile:
                bad = bad + 1
                print("Corrupted file:", fpath)
            else:
                good = good + 1
        print("Verification finished:", good, "are good,", bad, "failed")



if __name__ == '__main__':
    EntryPoint()
