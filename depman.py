import sys
sys.path.append('./Lib')

import argparse
import json
import os
from pathlib import Path

import config
from manifestlv1 import ManifestLV1
from depthclient import DepthClient

class EntryPoint:
    def __init__(self):
        sys.path.append('./Lib')
        curp = Path.cwd()
        last = None
        while curp != last:
            curm = Path(curp, config.settings['manifest'])
            if curm.exists():
                config.reporoot = str(curp)
                config.repofound = True
            last = curp
            curp = curp.parent
        if config.reporoot == '':
            config.reporoot = os.path.abspath('.')
        else:
            if os.path.exists(config.reporoot + os.sep + config.settings['config']):
                with open(config.reporoot + os.sep + config.settings['config']) as f:
                    configjson = json.load(f)
                    config.settings.update(configjson)

        parser = argparse.ArgumentParser(prog='Depman', description='Dependency manager')
        subparsers = parser.add_subparsers(title='subcommands', dest='subcommand')
        parser_sync = subparsers.add_parser('sync')
        parser_push = subparsers.add_parser('push')
        parser_add = subparsers.add_parser('add')
        parser_add.add_argument('path')
        parser_diff = subparsers.add_parser('diff')
        parser_commit = subparsers.add_parser('commit')
        parser_init = subparsers.add_parser('init')
        args = parser.parse_args()
        if args.subcommand != 'init' and not config.repofound:
            print('No repository found')
            return
        if not args.subcommand:
            parser.print_help()
            return
        print('Root:', config.reporoot)
        func = getattr(self, args.subcommand)
        func(args)

    def init(self, args):
        if os.path.exists(config.reporoot + os.sep + config.settings['manifest']):
            print('Repository exists')
            return
        print('Initializing repository in ' + config.reporoot)
        m = ManifestLV1()
        with open(config.reporoot + os.sep + config.settings['manifest'], mode='w') as f:
            f.write(m.dumps())

    def sync(self, args):
        m = ManifestLV1()
        with open(config.reporoot + os.sep + config.settings['manifest'], mode='r') as f:
            m.loads(f.read())
        cli = DepthClient()
        nvsn = cli.newest_version()
        print('Current version:', m.version)
        print('Newest version:', nvsn)
        if m.version < nvsn:
            with open(config.reporoot + os.sep + config.settings['manifest'], mode='w') as f:
                f.write(cli.fetch_manifest(nvsn))

    def diff(self, args):
        pass

    def add(self, args):
        ignorelist = []
        with open(config.reporoot + os.sep + config.settings['ignore'], mode='r') as f:
            ignorelist = f.read()
            ignorelist = ignorelist.splitlines()
        ignorelist.append(config.settings['manifest'])
        m = ManifestLV1()
        with open(config.reporoot + os.sep + config.settings['manifest'], mode='r') as f:
            m.loads(f.read())
        p = args.path
        p = p.strip('/')
        p = p.strip('\\')
        if os.path.isfile(p):
            m.add_file(p, ignorelist)
        elif os.path.isdir(p):
            m.add_subdirectory(p, ignorelist)
        else:
            print('File not found:', p)
            return
        with open(config.reporoot + os.sep + config.settings['manifest'], mode='w') as f:
            f.write(m.dumps())

    def push(self, args):
        cli = DepthClient()
        remote = cli.get_server_file_list()
        m = ManifestLV1()
        with open(config.reporoot + os.sep + config.settings['manifest'], mode='r') as f:
            m.loads(f.read())
        local = m.get_upload_dict()
        pending = dict((h, local[h]) for h in local if h not in remote)
        cli.batch_upload(pending)
        m.version = cli.newest_version() + 1
        with open(config.reporoot + os.sep + config.settings['manifest'], mode='w') as f:
            f.write(m.dumps())
        with open(config.reporoot + os.sep + config.settings['manifest'], mode='r') as f:
            cli.upload_manifest(f.read())

if __name__ == '__main__':
    EntryPoint()
