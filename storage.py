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
