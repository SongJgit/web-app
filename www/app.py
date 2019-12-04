import logging
logging.basicConfig(level=logging.INFO)

import asyncio,os,json,time
from datetime import datetime
from aiohttp import web


async def index(request):
    return web.Response(body=b'<h1>Awesome</h1>', content_type='text/html')


async def name(request):
    text = '<h1>hello, %s!</h1>' % request.match_info['name']
    return web.Response(body=text.encode('utf-8'), content_type='text/html')


async def init(loop):
    app = web.Application(loop=loop)
    app.add_routes([web.get('/', index),
                   web.get('/{name}', name)])
    # await 返回一个创建好的，绑定IP、端口、HTTP协议簇的监听服务的协程。await的作用是使srv的行为模式和 loop.create_server()一致
    srv = await loop.create_server(app.make_handler(), '127.0.0.1', 9000)
    logging.info('server started at http://127.0.0.1:9000...')
    return srv


loop = asyncio.get_event_loop()
loop.run_until_complete(init(loop))
loop.run_forever()
