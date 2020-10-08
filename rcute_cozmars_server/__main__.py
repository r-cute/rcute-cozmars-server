import asyncio
import sanic

from subprocess import check_call
from wsmprpc import RPCServer
from .cozmars_server import CozmarsServer
from . import util
from .version import __version__
from websockets.exceptions import ConnectionClosedOK

async def dim_screen(sec):
    global cozmars_rpc_server
    await asyncio.sleep(sec)
    cozmars_rpc_server.screen_backlight.fraction = None

def lightup_screen(sec):
    global cozmars_rpc_server, dim_screen_task, server_loop
    dim_screen_task and server_loop.call_soon_threadsafe(dim_screen_task.cancel)
    cozmars_rpc_server.screen_backlight.fraction = .1
    dim_screen_task = asyncio.run_coroutine_threadsafe(dim_screen(5), server_loop)

async def delay_check_call(sec, cmd):
    await asyncio.sleep(sec)
    cozmars_rpc_server.screen_backlight.fraction = 0
    check_call(cmd.split(' '))

async def button_poweroff():
    cozmars_rpc_server.screen.image(util.poweroff_screen())
    cozmars_rpc_server.screen_backlight.fraction = .1
    cozmars_rpc_server.buzzer.play('A4')
    await asyncio.sleep(.3)
    cozmars_rpc_server.buzzer.stop()
    await delay_check_call(5, 'sudo poweroff')

def idle():
    global cozmars_rpc_server, server_loop
    cozmars_rpc_server.screen.image(util.splash_screen())
    cozmars_rpc_server.button.when_pressed = lambda: lightup_screen(5)
    cozmars_rpc_server.button.hold_time = 5
    cozmars_rpc_server.button.when_held = lambda: asyncio.run_coroutine_threadsafe(button_poweroff(), server_loop)

app = sanic.Sanic(__name__)

@app.listener("before_server_start")
async def before_server_start(request, loop):
    global cozmars_rpc_server, dim_screen_task, server_loop
    server_loop = loop
    dim_screen_task = None
    cozmars_rpc_server = CozmarsServer()
    idle()
    lightup_screen(5)
    cozmars_rpc_server.buzzer.play('C4')
    await asyncio.sleep(.3)
    cozmars_rpc_server.buzzer.stop()

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
    else:
        dim_screen_task.cancel()
        await ws.send('0')
        try:
            async with cozmars_rpc_server:
                await RPCServer(ws, cozmars_rpc_server).run()
        finally:
            idle()

def redirect_html(sec, url, txt):
    return "<html><head><meta charset='utf-8'/><meta http-equiv='refresh' content='"+str(sec)+";url="+url+"'/></head><body>"+txt+"</body></html>"

@app.route('/restart_wifi')
def restart_wifi(request):
    asyncio.create_task(delay_check_call(1, 'sudo systemctl restart autohotspot.service'))
    return sanic.response.html(redirect_html(15, '/', '<p>正在重启网络...</p>'))

@app.route('/restart_server')
def restart_server(request):
    asyncio.create_task(delay_check_call(1, 'sudo systemctl restart cozmars.service'))
    return sanic.response.html(redirect_html(15, '/', '<p>正在重启服务...</p>'))

@app.route('/poweroff')
def poweroff(request):
    cozmars_rpc_server.screen.image(util.poweroff_screen())
    cozmars_rpc_server.screen_backlight.fraction = .1
    asyncio.create_task(delay_check_call(5, 'sudo poweroff'))
    return sanic.response.html('<p>正在关机...</p><p>软件关机后请等待 Cozmars 机器人头部内的电源灯熄灭后再按下侧面的电源键</p>')

@app.route('/reboot')
def reboot(request):
    cozmars_rpc_server.screen.image(util.reboot_screen())
    cozmars_rpc_server.screen_backlight.fraction = .1
    asyncio.create_task(delay_check_call(5, 'sudo reboot'))
    return sanic.response.html(redirect_html(60, '/', '<p>正在重启...</p><p>大约需要一分钟</p>'))

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
        return sanic.response.html("<p style='color:green'>wifi设置已保存，重启网络后生效<form action='restart_wifi'><input type='submit' value='重启网络'></form></p>")
    except Exception as e:
        return sanic.response.html(f"<p stype='color:red'>wifi设置失败<br><br>{str(e)}</p>")

@app.route('/')
def index(request):
    with open(util.static('index.tmpl')) as file:
        return sanic.response.html(file.read().format(version=__version__, mac=util.MAC, serial=util.SERIAL, ip=util.IP))

@app.route('/upgrade')
def upgrade(request):

    async def streaming_fn(response):
        await response.write('<p>正在检查更新，请稍等...</p>')
        proc = await asyncio.create_subprocess_shell('sudo python3 -m pip install rcute-cozmars-server -U -i https://pypi.tuna.tsinghua.edu.cn/simple', stderr=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE)

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

        await asyncio.wait([write(proc.stdout, '%s<br>', False),
                            write(proc.stderr, '<span style="color:red">%s</span><br>', True)])
        if err_flag:
            await response.write("<p style='color:red'>********* 更新失败 *********</p>")
        else:
            await response.write("<p style='color:green'>********* 更新完成，重启服务后生效 *********<br><form action='restart_server'><input type='submit' value='重启服务'></form></p>")
    return sanic.response.stream(streaming_fn, content_type='text/html; charset=utf-8')

# if __name__ == "__main__":
app.run(host="0.0.0.0", port=80, debug=False)
# app.run(host="0.0.0.0", port=80)
