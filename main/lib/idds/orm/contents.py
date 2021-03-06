#!/usr/bin/env python
#
# Licensed under the Apache License, Version 2.0 (the "License");
# You may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# http://www.apache.org/licenses/LICENSE-2.0OA
#
# Authors:
# - Wen Guan, <wen.guan@cern.ch>, 2019


"""
operations related to Requests.
"""

import datetime
import json

import sqlalchemy
from sqlalchemy import BigInteger, Integer
from sqlalchemy.exc import DatabaseError, IntegrityError
from sqlalchemy.sql import text, bindparam, outparam

from idds.common import exceptions
from idds.common.constants import ContentType, ContentStatus
from idds.orm.base.session import read_session, transactional_session
from idds.orm.base.utils import row2dict


@transactional_session
def add_content(coll_id, scope, name, min_id, max_id, content_type=ContentType.File, status=ContentStatus.New,
                bytes=0, md5=None, adler32=None, processing_id=None, storage_id=None, retries=0,
                path=None, expired_at=None, content_metadata=None, returning_id=False, session=None):
    """
    Add a content.

    :param coll_id: collection id.
    :param scope: The scope of the request data.
    :param name: The name of the request data.
    :param min_id: The minimal id of the content.
    :param max_id: The maximal id of the content.
    :param content_type: The type of the content.
    :param status: content status.
    :param bytes: The size of the content.
    :param md5: md5 checksum.
    :param alder32: adler32 checksum.
    :param processing_id: The processing id.
    :param storage_id: The storage id.
    :param retries: The number of retries.
    :param path: The content path.
    :param expired_at: The datetime when it expires.
    :param content_metadata: The metadata as json.

    :raises DuplicatedObject: If a collection with the same name exists.
    :raises DatabaseException: If there is a database error.

    :returns: content id.
    """
    if isinstance(content_type, ContentType):
        content_type = content_type.value
    if isinstance(status, ContentStatus):
        status = status.value
    if content_metadata:
        content_metadata = json.dumps(content_metadata)

    if returning_id:
        insert_coll_sql = """insert into atlas_idds.contents(coll_id, scope, name, min_id, max_id, content_type,
                                                                       status, bytes, md5, adler32, processing_id,
                                                                       storage_id, retries, path, expired_at,
                                                                       content_metadata)
                             values(:coll_id, :scope, :name, :min_id, :max_id, :content_type, :status, :bytes,
                                    :md5, :adler32, :processing_id, :storage_id, :retries, :path, :expired_at,
                                    :content_metadata) RETURNING content_id into :content_id
                          """
        stmt = text(insert_coll_sql)
        stmt = stmt.bindparams(outparam("content_id", type_=BigInteger().with_variant(Integer, "sqlite")))
    else:
        insert_coll_sql = """insert into atlas_idds.contents(coll_id, scope, name, min_id, max_id, content_type,
                                                                       status, bytes, md5, adler32, processing_id,
                                                                       storage_id, retries, path, expired_at,
                                                                       content_metadata)
                             values(:coll_id, :scope, :name, :min_id, :max_id, :content_type, :status, :bytes,
                                    :md5, :adler32, :processing_id, :storage_id, :retries, :path, :expired_at,
                                    :content_metadata)
                          """
        stmt = text(insert_coll_sql)

    try:
        content_id = None
        if returning_id:
            ret = session.execute(stmt, {'coll_id': coll_id, 'scope': scope, 'name': name, 'min_id': min_id, 'max_id': max_id,
                                         'content_type': content_type, 'status': status, 'bytes': bytes, 'md5': md5,
                                         'adler32': adler32, 'processing_id': processing_id, 'storage_id': storage_id,
                                         'retries': retries, 'path': path, 'created_at': datetime.datetime.utcnow(),
                                         'updated_at': datetime.datetime.utcnow(), 'expired_at': expired_at,
                                         'content_metadata': content_metadata, 'content_id': content_id})
            content_id = ret.out_parameters['content_id'][0]
        else:
            ret = session.execute(stmt, {'coll_id': coll_id, 'scope': scope, 'name': name, 'min_id': min_id, 'max_id': max_id,
                                         'content_type': content_type, 'status': status, 'bytes': bytes, 'md5': md5,
                                         'adler32': adler32, 'processing_id': processing_id, 'storage_id': storage_id,
                                         'retries': retries, 'path': path, 'created_at': datetime.datetime.utcnow(),
                                         'updated_at': datetime.datetime.utcnow(), 'expired_at': expired_at,
                                         'content_metadata': content_metadata})

        return content_id
    except IntegrityError as error:
        raise exceptions.DuplicatedObject('Content coll_id:scope:name(%s:%s:%s) already exists!: %s' %
                                          (coll_id, scope, name, error))
    except DatabaseError as error:
        raise exceptions.DatabaseException(error)


@transactional_session
def add_contents(contents, returning_id=False, bulk_size=100, session=None):
    """
    Add contents.

    :param contents: dict of contents.
    :param returning_id: whether to return id.
    :param session: session.

    :raises DuplicatedObject: If a collection with the same name exists.
    :raises DatabaseException: If there is a database error.

    :returns: content id.
    """
    default_params = {'coll_id': None, 'scope': None, 'name': None, 'min_id': None, 'max_id': None,
                      'content_type': ContentType.File, 'status': ContentStatus.New,
                      'bytes': 0, 'md5': None, 'adler32': None, 'processing_id': None,
                      'storage_id': None, 'retries': 0, 'path': None,
                      'expired_at': datetime.datetime.utcnow() + datetime.timedelta(days=30),
                      'content_metadata': None}

    if returning_id:
        insert_coll_sql = """insert into atlas_idds.contents(coll_id, scope, name, min_id, max_id, content_type,
                                                                       status, bytes, md5, adler32, processing_id,
                                                                       storage_id, retries, path, expired_at,
                                                                       content_metadata)
                             values(:coll_id, :scope, :name, :min_id, :max_id, :content_type, :status, :bytes,
                                    :md5, :adler32, :processing_id, :storage_id, :retries, :path, :expired_at,
                                    :content_metadata) RETURNING content_id into :content_id
                          """
        stmt = text(insert_coll_sql)
        stmt = stmt.bindparams(outparam("content_id", type_=BigInteger().with_variant(Integer, "sqlite")))
    else:
        insert_coll_sql = """insert into atlas_idds.contents(coll_id, scope, name, min_id, max_id, content_type,
                                                                       status, bytes, md5, adler32, processing_id,
                                                                       storage_id, retries, path, expired_at,
                                                                       content_metadata)
                             values(:coll_id, :scope, :name, :min_id, :max_id, :content_type, :status, :bytes,
                                    :md5, :adler32, :processing_id, :storage_id, :retries, :path, :expired_at,
                                    :content_metadata)
                          """
        stmt = text(insert_coll_sql)

    params = []
    for content in contents:
        param = {}
        for key in default_params:
            if key in content:
                param[key] = content[key]
            else:
                param[key] = default_params[key]

        if isinstance(param['content_type'], ContentType):
            param['content_type'] = param['content_type'].value
        if isinstance(param['status'], ContentStatus):
            param['status'] = param['status'].value
        if param['content_metadata']:
            param['content_metadata'] = json.dumps(param['content_metadata'])
        params.append(param)

    sub_params = [params[i:i + bulk_size] for i in range(0, len(params), bulk_size)]

    try:
        content_ids = None
        if returning_id:
            content_ids = []
            for sub_param in sub_params:
                content_id = None
                sub_param['content_id'] = content_id
                ret = session.execute(stmt, sub_param)
                content_ids.extend(ret.out_parameters['content_id'])
        else:
            for sub_param in sub_params:
                ret = session.execute(stmt, sub_param)
            content_ids = [None for _ in range(len(params))]
        return content_ids
    except IntegrityError as error:
        raise exceptions.DuplicatedObject('Duplicated objects: %s' % (error))
    except DatabaseError as error:
        raise exceptions.DatabaseException(error)


@read_session
def get_content_id(coll_id, scope, name, content_type=None, min_id=None, max_id=None, session=None):
    """
    Get content id or raise a NoObject exception.

    :param coll_id: collection id.
    :param scope: The scope of the request data.
    :param name: The name of the request data.
    :param min_id: The minimal id of the content.
    :param max_id: The maximal id of the content.
    :param content_type: The type of the content.

    :param session: The database session in use.

    :raises NoObject: If no content is founded.

    :returns: Content id.
    """

    try:
        if content_type is not None and isinstance(content_type, ContentType):
            content_type = content_type.value
        if content_type is None:
            select = """select content_id from atlas_idds.contents where coll_id=:coll_id and
                        scope=:scope and name=:name and min_id=:min_id and max_id=:max_id"""
            stmt = text(select)
            result = session.execute(stmt, {'coll_id': coll_id, 'scope': scope, 'name': name,
                                            'min_id': min_id, 'max_id': max_id})
        else:
            if content_type == ContentType.File.value:
                select = """select content_id from atlas_idds.contents where coll_id=:coll_id and
                            scope=:scope and name=:name and content_type=:content_type"""
                stmt = text(select)
                result = session.execute(stmt, {'coll_id': coll_id, 'scope': scope, 'name': name,
                                                'content_type': content_type})
            else:
                select = """select content_id from atlas_idds.contents where coll_id=:coll_id and
                            scope=:scope and name=:name and content_type=:content_type and min_id=:min_id and
                            max_id=:max_id"""
                stmt = text(select)
                result = session.execute(stmt, {'coll_id': coll_id, 'scope': scope, 'name': name,
                                                'content_type': content_type, 'min_id': min_id, 'max_id': max_id})

        content_id = result.fetchone()

        if content_id is None:
            raise exceptions.NoObject('content(coll_id: %s, scope: %s, name: %s, content_type: %s, min_id: %s, max_id: %s) cannot be found' %
                                      (coll_id, scope, name, content_type, min_id, max_id))
        content_id = content_id[0]
        return content_id
    except sqlalchemy.orm.exc.NoResultFound as error:
        raise exceptions.NoObject('content(coll_id: %s, scope: %s, name: %s, content_type: %s, min_id: %s, max_id: %s) cannot be found: %s' %
                                  (coll_id, scope, name, content_type, min_id, max_id, error))
    except Exception as error:
        raise error


@read_session
def get_content(content_id=None, coll_id=None, scope=None, name=None, content_type=None, min_id=None, max_id=None, session=None):
    """
    Get content or raise a NoObject exception.

    :param content_id: Content id.
    :param coll_id: Collection id.
    :param scope: The scope of the request data.
    :param name: The name of the request data.
    :param min_id: The minimal id of the content.
    :param max_id: The maximal id of the content.
    :param content_type: The type of the content.

    :param session: The database session in use.

    :raises NoObject: If no content is founded.

    :returns: Content.
    """

    try:
        if not content_id:
            content_id = get_content_id(coll_id=coll_id, scope=scope, name=name, content_type=content_type, min_id=min_id, max_id=max_id, session=session)
        select = """select * from atlas_idds.contents where content_id=:content_id"""
        stmt = text(select)
        result = session.execute(stmt, {'content_id': content_id})
        content = result.fetchone()

        if content is None:
            raise exceptions.NoObject('content(content_id: %s, coll_id: %s, scope: %s, name: %s, content_type: %s, min_id: %s, max_id: %s) cannot be found' %
                                      (content_id, coll_id, scope, name, content_type, min_id, max_id))

        content = row2dict(content)
        if content['content_type'] is not None:
            content['content_type'] = ContentType(content['content_type'])
        if content['status'] is not None:
            content['status'] = ContentStatus(content['status'])
        if content['content_metadata']:
            content['content_metadata'] = json.loads(content['content_metadata'])

        return content
    except sqlalchemy.orm.exc.NoResultFound as error:
        raise exceptions.NoObject('content(content_id: %s, coll_id: %s, scope: %s, name: %s, content_type: %s, min_id: %s, max_id: %s) cannot be found: %s' %
                                  (content_id, coll_id, scope, name, content_type, min_id, max_id, error))
    except Exception as error:
        raise error


@read_session
def get_match_contents(coll_id, scope, name, content_type=None, min_id=None, max_id=None, session=None):
    """
    Get contents which matches the query or raise a NoObject exception.

    :param coll_id: collection id.
    :param scope: The scope of the request data.
    :param name: The name of the request data.
    :param min_id: The minimal id of the content.
    :param max_id: The maximal id of the content.
    :param content_type: The type of the content.

    :param session: The database session in use.

    :raises NoObject: If no content is founded.

    :returns: list of Content ids.
    """

    try:
        if content_type is not None and isinstance(content_type, ContentType):
            content_type = content_type.value

        if content_type is not None:
            if content_type == ContentType.File.value:
                select = """select * from atlas_idds.contents where coll_id=:coll_id and
                            scope=:scope and name=:name and content_type=:content_type"""
                stmt = text(select)
                result = session.execute(stmt, {'coll_id': coll_id, 'scope': scope, 'name': name,
                                                'content_type': content_type})
            else:
                select = """select * from atlas_idds.contents where coll_id=:coll_id and
                            scope=:scope and name=:name and content_type=:content_type
                            and min_id<=:min_id and max_id>=:max_id"""
                stmt = text(select)
                result = session.execute(stmt, {'coll_id': coll_id, 'scope': scope, 'name': name,
                                                'content_type': content_type, 'min_id': min_id,
                                                'max_id': max_id})
        else:
            if min_id is None or max_id is None:
                select = """select * from atlas_idds.contents where coll_id=:coll_id and
                            scope=:scope and name=:name"""
                stmt = text(select)
                result = session.execute(stmt, {'coll_id': coll_id, 'scope': scope, 'name': name})
            else:
                select = """select * from atlas_idds.contents where coll_id=:coll_id and
                            scope=:scope and name=:name and min_id<=:min_id and max_id>=:max_id"""
                stmt = text(select)
                result = session.execute(stmt, {'coll_id': coll_id, 'scope': scope, 'name': name,
                                                'min_id': min_id, 'max_id': max_id})

        contents = result.fetchall()
        rets = []
        for content in contents:
            content = row2dict(content)
            if content['content_type'] is not None:
                content['content_type'] = ContentType(content['content_type'])
            if content['status'] is not None:
                content['status'] = ContentStatus(content['status'])
            if content['content_metadata']:
                content['content_metadata'] = json.loads(content['content_metadata'])
            rets.append(content)
        return rets
    except sqlalchemy.orm.exc.NoResultFound as error:
        raise exceptions.NoObject('No match contents for (coll_id: %s, scope: %s, name: %s, content_type: %s, min_id: %s, max_id: %s): %s' %
                                  (coll_id, scope, name, content_type, min_id, max_id, error))
    except Exception as error:
        raise error


@read_session
def get_contents(scope=None, name=None, coll_id=None, status=None, session=None):
    """
    Get content or raise a NoObject exception.

    :param scope: The scope of the content data.
    :param name: The name of the content data.
    :param coll_id: Collection id.

    :param session: The database session in use.

    :raises NoObject: If no content is founded.

    :returns: list of contents.
    """

    try:
        if status is not None:
            if not isinstance(status, (tuple, list)):
                status = [status]
            new_status = []
            for st in status:
                if isinstance(st, ContentStatus):
                    new_status.append(st.value)
                else:
                    new_status.append(st)
            status = new_status

        if scope and name:
            if coll_id:
                if status is not None:
                    select = """select * from atlas_idds.contents where coll_id=:coll_id and
                                scope=:scope and name like :name and status in :status"""
                    stmt = text(select)
                    stmt = stmt.bindparams(bindparam('status', expanding=True))
                    result = session.execute(stmt, {'coll_id': coll_id, 'scope': scope, 'name': '%' + name + '%', 'status': status})
                else:
                    select = """select * from atlas_idds.contents where coll_id=:coll_id and
                                scope=:scope and name like :name"""
                    stmt = text(select)
                    result = session.execute(stmt, {'coll_id': coll_id, 'scope': scope, 'name': '%' + name + '%'})
            else:
                if status is not None:
                    select = """select * from atlas_idds.contents where scope=:scope and name like :name and status in :status"""
                    stmt = text(select)
                    stmt = stmt.bindparams(bindparam('status', expanding=True))
                    result = session.execute(stmt, {'scope': scope, 'name': '%' + name + '%', 'status': status})
                else:
                    select = """select * from atlas_idds.contents where scope=:scope and name like :name"""
                    stmt = text(select)
                    result = session.execute(stmt, {'scope': scope, 'name': '%' + name + '%'})
        else:
            if coll_id:
                if status is not None:
                    select = """select * from atlas_idds.contents where coll_id=:coll_id and status in :status"""
                    stmt = text(select)
                    stmt = stmt.bindparams(bindparam('status', expanding=True))
                    result = session.execute(stmt, {'coll_id': coll_id, 'status': status})
                else:
                    select = """select * from atlas_idds.contents where coll_id=:coll_id"""
                    stmt = text(select)
                    result = session.execute(stmt, {'coll_id': coll_id})
            else:
                if status is not None:
                    select = """select * from atlas_idds.contents where status in :status"""
                    stmt = text(select)
                    stmt = stmt.bindparams(bindparam('status', expanding=True))
                    result = session.execute(stmt, {'status': status})
                else:
                    raise exceptions.WrongParameterException("Both (scope:%s and name:%s) and coll_id:%s status:%s are not fully provided" %
                                                             (scope, name, coll_id, status))

        contents = result.fetchall()
        rets = []
        for content in contents:
            content = row2dict(content)
            if content['content_type'] is not None:
                content['content_type'] = ContentType(content['content_type'])
            if content['status'] is not None:
                content['status'] = ContentStatus(content['status'])
            if content['content_metadata']:
                content['content_metadata'] = json.loads(content['content_metadata'])
            rets.append(content)
        return rets
    except sqlalchemy.orm.exc.NoResultFound as error:
        raise exceptions.NoObject('No record can be found with (scope=%s, name=%s, coll_id=%s): %s' %
                                  (scope, name, coll_id, error))
    except Exception as error:
        raise error


@read_session
def get_content_status_statistics(coll_id=None, session=None):
    """
    Get statistics group by status

    :param coll_id: Collection id.
    :param session: The database session in use.

    :returns: statistics group by status, as a dict.
    """
    try:
        if coll_id:
            sql = "select status, count(*) from atlas_idds.contents where coll_id=:coll_id group by status"
            stmt = text(sql)
            result = session.execute(stmt, {'coll_id': coll_id})
        else:
            sql = "select status, count(*) from atlas_idds.contents group by status"
            stmt = text(sql)
            result = session.execute(stmt)
        rets = {}
        for status, count in result:
            status = ContentStatus(status)
            rets[status] = count
        return rets
    except Exception as error:
        raise error


@transactional_session
def update_content(content_id, parameters, session=None):
    """
    update a content.

    :param content_id: the content id.
    :param parameters: A dictionary of parameters.
    :param session: The database session in use.

    :raises NoObject: If no content is founded.
    :raises DatabaseException: If there is a database error.

    """
    try:
        if 'content_type' in parameters and isinstance(parameters['content_type'], ContentType):
            parameters['content_type'] = parameters['content_type'].value
        if 'status' in parameters and isinstance(parameters['status'], ContentStatus):
            parameters['status'] = parameters['status'].value
        if 'content_metadata' in parameters:
            parameters['content_metadata'] = json.dumps(parameters['content_metadata'])

        parameters['updated_at'] = datetime.datetime.utcnow()

        update = "update atlas_idds.contents set "
        for key in parameters.keys():
            update += key + "=:" + key + ","
        update = update[:-1]
        update += " where content_id=:content_id"

        stmt = text(update)
        parameters['content_id'] = content_id
        session.execute(stmt, parameters)
    except sqlalchemy.orm.exc.NoResultFound as error:
        raise exceptions.NoObject('Content %s cannot be found: %s' % (content_id, error))


@transactional_session
def update_contents(parameters, with_content_id=False, session=None):
    """
    updatecontents.

    :param parameters: list of dictionary of parameters.
    :param with_content_id: whether content_id is included.
    :param session: The database session in use.

    :raises NoObject: If no content is founded.
    :raises DatabaseException: If there is a database error.

    """
    try:
        if with_content_id:
            keys = ['content_id', 'status', 'path']
            update = """update atlas_idds.contents set path=:path, updated_at=:updated_at, status=:status
                        where content_id=:content_id"""
        else:
            keys = ['coll_id', 'scope', 'name', 'min_id', 'max_id', 'status', 'path']
            update = """update atlas_idds.contents set path=:path, updated_at=:updated_at, status=:status
                        where coll_id=:coll_id and scope=:scope and name=:name and min_id=:min_id and max_id=:max_id"""
        stmt = text(update)

        contents = []
        for parameter in parameters:
            content = {}
            for key in keys:
                if key in parameter:
                    content[key] = parameter[key]
                else:
                    content[key] = None
            if content['status'] is not None and isinstance(content['status'], ContentStatus):
                content['status'] = content['status'].value
            content['updated_at'] = datetime.datetime.utcnow()
            contents.append(content)
        session.execute(stmt, contents)
    except sqlalchemy.orm.exc.NoResultFound as error:
        raise exceptions.NoObject('Content cannot be found: %s' % (error))


@transactional_session
def delete_content(content_id=None, session=None):
    """
    delete a content.

    :param content_id: The id of the content.
    :param session: The database session in use.

    :raises NoObject: If no content is founded.
    :raises DatabaseException: If there is a database error.
    """
    try:
        delete = "delete from atlas_idds.contents where content_id=:content_id"
        stmt = text(delete)
        session.execute(stmt, {'content_id': content_id})
    except sqlalchemy.orm.exc.NoResultFound as error:
        raise exceptions.NoObject('Content %s cannot be found: %s' % (content_id, error))
