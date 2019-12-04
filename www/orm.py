import asyncio
from aiohttp import web
import logging
import aiomysql
from orm import Model, StringField ,IntegerField


async def create_pool(loop,**kw):
    # **kw：表示就是形参中按照关键字传值，多余的值都给kw，且以字典*的方式呈现
    # 创建连接池,保持一定数量的连接
    logging.info('create database connection pool..')
    global __pool
    __pool = await aiomysql.create_pool(
        host=kw.get('host', 'localhost'),
        port=kw.get('port', 3306),
        user=kw['SJian'],
        password=kw['123'],
        db=kw['db'],
        charset=kw.get('charset','utf8'),
        autocommit=kw.get('autocommit',True),
        maxsize=kw.get('maxsize',10),
        minsize=kw.get('minsize',1),
        loop=loop
    )


async def select(sql,args,size=None):
    # 传入sql语句和参数
    # args：表示就是将实参中按照位置传值
    log(sql,args)
    global __pool
    with (await __pool) as conn:
        # 获取数据库连接
        cur = await conn.cursor(aiomysql.DictCursor)
        # 获取数据库游标
        await cur.execute(sql.replace('?','%s'),args or ())
        # 用?进行占位,用这些语句时在用%s替换
        if size:
            rs =await cur.fetchmany(size)
        else:
            rs = await cur.fetchall()
        await cur.close()
        logging.info("rows returned: %s" % len(rs))
        return rs


async def execute(sql,args):
    # 通用函数,执行增删改,cursor通过rowcount返回结果数不返回结果集
    log(sql)
    with (await __pool) as conn :
        try:
            cur  = await conn.cursor()
            await cur.execute(sql.replace('?','%s').args)
            affected =cur.rowcount
            await cur.close()
        except BaseException as e:
            raise
        return

class User(Model):
    __table__ = 'users'

    id = IntegerField(primary_key=True)
    name = StringField()


user = User(id=312091156, name='SJian')
user.insert()
user = user.findAll()


