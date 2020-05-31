import asyncio
import sanic

from wsmprpc import RPCServer
from cozmars_server import CozmarsServer

from subprocess import check_call

app = sanic.Sanic(__name__)

@app.listener("before_server_start")
async def before_server_start(request, loop):
    global cozmars_rpc_server
    cozmars_rpc_server = CozmarsServer()

app.static('/static', './static/')
app.static('/servo', './static/servo.html', content_type="text/html; charset=utf-8")
app.static('/', './static/index.html', content_type="text/html; charset=utf-8")

@app.websocket('/rpc')
async def rpc(request, ws):
    async with cozmars_rpc_server:
        await RPCServer(ws, cozmars_rpc_server).run()

@app.route('/poweroff')
def poweroff(request):
    check_call(['sudo', 'poweroff'])

@app.route('/reboot')
def reboot(request):
    check_call(['sudo', 'reboot'])

@app.route('/serial')
def serial(request):
    import uuid
    return sanic.response.text(hex(uuid.getnode())[-4:])

@app.route('/ip')
def ip(request):
    import socket
    return sanic.response.text(socket.gethostbyname(f'{socket.gethostname()}.local'))

app.run(host="0.0.0.0", port=80, debug=False)
# app.run(host="0.0.0.0", port=80)
