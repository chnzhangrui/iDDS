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


from idds.common import exceptions
from idds.common.constants import RequestStatus, RequestLocking
from idds.orm.base.session import transactional_session
from idds.orm import requests as orm_requests
from idds.orm import transforms as orm_transforms
from idds.orm import collections as orm_collections


@transactional_session
def add_request(scope, name, requester=None, request_type=None, transform_tag=None,
                status=RequestStatus.New, locking=RequestLocking.Idle, priority=0,
                lifetime=30, workload_id=None, request_metadata=None,
                processing_metadata=None, session=None):
    """
    Add a request.

    :param scope: The scope of the request data.
    :param name: The name of the request data.
    :param requestr: The requester, such as panda, user and so on.
    :param request_type: The type of the request, such as ESS, DAOD.
    :param transform_tag: Transform tag, such as ATLAS AMI tag.
    :param status: The request status as integer.
    :param locking: The request locking as integer.
    :param priority: The priority as integer.
    :param lifetime: The life time as umber of days.
    :param workload_id: The external workload id.
    :param request_metadata: The metadata as json.
    :param processing_metadata: The metadata as json.

    :returns: request id.
    """
    kwargs = {'scope': scope, 'name': name, 'requester': requester, 'request_type': request_type,
              'transform_tag': transform_tag, 'status': status, 'locking': locking,
              'priority': priority, 'lifetime': lifetime, 'workload_id': workload_id,
              'request_metadata': request_metadata, 'processing_metadata': processing_metadata,
              'session': session}
    if request_metadata and 'workload_id' in request_metadata:
        kwargs['workload_id'] = int(request_metadata['workload_id'])
    return orm_requests.add_request(**kwargs)


def get_request(request_id=None, workload_id=None):
    """
    Get a request or raise a NoObject exception.

    :param request_id: The id of the request.
    :param workload_id: The workload_id of the request.

    :raises NoObject: If no request is founded.

    :returns: Request.
    """
    return orm_requests.get_request(request_id=request_id, workload_id=workload_id)


def extend_request(request_id=None, workload_id=None, lifetime=30):
    """
    extend an request's lifetime.

    :param request_id: The id of the request.
    :param workload_id: The workload_id of the request.
    :param lifetime: The life time as umber of days.
    """
    return orm_requests.extend_request(request_id=request_id, workload_id=workload_id, lifetime=lifetime)


def cancel_request(request_id=None, workload_id=None):
    """
    cancel an request.

    :param request_id: The id of the request.
    :param workload_id: The workload_id of the request.
    """
    return orm_requests.cancel_request(request_id=request_id, workload_id=workload_id)


def update_request(request_id, parameters):
    """
    update an request.

    :param request_id: the request id.
    :param parameters: A dictionary of parameters.
    """
    return orm_requests.update_request(request_id, parameters)


@transactional_session
def update_request_with_transforms(request_id, parameters, transforms_to_add, transforms_to_extend, session=None):
    """
    update an request.

    :param request_id: the request id.
    :param parameters: A dictionary of parameters.
    :param transforms_to_add: list of transforms
    :param transforms_to_extend: list of transforms
    """
    for transform in transforms_to_add:
        if 'collections' not in transform or len(transform['collections']) == 0:
            msg = "Transform must have collections, such as input collection, output collection and log collection"
            raise exceptions.WrongParameterException(msg)

        collections = transform['collections']
        del transform['collections']
        transform_id = orm_transforms.add_transform(**transform, session=session)

        input_coll_ids = []
        log_coll_ids = []
        for collection in collections['input_collections']:
            collection['transform_id'] = transform_id
            input_coll_id = orm_collections.add_collection(**collection, session=session)
            input_coll_ids.append(input_coll_id)
        for collection in collections['log_collections']:
            collection['transform_id'] = transform_id
            log_coll_id = orm_collections.add_collection(**collection, session=session)
            log_coll_ids.append(log_coll_id)
        for collection in collections['output_collections']:
            collection['transform_id'] = transform_id
            workload_id = transform['transform_metadata']['workload_id'] if 'workload_id' in transform['transform_metadata'] else None
            collection['coll_metadata'] = {'transform_id': transform_id,
                                           'workload_id': workload_id,
                                           'input_collections': input_coll_ids,
                                           'log_collections': log_coll_ids}
            orm_collections.add_collection(**collection, session=session)

    for transform in transforms_to_extend:
        transform_id = transform['transform_id']
        del transform['transform_id']
        # orm_transforms.add_req2transform(request_id, transform_id, session=session)
        orm_transforms.update_transform(transform_id, parameters=transform, session=session)
    return orm_requests.update_request(request_id, parameters, session=session)


@transactional_session
def get_requests_by_status_type(status, request_type=None, time_period=None, locking=False, bulk_size=None, session=None):
    """
    Get requests by status and type

    :param status: list of status of the request data.
    :param request_type: The type of the request data.
    :param time_period: Delay of seconds before last update.
    :param locking: Wheter to lock requests to avoid others get the same request.
    :param bulk_size: Size limitation per retrieve.

    :returns: list of Request.
    """
    reqs = orm_requests.get_requests_by_status_type(status, request_type, time_period, locking=locking, bulk_size=bulk_size, session=session)
    if locking:
        parameters = {'locking': RequestLocking.Locking}
        for req in reqs:
            orm_requests.update_request(request_id=req['request_id'], parameters=parameters, session=session)
    return reqs


@transactional_session
def clean_locking(time_period=3600, session=None):
    """
    Clearn locking which is older than time period.

    :param time_period in seconds
    """
    orm_requests.clean_locking(time_period=time_period, session=session)
