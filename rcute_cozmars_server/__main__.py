import asyncio
import sanic

from wsmprpc import RPCServer
from cozmars_server import CozmarsServer

# https://stackoverflow.com/questions/6028000/how-to-read-a-static-file-from-inside-a-python-package#
# import pkgutil

app = sanic.Sanic(__name__)

@app.listener("before_server_start")
async def before_server_start(request, loop):
    global cozmars_rpc_server
    cozmars_rpc_server = CozmarsServer()

app.static('/static', './static/')
app.static('/servo', './static/servo.html', content_type="text/html; charset=utf-8")
app.static('/test', './static/test.html', content_type="text/html; charset=utf-8")
app.static('/', './static/index.html', content_type="text/html; charset=utf-8")

@app.websocket('/rpc')
async def rpc(request, ws):
    async with cozmars_rpc_server:
        await RPCServer(ws, cozmars_rpc_server).run()

@app.route('/poweroff')
def poweroff(request):
    from subprocess import check_call
    check_call(['sudo', 'poweroff'])

@app.route('/reboot')
def reboot(request):
    from subprocess import check_call
    check_call(['sudo', 'reboot'])

def _mac():
    import uuid
    return hex(uuid.getnode())[2:]

@app.route('/serial')
def serial(request):
    return sanic.response.text(_serial()[-4:])

def _ip():
    import socket
    return socket.gethostbyname(f'{socket.gethostname()}.local')

@app.route('/ip')
def ip(request):
    import socket
    return sanic.response.text(_ip())

def _version():
    return '1.0.1'

@app.route('/version')
def version(request):
    return sanic.response.text(_version())

@app.route('/wifi')
def wifi(request):
    from subprocess import check_output
    s = check_output(r"sudo grep ssid\|psk /etc/wpa_supplicant/wpa_supplicant-wlan0.conf".split(' ')).decode()
    ssid, pw = [a[a.find('"')+1:-1] for a in s.split('\n')[:2]]
    # return sanic.response.html(pkgutil.get_data(__name__, 'static/wifi.tmpl').decode().format(ssid=ssid, pw=pw))
    with open('./static/wifi.tmpl') as file:
        return sanic.response.html(file.read().format(ssid=ssid, pw=pw))

@app.route('/save_wifi', methods=['POST', 'GET'])
def save_wifi(request):
    from subprocess import check_call
    try:
        ssid, pw = [(request.form or request.args)[a][0] for a in ['ssid', 'pass']]
        check_call(f'sudo sh save_wifi.sh {ssid} {pw}'.split(' '))
        return sanic.response.html("<p style='color:green'>wifi设置已保存，<form action='reboot'><input type='submit' value='重启cozmars'></form></p>")
    except Exception as e:
        return sanic.response.html(f"<p stype='color:red'>wifi设置失败<br><br>{str(e)}</p>")

@app.route('/about')
def about(request):
    mac = _mac()
    # return sanic.response.html(pkgutil.get_data(__name__, 'static/about.tmpl').decode().format(version=_version(),mac=':'.join([mac[i:i+2] for i in range(0,12,2)]),serial=mac[-4:],ip=_ip()))
    with open('./static/about.tmpl') as file:
        return sanic.response.html(file.read().format(version=_version(),mac=':'.join([mac[i:i+2] for i in range(0,12,2)]),serial=mac[-4:],ip=_ip()))

@app.route('/upgrade')
def upgrade(request):

    async def streaming_fn(response):
        proc = await asyncio.create_subprocess_shell('sudo pip3 install rcute-cozmars-server -U', stderr=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE)

        async def write(stream, format):
            while True:
                line = await stream.readline()
                if line:
                    await response.write(format % line.decode().rstrip())
                else:
                    break

        await asyncio.wait([write(proc.stdout, '%s<br>'),
                            write(proc.stderr, '<span style="color:red">%s</span><br>')])
    return sanic.response.stream(streaming_fn, content_type='text/html')

# if __name__ == "__main__":
app.run(host="0.0.0.0", port=80, debug=False)
# app.run(host="0.0.0.0", port=80)
