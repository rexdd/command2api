#!/bin/env python3
# coding: utf-8

import sys
import json
import socket
import string
import random
import logging
import argparse
import textwrap
from threading import Thread
from subprocess import Popen, PIPE
from flask import Response, Flask, request

VERSION = "0.0.2"

port = 8888
uri = '/' + ''.join(random.sample(string.ascii_letters+string.digits, 8))

app = Flask(__name__)


def get_lan_ip():
    hostname = socket.gethostname()
    ip = socket.gethostbyname(hostname)
    return ip


def get_wan_ip():
    with Popen("curl -m 2 -s ip.sb", shell=True, stdout=PIPE) as proc:
        wan_ip = proc.stdout.read().decode("utf8")
    if wan_ip:
        return wan_ip.strip()
    else:
        return get_lan_ip()


def command_run(command):
    global result
    result = {"code": 200, "data": []}

    with Popen(command, shell=True, stdout=PIPE) as proc:
        command_data = proc.stdout.readlines()

    if command_data:
        result['command'] = command
        for data in command_data:
            result['data'].append(data.decode('utf-8').strip())
        return result
    else:
        result['code'] = 500
        result['command'] = command
        return result


class MyThread(Thread):
    def __init__(self, func, args):
        super(MyThread, self).__init__()
        self.func = func
        self.args = args

    def run(self):
        self.result = self.func(*self.args)

    def get_result(self):
        return self.result


def main():
    if uri in request.url:
        if args.only:
            return Response(json.dumps(result, indent=4), mimetype="application/json")
        else:
            res = command_run(cli)
            return Response(json.dumps(res, indent=4), mimetype="application/json")


if __name__ == '__main__':
    logging_format = logging.Formatter(
        '%(asctime)s %(filename)s[line:%(lineno)d] %(levelname)s - %(message)s')

    handler = logging.FileHandler('/var/log/command2api.log')
    handler.setLevel(logging.DEBUG)
    handler.setFormatter(logging_format)

    app.logger.addHandler(handler)

    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=textwrap.dedent("""\
                    -> 实时获取终端命令执行结果，返回JSON格式 - 万物皆可API
                    """),
        epilog=textwrap.dedent(f"""\
                    Example:
                    # {sys.argv[0]} --cli "date" --uri "/stats" --port {port}"""))
    parser.add_argument("--cli", required=True, help='执行命令')
    parser.add_argument("--uri", help='URI地址, 默认值: 随时生成')
    parser.add_argument("--port", help=f"监听端口, 默认值: {port}")
    parser.add_argument("--only", action='store_true',
                        help='仅执行一次，适用查看长时间执行结果')
    parser.add_argument("--version", action='version',
                        version=f'%(prog)s version {VERSION}')
    args = parser.parse_args()

    cli = args.cli

    if args.uri:
        uri = args.uri
    app.add_url_rule(uri, 'main', main)

    if args.port:
        port = args.port

    lan_ip = get_lan_ip()
    wan_ip = get_wan_ip()
    request_lan_url = f"http://{lan_ip}:{port}{uri}"
    request_wan_url = f"http://{wan_ip}:{port}{uri}"

    print("="*50)
    print(f"内网地址: {request_lan_url}")
    print(f"外网地址: {request_wan_url}")
    print("="*50)

    if args.only:
        mt = MyThread(command_run, args=(cli,))
        mt.start()

    app.run(host='0.0.0.0', port=port)
