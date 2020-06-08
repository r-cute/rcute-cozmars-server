import asyncio
import sanic

from wsmprpc import RPCServer
from cozmars_server import CozmarsServer

app = sanic.Sanic(__name__)

@app.listener("before_server_start")
async def before_server_start(request, loop):
    global cozmars_rpc_server
    cozmars_rpc_server = CozmarsServer()

app.static('/static', './static/')
app.static('/servo', './static/servo.html', content_type="text/html; charset=utf-8")
app.static('/about', './static/about.html', content_type="text/html; charset=utf-8")
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

@app.route('/serial')
def serial(request):
    import uuid
    return sanic.response.text(hex(uuid.getnode())[-4:])

@app.route('/ip')
def ip(request):
    import socket
    return sanic.response.text(socket.gethostbyname(f'{socket.gethostname()}.local'))

@app.route('/version')
def version(request):
    return sanic.response.text('1.0')

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


app.run(host="0.0.0.0", port=80, debug=False)
# app.run(host="0.0.0.0", port=80)
