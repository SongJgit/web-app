import asyncio
import logging
import aiomysql


def log(sql, args=()):
    logging.info('SQL: %s' % sql)


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
        maxsize=kw.get('maxsize', 10),
        minsize=kw.get('minsize', 1),
        loop=loop
    )


async def select(sql,args,size=None):
    # 传入sql语句和参数
    # args：表示就是将实参中按照位置传值
    log(sql, args)
    global __pool
    async with __pool.get() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute(sql.replace('?', '%s'), args or ())
            if size:
                rs = await cur.fetchmany(size)
            else:
                rs = await cur.fetchall()
        logging.info('rows returned: %s' % len(rs))
        return rs


async def destory_pool():
    # 连接池的销毁
    global __pool
    if __pool is not None:
        __pool.close()
        await __pool.await_closed


async def execute(sql,args,autocommit=True):
    # 通用函数,执行增删改,cursor通过rowcount返回结果数不返回结果集
    log(sql)
    async with __pool.get() as conn:
        if not autocommit:
            await conn.begin()
        try:
            async with conn.cursor(aiomysql.DictCursor) as cur:
                await cur.execute(sql.replace('?','%s'),args)
                affected =cur.rowcount
            if not autocommit:
                await  conn.commit()
        except BaseException as e:
            if not autocommit:
                await  conn.rollback()
            raise
        finally:
            conn.close()
        return affected


def create_args_string(num):
    # 用于输出元类中创建sql_insert语句中的占位符
    L = []
    for n in range(num):
        L.append('?')
    return ','.join(L)
    # 用,连接起来组成一个字符串


# orm框架
class Field(object):
    # 保存数据库的字段名和字段类型
    # 对数据库的字段进行定义,其子类对应多个类型
    def __init__(self, name, column_type, primary_key, default):
        self.name = name
        self.column_type = column_type
        self.primary_kry = primary_key
        self.default = default

    def __str__(self):
        return '<%s, %s:%s>' % (self.__class__.__name__, self.column_type, self.name)


class StringField(Field):
    # 以下的field分别代表不同的数据属性
    def __init__(self, name=None, primary_key=False, default=None, ddl='varchar(100)'):
        super().__init__(name, ddl, primary_key, default)


class BooleanField(Field):
    def __init__(self, name=None, default=False):
        super().__init__(name, 'boolean', False, default)


class IntegerField(Field):

    def __init__(self, name=None, primary_key=False, default=0):
        super().__init__(name, 'real', primary_key, default)


class TextField(Field):

    def __init__(self, name=None, default=None):
        super().__init__(name, 'text', False, default)


class ModelMetaclass(type):

    def __new__(cls, name, bases, attrs):
        # cls 当前准备创建的类的对象
        # name 类的名字
        # bases 类继承的父类的集合
        # attrs 类的方法以及属性的集合
        if name == 'Model':
            return type.__new__(cls, name, bases, attrs)
        tableName = attrs.get('__table__', None) or name
        # 取出表名,默认与类的名字相同
        logging.info('found model : %s (table:%s)' % (name, tableName))
        mappings = dict()
        # 存储所有的字段,以及字段值
        fields = []
        # 用来存储主键以外的属性,而且只保存key
        primaryKey = None
        for k, v in attrs.items():
            # k属性或方法名字,v是值
            if isinstance(v, Field):
                # 寻找Field类型
                logging.info('found mapping :%s==>%s' % (k, v))
                mappings[k] = v
                # 把键值对存入mappings字典中,比如name对应<StringField:username>
                if v.primary_key:
                    # 找到主键
                    if primaryKey:
                        raise ValueError('Duplicate primary key for field :%s'% k)
                    primaryKey = k # 此列设置为列表的主键
                else:
                    fields.append(k)
        if not primaryKey:
            raise ValueError('Primary key not found')
        for k in mappings.key():
            attrs.pop(k)
            # 从类的实行中删除Field属性,否则有可能出现运行错误,实例的属性会遮盖类的同名属性
        escaped_fields = list(map(lambda f: '%s' % f, fields))
        # 保存除主键外的属性名为''(运算出字符串)列表形式
        attrs['__mappings__'] = mappings
        # 保存属性和列的映射关系
        attrs['__table__'] = tableName
        # 保存表名
        attrs['__primary_key__'] = primaryKey
        # 保存主键属性名
        attrs['__fields__'] = fields
        # 除主键外的属性名
        attrs['__select__'] = 'select `%s`, %s from `%s`' % (primaryKey, ', '.join(escaped_fields), tableName)
        attrs['__insert__'] = 'insert into `%s` (%s, `%s`) values (%s)' % (tableName, ', '.join(escaped_fields),
                                                                           primaryKey, create_args_string(len(escaped_fields) + 1))
        attrs['__update__'] = 'update `%s` set %s where `%s`=?' % (tableName,
                                                                   ', '.join(map(lambda f: '`%s`=?' % (mappings.get(f).name or f), fields)), primaryKey)
        attrs['__delete__'] = 'delete from `%s` where `%s`=?' % (tableName, primaryKey)
        return type.__new__(cls, name, bases, attrs)


class Model(dict,metaclass=ModelMetaclass):

    def __init__(self, **kw):
        super().__init__(**kw)

    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError(r"'Model' object has no attribute '%s'" % key)

    def __setattr__(self, key, value):
        self[key] = value

    def getValue(self, key):
        # 返回对象的属性如果没有属性则会调用__getattr__
        return getattr(self, key, None)

    def getValue0rDefault(self,key):
        value = getattr(self, key, None)
        if value is None:
            field = self.__mapping__[key]
            if field.default is not None:
                value = field.default() if callable(field.default) else field.default
                logging.debug('using default value for %s:%s' % (key,str(value)))
                setattr(self, key, value)
        return  value

@classmethod
async def findAll(cls, where=None, args=None, **kw):
    sql = [cls.__select__]




