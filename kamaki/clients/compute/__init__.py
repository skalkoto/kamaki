# Copyright 2011-2013 GRNET S.A. All rights reserved.
#
# Redistribution and use in source and binary forms, with or
# without modification, are permitted provided that the following
# conditions are met:
#
#   1. Redistributions of source code must retain the above
#      copyright notice, this list of conditions and the following
#      disclaimer.
#
#   2. Redistributions in binary form must reproduce the above
#      copyright notice, this list of conditions and the following
#      disclaimer in the documentation and/or other materials
#      provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY GRNET S.A. ``AS IS'' AND ANY EXPRESS
# OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
# PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL GRNET S.A OR
# CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF
# USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED
# AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
#
# The views and conclusions contained in the software and
# documentation are those of the authors and should not be
# interpreted as representing official policies, either expressed
# or implied, of GRNET S.A.

from kamaki.clients import ClientError
from kamaki.clients.compute.rest_api import ComputeRestClient
from kamaki.clients.utils import path4url


class ComputeClient(ComputeRestClient):
    """OpenStack Compute API 1.1 client"""

    def list_servers(
            self,
            detail=False,
            changes_since=None,
            image=None,
            flavor=None,
            name=None,
            marker=None,
            limit=None,
            status=None,
            host=None,
            response_headers=dict(previous=None, next=None)):
        """
        :param detail: if true, append full server details to each item

        :param response_headers: (dict) use it to get previous/next responses
            Keep the existing dict format to actually get the server responses
            Use it with very long lists or with marker

        :returns: list of server ids and names
        """
        r = self.servers_get(
            detail=bool(detail),
            changes_since=changes_since,
            image=image,
            flavor=flavor,
            name=name,
            marker=marker,
            limit=limit,
            status=status,
            host=host)
        for k, v in response_headers.items():
            response_headers[k] = r.headers.get(k, v)
        return r.json['servers']

    def get_server_details(
            self, server_id,
            changes_since=None,
            image=None,
            flavor=None,
            name=None,
            marker=None,
            limit=None,
            status=None,
            host=None,
            response_headers=dict(previous=None, next=None),
            **kwargs):
        """Return detailed info for a server

        :param server_id: integer (int or str)

        :returns: dict with server details
        """
        r = self.servers_get(
            server_id,
            changes_since=changes_since,
            image=image,
            flavor=flavor,
            name=name,
            marker=marker,
            limit=limit,
            status=status,
            host=host,
            **kwargs)
        for k, v in response_headers.items():
            response_headers[k] = r.headers.get(k, v)
        return r.json['server']

    def create_server(
            self, name, flavor_id, image_id,
            security_group=None,
            user_data=None,
            availability_zone=None,
            server=None,
            metadata=None,
            personality=None,
            response_headers=dict(location=None)):
        """Submit request to create a new server

        :param name: (str)

        :param flavor_id: integer id denoting a preset hardware configuration

        :param image_id: (str) id denoting the OS image to run on the VM

        :param metadata: (dict) vm metadata

        :param personality: a list of (file path, file contents) tuples,
            describing files to be injected into VM upon creation.

        :returns: a dict with the new VMs details

        :raises ClientError: wraps request errors
        """
        req = {'server': {
            'name': name, 'flavorRef': flavor_id, 'imageRef': image_id}}

        if metadata:
            req['server']['metadata'] = metadata

        if personality:
            req['server']['personality'] = personality

        r = self.servers_post(
            json_data=req,
            security_group=security_group,
            user_data=user_data,
            availability_zone=availability_zone)
        for k, v in response_headers.items():
            response_headers[k] = r.headers.get(k, v)
        return r.json['server']

    def update_server_name(self, server_id, new_name):
        """Update the name of the server as reported by the API (does not
            modify the hostname used inside the VM)

        :param server_id: integer (str or int)

        :param new_name: (str)

        :returns: (dict) response headers
        """
        req = {'server': {'name': new_name}}
        r = self.servers_put(server_id, json_data=req)
        return r.headers

    def delete_server(self, server_id):
        """Submit a deletion request for a server specified by id

        :param server_id: integer (str or int)

        :returns: (dict) response headers
        """
        r = self.servers_delete(server_id)
        return r.headers

    def reboot_server(self, server_id, hard=False):
        """
        :param server_id: integer (str or int)

        :param hard: perform a hard reboot if true, soft reboot otherwise
        """
        boot_type = 'HARD' if hard else 'SOFT'
        req = {'reboot': {'type': boot_type}}
        r = self.servers_post(server_id, 'action', json_data=req)
        return r.headers

    def resize_server(self, server_id, flavor_id):
        """
        :param server_id: (str)

        :param flavor_id: (int)

        :returns: (dict) request headers
        """
        req = {'resize': {'flavorRef': flavor_id}}
        r = self.servers_post(server_id, 'action', json_data=req)
        return r.headers

    def get_server_metadata(self, server_id, key='', response_headers=dict(
            previous=None, next=None)):
        """
        :param server_id: integer (str or int)

        :param key: (str) the metadatum key (all metadata if not given)

        :returns: a key:val dict of requests metadata
        """
        r = self.servers_metadata_get(server_id, key)
        for k, v in response_headers.items():
            response_headers[k] = r.headers.get(k, v)
        return r.json['meta' if key else 'metadata']

    def create_server_metadata(self, server_id, key, val):
        """
        :param server_id: integer (str or int)

        :param key: (str)

        :param val: (str)

        :returns: dict of updated key:val metadata
        """
        req = {'meta': {key: val}}
        r = self.servers_put(server_id, key, json_data=req, success=201)
        return r.json['meta']

    def update_server_metadata(
            self, server_id,
            response_headers=dict(previous=None, next=None), **metadata):
        """
        :param server_id: integer (str or int)

        :param metadata: dict of key:val metadata

        :returns: dict of updated key:val metadata
        """
        req = {'metadata': metadata}
        r = self.servers_post(server_id, json_data=req, success=201)
        for k, v in response_headers.items():
            response_headers[k] = r.headers.get(k, v)
        return r.json['metadata']

    def delete_server_metadata(self, server_id, key):
        """
        :param server_id: integer (str or int)

        :param key: (str) the meta key

        :returns: (dict) response headers
        """
        r = self.servers_delete(server_id, key)
        return r.headers

    def list_flavors(self, detail=False):
        """
        :param detail: (bool) detailed flavor info if set, short if not

        :returns: (list) flavor info
        """
        r = self.flavors_get(command='detail' if detail else '')
        return r.json['flavors']

    def get_flavor_details(self, flavor_id):
        """
        :param flavor_id: integer (str or int)

        :returns: dict
        """
        r = self.flavors_get(flavor_id)
        return r.json['flavor']

    def list_images(self, detail=False):
        """
        :param detail: (bool) detailed info if set, short if not

        :returns: dict id,name + full info if detail
        """
        detail = 'detail' if detail else ''
        r = self.images_get(command=detail)
        return r.json['images']

    def get_image_details(self, image_id, **kwargs):
        """
        :param image_id: integer (str or int)

        :returns: dict

        :raises ClientError: 404 if image not available
        """
        r = self.images_get(image_id, **kwargs)
        try:
            return r.json['image']
        except KeyError:
            raise ClientError('Image not available', 404, details=[
                'Image %d not found or not accessible'])

    def delete_image(self, image_id):
        """
        :param image_id: (str)
        """
        r = self.images_delete(image_id)
        return r.headers

    def get_image_metadata(self, image_id, key=''):
        """
        :param image_id: (str)

        :param key: (str) the metadatum key

        :returns (dict) metadata if key not set, specific metadatum otherwise
        """
        command = path4url('metadata', key)
        r = self.images_get(image_id, command)
        return r.json['meta' if key else 'metadata']

    def create_image_metadata(self, image_id, key, val):
        """
        :param image_id: integer (str or int)

        :param key: (str) metadatum key

        :param val: (str) metadatum value

        :returns: (dict) updated metadata
        """
        req = {'meta': {key: val}}
        r = self.images_put(image_id, 'metadata/' + key, json_data=req)
        return r.json['meta']

    def update_image_metadata(self, image_id, **metadata):
        """
        :param image_id: (str)

        :param metadata: dict

        :returns: updated metadata
        """
        req = {'metadata': metadata}
        r = self.images_post(image_id, 'metadata', json_data=req)
        return r.json['metadata']

    def delete_image_metadata(self, image_id, key):
        """
        :param image_id: (str)

        :param key: (str) metadatum key

        :returns: (dict) response headers
        """
        command = path4url('metadata', key)
        r = self.images_delete(image_id, command)
        return r.headers

    def get_floating_ip_pools(self, tenant_id):
        """
        :param tenant_id: (str)

        :returns: (dict) {floating_ip_pools:[{name: ...}, ...]}
        """
        r = self.floating_ip_pools_get(tenant_id)
        return r.json

    def get_floating_ips(self, tenant_id):
        """
        :param tenant_id: (str)

        :returns: (dict) {floating_ips:[
            {fixed_ip: ..., id: ..., instance_id: ..., ip: ..., pool: ...},
            ... ]}
        """
        r = self.floating_ips_get(tenant_id)
        return r.json

    def alloc_floating_ip(self, tenant_id, pool=None):
        """
        :param tenant_id: (str)

        :param pool: (str) pool of ips to allocate from

        :returns: (dict) {fixed_ip: . id: . instance_id: . ip: . pool: .}
        """
        json_data = dict(pool=pool) if pool else dict()
        r = self.floating_ips_post(tenant_id, json_data)
        return r.json['floating_ip']

    def get_floating_ip(self, tenant_id, fip_id=None):
        """
        :param tenant_id: (str)

        :param fip_id: (str) floating ip id (if None, all ips are returned)

        :returns: (list) [
            {fixed_ip: ..., id: ..., instance_id: ..., ip: ..., pool: ...},
            ... ]
        """
        r = self.floating_ips_get(tenant_id, fip_id)
        return r.json['floating_ips']

    def delete_floating_ip(self, tenant_id, fip_id=None):
        """
        :param tenant_id: (str)

        :param fip_id: (str) floating ip id (if None, all ips are deleted)

        :returns: (dict) request headers
        """
        r = self.floating_ips_delete(tenant_id, fip_id)
        return r.headers
