import asyncio
import sanic
from subprocess import check_call
from wsmprpc import RPCServer
from .cozmars_server import CozmarsServer
from . import util
from .version import __version__
from websockets.exceptions import ConnectionClosedOK
_ = util._
parsed_template = util.parsed_template

async def dim_screen(sec):
    global cozmars_rpc_server
    await asyncio.sleep(sec)
    cozmars_rpc_server._screen_backlight(None)

def lightup_screen(sec):
    global cozmars_rpc_server, dim_screen_task, server_loop
    dim_screen_task and server_loop.call_soon_threadsafe(dim_screen_task.cancel)
    cozmars_rpc_server._screen_backlight(.02)
    dim_screen_task = asyncio.run_coroutine_threadsafe(dim_screen(5), server_loop)

async def delay_check_call(sec, cmd):
    await asyncio.sleep(sec)
    cozmars_rpc_server._screen_backlight(0)
    check_call(cmd.split(' '))

async def button_poweroff():
    cozmars_rpc_server.screen.image(util.poweroff_screen())
    cozmars_rpc_server._screen_backlight(.02)
    await util.beep(cozmars_rpc_server)
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
    await util.beep(cozmars_rpc_server)

app.static('/static', util.STATIC)
app.static('/conf', util.CONF, content_type="application/json")
app.static('/env', util.ENV, content_type="application/json")

@app.route('/')
def index(request):
    return sanic.response.html(parsed_template('index', version=__version__, mac=util.MAC, serial=util.SERIAL, ip=util.IP))

@app.route('/servo')
def servo(request):
    return sanic.response.html(parsed_template('servo'))

@app.route('/motor')
def motor(request):
    return sanic.response.html(parsed_template('motor'))

@app.route('/test')
def test(request):
    return sanic.response.html(parsed_template('test'))

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
    return f"""<html>
        <head><meta charset='utf-8'/><meta http-equiv='refresh' content='{str(sec)};url={url}' /></head>
        <body>{txt}</body>
        </html>"""

@app.route('/restart_wifi')
def restart_wifi(request):
    asyncio.create_task(delay_check_call(1, 'sudo systemctl restart autohotspot.service'))
    return sanic.response.html(redirect_html(15, '/', """<p>{}...</p>""".format(_("Restarting network"))))

@app.route('/restart_service')
def restart_server(request):
    asyncio.create_task(delay_check_call(1, 'sudo systemctl restart cozmars.service'))
    return sanic.response.html(redirect_html(15, '/', """<p>{}...</p>""".format(_("Restarting service"))))

@app.route('/poweroff')
def poweroff(request):
    cozmars_rpc_server.screen.image(util.poweroff_screen())
    cozmars_rpc_server.screen_backlight.fraction = .1
    asyncio.create_task(delay_check_call(5, 'sudo poweroff'))
    return sanic.response.html("""<p>{}<br> {}</p>""".format(_("Shutting down"), _("Please wait for the power light in the head of the Cozmars robot to go out before pressing the power button on the side.")))

@app.route('/reboot')
def reboot(request):
    cozmars_rpc_server.screen.image(util.reboot_screen())
    cozmars_rpc_server.screen_backlight.fraction = .1
    asyncio.create_task(delay_check_call(5, 'sudo reboot'))
    return sanic.response.html(redirect_html(60, '/', """<p>{}... </p> <p>{}</p>""".format(_("Rebooting"), _("This takes about a minute"))))

@app.route('/about')
def serial(request):
    return sanic.response.json({'hostname': util.HOSTNAME, 'mac': util.MAC, 'serial':util.SERIAL, 'version': __version__, 'ip': util.IP})

@app.route('/wifi')
def wifi(request):
    from subprocess import check_output
    s = check_output(r"sudo grep ssid\|psk /etc/wpa_supplicant/wpa_supplicant.conf".split(' ')).decode()
    ssid, pw = [a[a.find('"')+1:a.rfind('"')] for a in s.split('\n')[:2]]
    return sanic.response.html(parsed_template("wifi", ssid=ssid, hostname=util.HOSTNAME, serial=util.SERIAL, ip="10.3.141.1"))

@app.route('/save_wifi', methods=['POST', 'GET'])
def save_wifi(request):
    from subprocess import check_call
    try:
        ssid, pw = [(request.form or request.args)[a][0] for a in ['ssid', 'pass']]
        check_call(f'sudo sh {util.pkg("save_wifi.sh")} {ssid} {pw}'.split(' '))
        return sanic.response.html("""<p style='color:green'>
            {}
            <form action='/restart_wifi'>
            <input type='submit' value='{}'>
            </form></p>""".format(_("Wifi settings saved, will be effective after restarting the network"), _("Restart Network")))
    except Exception as e:
        return sanic.response.html("""<p stype='color:red'>{}<br><br>{}</p>""".format(_("Wifi setup failed"), str(e)))

@app.route('/upgrade')
def upgrade(request):

    async def streaming_fn(response):
        await response.write("""<p>{}...</p>""".format(_("Checking for upgrade, please wait")))
        proc = await asyncio.create_subprocess_shell(cozmars_rpc_server.conf['upgrade']['cmd'], stderr=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE)

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
            await response.write("""<p style='color:red'>********* {} *********</p>""".format(_("Update failed")))
        else:
            await response.write("""<p style='color:green'>********* {} *********<br>
                <form action='/restart_service'><input type='submit' value='{}'></form>
                </p>""".format(_("Upgrade complete, will be effective after restarting service"), _("Restart service")))
    return sanic.response.stream(streaming_fn, content_type='text/html; charset=utf-8')

# if __name__ == "__main__":
app.run(host="0.0.0.0", port=80, debug=False)
# app.run(host="0.0.0.0", port=80)
