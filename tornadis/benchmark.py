import argparse
import datetime
import itertools
import logging
import math
import sys
import tornadis
import tornado


logging.basicConfig(level=logging.CRITICAL)


def get_parameters():
    parser = argparse.ArgumentParser(
        description='Tornadis benchmarking utility', add_help=False)
    parser.add_argument('--help', action='help')
    parser.add_argument('-h', '--hostname',
                        help="Server hostname (default 127.0.0.1)",
                        default="127.0.0.1")
    parser.add_argument('-p', '--port', help="Server port (default 6379)",
                        default=6379)
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
    parser.add_argument('-d', '--data-size', default=2,
                        help="Data size of SET/GET value in bytes (default 2)",
                        type=int)
    return parser.parse_args()


def group_iterable(iterable, group_size):
    it = iter(iterable)
    while True:
        chunk = tuple(itertools.islice(it, group_size))
        if not chunk:
            return
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
        client = tornadis.Client()
        print "Connect client", client_number
        yield client.connect()
        print "Client", client_number, "connected"
        futures = (client.call("SET", "benchmark-key", self.value)
                   for _ in xrange(self.requests_per_client))
        if self.params.batch_size:
            batches = group_iterable(futures, self.params.batch_size)
            for batch in itertools.imap(list, batches):
                print "Send {} requests with client {}".format(len(batch),
                                                               client_number)
                responses = yield batch
                resp_count = len(responses)
                print "Received {} responses " \
                      "with client {}".format(resp_count, client_number)
                self.response_count += resp_count
        else:
            print "Send {} requests " \
                  "with client {}".format(self.requests_per_client,
                                          client_number)
            responses = yield list(futures)
            resp_count = len(responses)
            print "Received {} responses with client {}".format(resp_count,
                                                                client_number)
            self.response_count += resp_count

    def stop_loop(self, future):
        excep = future.exception()
        if self.response_count == self.request_count:
            loop = tornado.ioloop.IOLoop.instance()
            loop.stop()
        if excep is not None:
            raise(excep)


def main():
    params = get_parameters()
    if params.requests % params.clients != 0:
        print >> sys.stderr, "Number of requests must be a multiple " \
                             "of number of clients"
        sys.exit(-1)

    loop = tornado.ioloop.IOLoop.instance()
    benchmark = Benchmark(params)
    print "Max requests per client:", benchmark.requests_per_client
    before = datetime.datetime.now()
    for client_number in xrange(params.clients):
        future = benchmark.multiple_set(client_number)
        loop.add_future(future, benchmark.stop_loop)
    loop.start()
    after = datetime.datetime.now()
    seconds = (after - before).total_seconds()
    print "{} seconds".format(seconds)
    print "{} requests per second".format(int(params.requests / seconds))


if __name__ == '__main__':
    main()
