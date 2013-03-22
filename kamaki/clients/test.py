# Copyright 2013 GRNET S.A. All rights reserved.
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

from mock import patch, call
from unittest import makeSuite, TestSuite, TextTestRunner, TestCase
from time import sleep
from inspect import getmembers, isclass
from itertools import product
from random import randint

from kamaki.clients.connection.test import (
    KamakiConnection,
    KamakiHTTPConnection,
    KamakiResponse,
    KamakiHTTPResponse)
from kamaki.clients.utils.test import Utils
from kamaki.clients.astakos.test import AstakosClient
from kamaki.clients.compute.test import ComputeClient, ComputeRestClient
from kamaki.clients.cyclades.test import CycladesClient
from kamaki.clients.cyclades.test import CycladesRestClient
from kamaki.clients.image.test import ImageClient
from kamaki.clients.storage.test import StorageClient
from kamaki.clients.pithos.test import PithosClient, PithosRestClient


class ClientError(TestCase):

    def test___init__(self):
        from kamaki.clients import ClientError
        for msg, status, details, exp_msg, exp_status, exp_details in (
                ('some msg', 42, 0.28, 0, 0, 0),
                ('some msg', 'fail', [], 0, 0, 0),
                ('some msg', 42, 'details on error', 0, 0, 0),
                (
                    '404 {"ExampleError":'
                    ' {"message": "a msg", "code": 42, "details": "dets"}}',
                    404,
                    0,
                    '404 ExampleError (a msg)\n',
                    42,
                    ['dets']),
                (
                    '404 {"ExampleError":'
                    ' {"message": "a msg", "code": 42}}',
                    404,
                    'details on error',
                    '404 ExampleError (a msg)\n',
                    42,
                    0),
                (
                    '404 {"ExampleError":'
                    ' {"details": "Explain your error"}}',
                    404,
                    'details on error',
                    '404 ExampleError',
                    0,
                    ['details on error', 'Explain your error']),
                ('some msg\n', -10, ['details', 'on', 'error'], 0, 0, 0)):
            ce = ClientError(msg, status, details)
            exp_msg = exp_msg or (msg if msg.endswith('\n') else msg + '\n')
            exp_status = exp_status or status
            exp_details = exp_details or details
            self.assertEqual('%s' % ce, exp_msg)
            self.assertEqual(
                exp_status if isinstance(exp_status, int) else 0,
                ce.status)
            self.assertEqual(exp_details, ce.details)


class SilentEvent(TestCase):

    def thread_content(self, methodid, raiseException=0):
        wait = 0.1
        self.can_finish = -1
        while self.can_finish < methodid and wait < 4:
            sleep(wait)
            wait = 2 * wait
        if raiseException and raiseException == methodid:
            raise Exception('Some exception')
        self._value = methodid
        self.assertTrue(wait < 4)

    def setUp(self):
        from kamaki.clients import SilentEvent
        self.SE = SilentEvent

    def test_run(self):
        threads = [self.SE(self.thread_content, i) for i in range(4)]
        for t in threads:
            t.start()

        for i in range(4):
            self.assertTrue(threads[i].is_alive())
            self.can_finish = i
            threads[i].join()
            self.assertFalse(threads[i].is_alive())

    def test_value(self):
        threads = [self.SE(self.thread_content, i) for i in range(4)]
        for t in threads:
            t.start()

        for mid, t in enumerate(threads):
            if t.is_alive():
                self.can_finish = mid
                continue
            self.assertTrue(mid, t.value)

    def test_exception(self):
        threads = [self.SE(self.thread_content, i, (i % 2)) for i in range(4)]
        for t in threads:
            t.start()

        for i, t in enumerate(threads):
            if t.is_alive():
                self.can_finish = i
                continue
            if i % 2:
                self.assertTrue(isinstance(t.exception, Exception))
            else:
                self.assertFalse(t.exception)


class FR(object):
    json = None
    text = None
    headers = dict()
    content = json
    status = None
    status_code = 200

    def release(self):
        pass


class FakeConnection(object):
    """A fake Connection class"""

    headers = dict()
    params = dict()

    def __init__(self):
        pass

    def set_header(self, name, value):
        pass

    def reset_headers(self):
        self.headers = {}

    def set_param(self, name, value):
        self.params = {}

    def reset_params(self):
        pass

    def perform_request(self, *args):
        return FR()


class Client(TestCase):

    def assert_dicts_are_equal(self, d1, d2):
        for k, v in d1.items():
            self.assertTrue(k in d2)
            if isinstance(v, dict):
                self.assert_dicts_are_equal(v, d2[k])
            else:
                self.assertEqual(unicode(v), unicode(d2[k]))

    def setUp(self):
        from kamaki.clients import Client
        from kamaki.clients import ClientError as CE
        self.base_url = 'http://example.com'
        self.token = 's0m370k3n=='
        self.client = Client(self.base_url, self.token, FakeConnection())
        self.CE = CE

    def tearDown(self):
        FR.text = None
        FR.status = None
        FR.status_code = 200
        FakeConnection.headers = dict()
        self.client.token = self.token

    def test___init__(self):
        self.assertEqual(self.client.base_url, self.base_url)
        self.assertEqual(self.client.token, self.token)
        self.assert_dicts_are_equal(self.client.headers, {})
        DATE_FORMATS = [
            '%a %b %d %H:%M:%S %Y',
            '%A, %d-%b-%y %H:%M:%S GMT',
            '%a, %d %b %Y %H:%M:%S GMT']
        self.assertEqual(self.client.DATE_FORMATS, DATE_FORMATS)
        self.assertTrue(isinstance(self.client.http_client, FakeConnection))

    def test__init_thread_limit(self):
        exp = 'Nothing set here'
        for faulty in (-1, 0.5, 'a string', {}):
            self.assertRaises(
                AssertionError,
                self.client._init_thread_limit,
                faulty)
            self.assertEqual(exp, getattr(self.client, '_thread_limit', exp))
            self.assertEqual(exp, getattr(self.client, '_elapsed_old', exp))
            self.assertEqual(exp, getattr(self.client, '_elapsed_new', exp))
        self.client._init_thread_limit(42)
        self.assertEqual(42, self.client._thread_limit)
        self.assertEqual(0.0, self.client._elapsed_old)
        self.assertEqual(0.0, self.client._elapsed_new)

    def test__watch_thread_limit(self):
        waits = (
            dict(args=((0.1, 1), (0.1, 2), (0.2, 1), (0.7, 1), (0.3, 2))),
            dict(args=((1.0 - (i / 10.0), (i + 1)) for i in range(7))),
            dict(max=1, args=tuple([(randint(1, 10) / 3.0, 1), ] * 10)),
            dict(
                limit=5,
                args=tuple([
                    (1.0 + (i / 10.0), (5 - i - 1)) for i in range(4)] + [
                    (2.0, 1), (1.9, 2), (2.0, 1), (2.0, 2)])),
            dict(args=tuple(
                [(1.0 - (i / 10.0), (i + 1)) for i in range(7)] + [
                (0.1, 7), (0.2, 6), (0.4, 5), (0.3, 6), (0.2, 7), (0.1, 7)])),)
        for wait_dict in waits:
            if 'max' in wait_dict:
                self.client.MAX_THREADS = wait_dict['max']
            else:
                self.client.MAX_THREADS = 7
            if 'limit' in wait_dict:
                self.client._init_thread_limit(wait_dict['limit'])
            else:
                self.client._init_thread_limit()
                self.client._watch_thread_limit(list())
                self.assertEqual(1, self.client._thread_limit)
            for wait, exp_limit in wait_dict['args']:
                self.client._elapsed_new = wait
                self.client._watch_thread_limit(list())
                self.assertEqual(exp_limit, self.client._thread_limit)

    def test__raise_for_status(self):
        r = FR()
        for txt, sts_code, sts in (('err msg', 10, None), ('', 42, 'Err St')):
            r.text, r.status_code, r.status = txt, sts_code, sts
            try:
                self.client._raise_for_status(r)
            except self.CE as ce:
                self.assertEqual('%s' % ce, '%s %s\n' % (sts or '', txt))
                self.assertEqual(ce.status, sts_code)

        for msg, sts_code in (('err msg', 32), ('', 42), ('an err', None)):
            err = self.CE(msg, sts_code) if sts_code else Exception(msg)
            try:
                self.client._raise_for_status(err)
            except self.CE as ce:
                self.assertEqual('%s' % ce, '%s %s\n' % (sts_code or '', msg))
                self.assertEqual(ce.status, sts_code or 0)

    @patch('%s.FakeConnection.set_header' % __name__)
    def test_set_header(self, SH):
        num_of_calls = 0
        for name, value, condition in product(
                ('n4m3', '', None),
                ('v41u3', None, 42),
                (True, False, None, 1, '')):
            self.client.set_header(name, value, iff=condition)
            if value is not None and condition:
                self.assertEqual(SH.mock_calls[-1], call(name, value))
                num_of_calls += 1
            else:
                self.assertEqual(num_of_calls, len(SH.mock_calls))

    @patch('%s.FakeConnection.set_param' % __name__)
    def test_set_param(self, SP):
        num_of_calls = 0
        for name, value, condition in product(
                ('n4m3', '', None),
                ('v41u3', None, 42),
                (True, False, None, 1, '')):
            self.client.set_param(name, value, iff=condition)
            if condition:
                self.assertEqual(SP.mock_calls[-1], call(name, value))
                num_of_calls += 1
            else:
                self.assertEqual(num_of_calls, len(SP.mock_calls))

    @patch('%s.FakeConnection.perform_request' % __name__, return_value=FR())
    def test_request(self, PR):
        for args in product(
                ('get', '', dict(method='get')),
                ('/some/path', None, ['some', 'path']),
                (dict(), dict(h1='v1'), dict(h1='v2', h2='v2')),
                (dict(), dict(p1='v1'), dict(p1='v2', p2=None, p3='v3')),
                (dict(), dict(data='some data'), dict(
                    success=400,
                    json=dict(k2='v2', k1='v1')))):
            method, path, kwargs = args[0], args[1], args[-1]
            args = args[:-1]
            if not (isinstance(method, str) and method and isinstance(
                    path, str) and path):
                self.assertRaises(
                    AssertionError,
                    self.client.request,
                    *args, **kwargs)
            else:
                atoken = 'a70k3n_%s' % randint(1, 30)
                self.client.token = atoken
                if 'success' in kwargs:
                    self.assertRaises(
                        self.CE,
                        self.client.request,
                        *args, **kwargs)
                    FR.status_code = kwargs['success']
                else:
                    FR.status_code = 200
                self.client.request(*args, **kwargs)
                data = kwargs.get(
                    'data',
                    '{"k2": "v2", "k1": "v1"}' if 'json' in kwargs else None)
                self.assertEqual(self.client.http_client.url, self.base_url)
                self.assertEqual(self.client.http_client.path, path)
                self.assertEqual(
                    PR.mock_calls[-1],
                    call(method, data, *args[2:]))
                self.assertEqual(self.client.http_client.headers, dict())
                self.assertEqual(self.client.http_client.params, dict())

    @patch('kamaki.clients.Client.request', return_value='lala')
    def _test_foo(self, foo, request):
        method = getattr(self.client, foo)
        r = method('path', k='v')
        self.assertEqual(r, 'lala')
        request.assert_called_once_with(foo, 'path', k='v')

    def test_delete(self):
        self._test_foo('delete')

    def test_get(self):
        self._test_foo('get')

    def test_head(self):
        self._test_foo('head')

    def test_post(self):
        self._test_foo('post')

    def test_put(self):
        self._test_foo('put')

    def test_copy(self):
        self._test_foo('copy')

    def test_move(self):
        self._test_foo('move')


#  TestCase auxiliary methods

def runTestCase(cls, test_name, args=[], failure_collector=[]):
    """
    :param cls: (TestCase) a set of Tests

    :param test_name: (str)

    :param args: (list) these are prefixed with test_ and used as params when
        instantiating cls

    :param failure_collector: (list) collects info of test failures

    :returns: (int) total # of run tests
    """
    suite = TestSuite()
    if args:
        suite.addTest(cls('_'.join(['test'] + args)))
    else:
        suite.addTest(makeSuite(cls))
    print('* Test * %s *' % test_name)
    r = TextTestRunner(verbosity=2).run(suite)
    failure_collector += r.failures
    return r.testsRun


def _add_value(foo, value):
    def wrap(self):
        return foo(self, value)
    return wrap


def get_test_classes(module=__import__(__name__), name=''):
    module_stack = [module]
    while module_stack:
        module = module_stack[-1]
        module_stack = module_stack[:-1]
        for objname, obj in getmembers(module):
            if (objname == name or not name):
                if isclass(obj) and objname != 'TestCase' and (
                        issubclass(obj, TestCase)):
                    yield (obj, objname)


def main(argv):
    found = False
    failure_collector = list()
    num_of_tests = 0
    for cls, name in get_test_classes(name=argv[1] if len(argv) > 1 else ''):
        found = True
        num_of_tests += runTestCase(cls, name, argv[2:], failure_collector)
    if not found:
        print('Test "%s" not found' % ' '.join(argv[1:]))
    else:
        for i, failure in enumerate(failure_collector):
            print('Failure %s: ' % (i + 1))
            for field in failure:
                print('\t%s' % field)
        print('\nTotal tests run: %s' % num_of_tests)
        print('Total failures: %s' % len(failure_collector))


if __name__ == '__main__':
    from sys import argv
    main(argv)
