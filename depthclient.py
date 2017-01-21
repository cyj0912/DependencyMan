import os
import lzma
import hashlib

import requests
import config

class DepthClient:
    def __init__(self):
        self.server = config.settings['server']
        m = hashlib.md5()
        m.update(config.settings['password'].encode('utf-8'))
        self.cred = (config.settings['username'], m.hexdigest())
        print(self.cred)

    def get_server_file_list(self):
        r = requests.get(self.server + 'file')
        res = []
        for f in r.json()['files']:
            res.append(f['id'])
        return res

    def batch_upload(self, filelist):
        for h in filelist:
            with open(config.reporoot + os.sep + filelist[h], mode='rb') as f:
                compressed = lzma.compress(f.read())
                r = requests.put(self.server + 'file/' + h, auth=self.cred, headers = {'Content-Type' : 'application/octet-stream'}, data=compressed)
                print(r.status_code, r.text)

    def upload_manifest(self, content):
        r = requests.post(self.server + 'version', auth=self.cred, headers={'Content-Type' : 'application/octet-stream'}, data=content)
        print(r.status_code, r.text)

    def fetch_manifest(self, version):
        r = requests.get(self.server + 'version/' + str(version))
        return r.text

    def newest_version(self):
        r = requests.get(self.server + 'version', auth=self.cred)
        return r.json()['version']
