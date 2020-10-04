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
app.static('/motor', util.static('motor.html'), content_type="text/html; charset=utf-8")
app.static('/test', util.static('test.html'), content_type="text/html; charset=utf-8")
app.static('/config', util.CONF, content_type="application/json")
# app.static('/', util.static('index.html'), content_type="text/html; charset=utf-8")

@app.websocket('/rpc')
async def rpc(request, ws):
    if cozmars_rpc_server.lock.locked():
        await ws.send('-1')
        await ws.close()
        return
    await ws.send('0')
    async with cozmars_rpc_server:
        await RPCServer(ws, cozmars_rpc_server).run()

@app.route('/poweroff')
def poweroff(request):
    async def _poweroff():
        from subprocess import check_call
        await asyncio.sleep(1)
        check_call(['sudo', 'poweroff'])
    asyncio.create_task(_poweroff())
    return sanic.response.html('<p>正在关机...</p><p>软件关机后请等待 Cozmars 机器人头部内的电源灯熄灭后再按下侧面的电源键</p>')

@app.route('/reboot')
def reboot(request):
    async def _reboot():
        from subprocess import check_call
        await asyncio.sleep(1)
        check_call(['sudo', 'reboot'])
    asyncio.create_task(_reboot())
    return sanic.response.html('<p>正在重启...</p><p>大概需要几十秒至一分钟</p>')

@app.route('/about')
def serial(request):
    return sanic.response.json({'hostname': util.HOSTNAME, 'mac': util.MAC, 'serial':util.SERIAL, 'version': __version__, 'ip': util.IP})

@app.route('/wifi')
def wifi(request):
    from subprocess import check_output
    s = check_output(r"sudo grep ssid\|psk /etc/wpa_supplicant/wpa_supplicant.conf".split(' ')).decode()
    ssid, pw = [a[a.find('"')+1:a.rfind('"')] for a in s.split('\n')[:2]]
    with open(util.static('wifi.tmpl')) as file:
        return sanic.response.html(file.read().format(ssid=ssid, hostname=util.HOSTNAME, serial=util.SERIAL))

@app.route('/save_wifi', methods=['POST', 'GET'])
def save_wifi(request):
    from subprocess import check_call
    try:
        ssid, pw = [(request.form or request.args)[a][0] for a in ['ssid', 'pass']]
        check_call(f'sudo sh {util.pkg("save_wifi.sh")} {ssid} {pw}'.split(' '))
        return sanic.response.html("<p style='color:green'>wifi设置已保存，重启后生效<form action='reboot'><input type='submit' value='重启 Cozmars'></form></p>")
    except Exception as e:
        return sanic.response.html(f"<p stype='color:red'>wifi设置失败<br><br>{str(e)}</p>")

@app.route('/')
def index(request):
    with open(util.static('index.tmpl')) as file:
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
