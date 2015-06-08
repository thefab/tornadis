import argparse
import datetime
import itertools
import math
import sys
import tornadis
import tornado
from six import print_
import six


def get_parameters():
    parser = argparse.ArgumentParser(
        description='Tornadis benchmarking utility', add_help=False)
    parser.add_argument('--help', action='help')
    parser.add_argument('-h', '--hostname',
                        help="Server hostname (default 127.0.0.1)",
                        default="127.0.0.1")
    parser.add_argument('-p', '--port', help="Server port (default 6379)",
                        default=6379)
    parser.add_argument('-u', '--unix_domain_socket',
                        help="path to a unix socket to connect to (if set "
                        ", overrides host/port parameters)")
    parser.add_argument('-a', '--password', help="Password for Redis Auth")
    parser.add_argument('-c', '--clients',
                        help="Number of parallel connections (default 5)",
                        type=int, default=5)
    parser.add_argument('-n', '--requests',
                        help="Total number of requests (default 100000)",
                        type=int, default=10000)
    parser.add_argument('-b', '--batch-size',
                        help="Number of request to send in parallel",
                        type=int, default=None)
    parser.add_argument('-P', '--pipeline',
                        help="Pipeline requests (honnor batch-size if set)",
                        action="store_true")
    parser.add_argument('-d', '--data-size', default=2,
                        help="Data size of SET/GET value in bytes (default 2)",
                        type=int)
    return parser.parse_args()


def group_iterable(iterable, total_size, group_size):
    processed_size = 0
    while True:
        if processed_size >= total_size:
            return
        else:
            chunk = itertools.islice(iterable, group_size)
            processed_size += group_size
            yield chunk


class Benchmark(object):

    def __init__(self, params):
        self.params = params
        self.request_count = self.params.requests
        self.requests_per_client = int(math.ceil(self.params.requests /
                                                 float(self.params.clients)))
        self.response_count = 0
        self.value = '*' * self.params.data_size

    @tornado.gen.coroutine
    def multiple_set(self, client_number):
        uds = self.params.unix_domain_socket
        client = tornadis.Client(host=self.params.hostname,
                                 port=self.params.port,
                                 unix_domain_socket=uds,
                                 autoconnect=False,
                                 tcp_nodelay=True)
        print_("Connect client", client_number)
        yield client.connect()
        print_("Client", client_number, "connected")
        futures = (client.call("SET", "benchmark-key", self.value)
                   for _ in six.moves.range(self.requests_per_client))
        if self.params.batch_size:
            batches = group_iterable(futures, self.requests_per_client,
                                     self.params.batch_size)
            for batch in itertools.imap(list, batches):
                print_("Send {} requests with client {}".format(len(batch),
                                                                client_number))
                responses = yield batch
                resp_count = len(responses)
                print_("Received {} responses "
                       "with client {}".format(resp_count, client_number))
                self.response_count += resp_count
        else:
            print_("Send {} requests "
                   "with client {}".format(self.requests_per_client,
                                           client_number))
            responses = yield list(futures)
            resp_count = len(responses)
            print_("Received {} responses with client {}".format(resp_count,
                                                                 client_number)
                   )
            self.response_count += resp_count

    @tornado.gen.coroutine
    def _call_pipeline(self, client, pipeline, client_number):
        print_("Send {} pipelined requests "
               "with client {}".format(pipeline.number_of_stacked_calls,
                                       client_number))
        responses = yield client.call(pipeline)
        resp_count = len(responses)
        print_("Received {} pipelined responses "
               "with client {}".format(resp_count, client_number))
        raise tornado.gen.Return(resp_count)

    @tornado.gen.coroutine
    def pipelined_multiple_set(self, client_number):
        uds = self.params.unix_domain_socket
        client = tornadis.Client(host=self.params.hostname,
                                 port=self.params.port,
                                 unix_domain_socket=uds,
                                 autoconnect=False,
                                 tcp_nodelay=True)
        print_("Connect client", client_number)
        yield client.connect()
        print_("Client", client_number, "connected")
        pipeline_size = self.params.batch_size or self.requests_per_client
        print_(pipeline_size)
        pipeline = tornadis.Pipeline()
        for _ in six.moves.range(0, self.requests_per_client):
            pipeline.stack_call("SET", "benchmark-key", self.value)
            if pipeline.number_of_stacked_calls >= pipeline_size:
                resp_count = yield self._call_pipeline(client, pipeline,
                                                       client_number)
                self.response_count += resp_count
                pipeline = tornadis.Pipeline()
        if pipeline.number_of_stacked_calls > 0:
            resp_count = yield self._call_pipeline(client, pipeline,
                                                   client_number)
            self.response_count += resp_count

    def stop_loop(self, future):
        excep = future.exception()
        if self.response_count == self.request_count:
            loop = tornado.ioloop.IOLoop.instance()
            loop.stop()
        if excep is not None:
            print_(excep)
            raise(excep)


def main():
    params = get_parameters()
    if params.requests % params.clients != 0:
        print_("Number of requests must be a multiple "
               "of number of clients", file=sys.stderr)
        sys.exit(-1)

    loop = tornado.ioloop.IOLoop.instance()
    benchmark = Benchmark(params)
    print_("Max requests per client:", benchmark.requests_per_client)
    before = datetime.datetime.now()
    for client_number in six.moves.range(params.clients):
        if params.pipeline:
            future = benchmark.pipelined_multiple_set(client_number)
        else:
            future = benchmark.multiple_set(client_number)
        loop.add_future(future, benchmark.stop_loop)
    loop.start()
    after = datetime.datetime.now()
    seconds = (after - before).total_seconds()
    print_("{} seconds".format(seconds))
    print_("{} requests per second".format(int(params.requests / seconds)))


if __name__ == '__main__':
    main()
