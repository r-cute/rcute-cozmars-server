import asyncio
import sanic

from wsmprpc import RPCServer
from .cozmars_server import CozmarsServer
from . import util
from .version import __version__

app = sanic.Sanic(__name__)

@app.listener("before_server_start")
async def before_server_start(request, loop):
    global cozmars_rpc_server
    cozmars_rpc_server = CozmarsServer()

app.static('/static', util.STATIC)
app.static('/servo', util.static('servo.html'), content_type="text/html; charset=utf-8")
app.static('/test', util.static('test.html'), content_type="text/html; charset=utf-8")
app.static('/', util.static('index.html'), content_type="text/html; charset=utf-8")

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

@app.route('/serial')
def serial(request):
    return sanic.response.text(util.MAC[-4:])

@app.route('/ip')
def ip(request):
    return sanic.response.text(util.IP)

@app.route('/version')
def version(request):
    return sanic.response.text(__version__)

@app.route('/wifi')
def wifi(request):
    from subprocess import check_output
    s = check_output(r"sudo grep ssid\|psk /etc/wpa_supplicant/wpa_supplicant-wlan0.conf".split(' ')).decode()
    ssid, pw = [a[a.find('"')+1:-1] for a in s.split('\n')[:2]]
    with open(util.static('wifi.tmpl')) as file:
        return sanic.response.html(file.read().format(ssid=ssid, pw=pw))

@app.route('/save_wifi', methods=['POST', 'GET'])
def save_wifi(request):
    from subprocess import check_call
    try:
        ssid, pw = [(request.form or request.args)[a][0] for a in ['ssid', 'pass']]
        check_call(f'sudo sh {util.pkg("save_wifi.sh")} {ssid} {pw}'.split(' '))
        return sanic.response.html("<p style='color:green'>wifi设置已保存，<form action='reboot'><input type='submit' value='重启cozmars'></form></p>")
    except Exception as e:
        return sanic.response.html(f"<p stype='color:red'>wifi设置失败<br><br>{str(e)}</p>")

@app.route('/about')
def about(request):
    with open(util.static('about.tmpl')) as file:
        return sanic.response.html(file.read().format(version=__version__, mac=':'.join([util.MAC[i:i+2] for i in range(0,12,2)]),serial=util.MAC[-4:],ip=util.IP))

@app.route('/upgrade')
def upgrade(request):

    async def streaming_fn(response):
        await response.write('<p>正在检查更新，请稍等...</p>')
        proc = await asyncio.create_subprocess_shell('sudo pip3 install rcute-cozmars-server -U -i https://pypi.tuna.tsinghua.edu.cn/simple', stderr=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE)

        err_flag = False
        async def write(stream, format, err):
            nonlocal err_flag
            while True:
                line = await stream.readline()
                if line:
                    await response.write(format % line.decode().rstrip())
                    if err:
                        err_flag = True
                else:
                    break

        await asyncio.wait([write(proc.stdout, '%s<br>'),
                            write(proc.stderr, '<span style="color:red">%s</span><br>')])
        if err_flag:
            await response.write("<p style='color:red'>********* 更新失败 *********</p>")
        else:
            await response.write("<p style='color:green'>********* 更新完成 *********<br><form action='reboot'><input type='submit' value='重启cozmars'></form></p>")
    return sanic.response.stream(streaming_fn, content_type='text/html; charset=utf-8')

# if __name__ == "__main__":
app.run(host="0.0.0.0", port=80, debug=False)
# app.run(host="0.0.0.0", port=80)
