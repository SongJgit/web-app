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
    srv = await loop.create_server(app.make_handler(), '127.0.0.1', 9000)
    # 创建TCP服务,监听host地址的port端口,返回一个sever对象
    logging.info('server started at http://127.0.0.1:9000...')
    return srv


loop = asyncio.get_event_loop()
loop.run_until_complete(init(loop))
loop.run_forever()
