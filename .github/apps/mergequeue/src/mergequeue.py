"""
mergequeue
----------

mergequeue is a HTTP server meant to handle webhook event emitted from Github.
Registered as a Github App, it allows user to request automated merging from
a pull request comment. Each merge request is put in a queue and process by order
of arrival. See :class:`~core.MergeQueueHandler` for details.

mergequeue can be run locally as long as a valid Github Personnal Access Token is
available.
"""

import argparse
import functools
import logging
import sys

import core

logger = logging.getLogger()

options = None


def parse_arguments():
    """
    Parse the command line arguments.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument('-q', '--quiet', action='store_true',
                        dest='quiet', default=False,
                        help='Do not log to stdout')
    parser.add_argument('-d', '--debug', action='store_true',
                        dest='debug', default=False,
                        help='Set logging level to DEBUG')
    parser.add_argument('-H', '--host', dest='host', default="127.0.0.1",
                        help='Server hostname')
    parser.add_argument('-p', '--port', dest='port', default="8080", type=int,
                        help='Server listening port')
    parser.add_argument('repo_owner',
                        help='Github repository owner')
    parser.add_argument('repo_name',
                        help='Github repository name')
    parser.add_argument('token',
                        help='Github account token')

    global options
    options = parser.parse_args()


def setup_logger():
    logging.root = logger

    if options.debug:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)

    if not options.quiet:
        stdout = logging.StreamHandler(sys.stdout)
        stdout.setFormatter(logging.Formatter(
            '%(asctime)s: [%(levelname)s] %(message)s'))
        logger.addHandler(stdout)


if __name__ == "__main__":
    parse_arguments()
    setup_logger()

    Handler = functools.partial(core.MergeQueueHandler, options.token,
                                options.repo_owner, options.repo_name)
    server = core.Server(Handler, options.host, options.port)
    try:
        server.start()
    finally:
        server.stop()
