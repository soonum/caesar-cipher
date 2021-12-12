"""
core
----

Core logic of mergequeue Github application.
"""

import logging
import queue
import threading

import flask
from flask import request
import github


#: Header provided by Github to know which webhook event has been triggered.
GITHUB_EVENT = "X-Github-Event"
WEBHOOK_SECRET = "cjeoizfmlksnqczl43T542Fkcort"

#: ID used in Github comment to trigger action from the app.
APP_ID = "@mergequeue"
#: Prefix used in comment message to know if a message has been written by
#: the app on user behalf.
APP_PREFIX = "***[from mergequeue]***"

STAGING = "staging"
#: Size of the batch merge queue. Once it's full a batch merge is scheduled.
BATCH_SIZE = 3

logger = logging.getLogger()


class Server:
    """
    Simple HTTP server handling Github webhook requests.

    :param handler_class: class implementing routes endpoint
    :param host: hostname for the server as :class:`str`
    :param port: port to listen to as :class:`int`
    """

    def __init__(self, handler_class, host, port):
        self.host = host
        self.port = port

        self.handler = handler_class()
        self.app = flask.Flask('CI server')
        self.app.add_url_rule('/', methods=['POST'],
                              view_func=self.handler.on_webhook_event)

        self._shutting_down = False

    def start(self):
        logger.info("Starting server")
        self.handler.connect()
        self.app.run(host=self.host, port=self.port)

    def stop(self):
        if self._shutting_down:
            return

        logger.info("Shutting down")
        self._shutting_down = True
        self.handler.close()


class MergeQueueHandler:
    """
    Handle HTTP webhook events via :meth:`~MergeQueueHandler.on_webhook_event`.
    According to the value of :const:`GITHUB_EVENT` header, an event can be
    either discarded or handled by one of the following handler:
    * :meth:`~MergeQueueHandler.on_pull_request_comment`
    * :meth:`~MergeQueueHandler.on_workflow_run`

    It manages user requests for branch merging in two ways:
    * one branch at a time via :meth:`~MergeQueueHandler.try_merge`
    * several branch in one go via :meth:`~MergeQueueHandler.try_batchmerge`

    A call to :meth:`~MergeQueueHandler.connect` must be executed prior sending
    commands from Github endpoint.

    :param access_token: personal access token as :class:`str`
    :param repo_owner: repository owner name as :class:`str`
    :param repo_name: repository name as :class:`str`
    """

    def __init__(self, access_token, repo_owner, repo_name):
        self._access_token = access_token
        self._repo_owner = repo_owner
        self._repo_name = repo_name
        self._repo_path = self._repo_owner + '/' + self._repo_name

        self._conn = None
        self.repo = None

        self._merge_queue = queue.Queue()
        self._batch_merge_queue = []
        self._batch_merge_lock = threading.Lock()
        # Thread handling queue of merge requests
        self._queue_thread = None

        # Dict formatted as {issue_number: WorkflowEvent}
        self._workflow_events = {}

        self._available_commands = {
            "try-merge": self.try_merge,
            "try-batchmerge": self.try_batchmerge
        }

        self._shutting_down = False

    def connect(self):
        """
        Connect to repository hosted on Github.
        """
        logger.info("Connecting to Github")
        self._conn = github.Github(self._access_token)
        logger.info(f"Fetching repository {self._repo_path}")
        self.repo = self._conn.get_repo(self._repo_path)

        self._queue_thread = threading.Thread(target=self._process_queue).start()

    def close(self):
        if self._shutting_down:
            return

        self._shutting_down = True
        self._merge_queue.put_nowait(None)
        if self._queue_thread:
            # Give some time to process ongoing merge
            self._queue_thread.join(timeout=20)

    def on_webhook_event(self):
        """
        Handle any registered webhook event.
        """
        event_name = request.headers.get(GITHUB_EVENT)
        if not event_name:
            return "Webhook Event Not Found"

        body = request.get_json()

        if event_name == "issue_comment":
            if not body["issue"].get("pull_request"):
                # Comment from a regular issue, discard event.
                return "Comment not from a pull-request"
            return self.on_pull_request_comment(body)
        elif event_name == "workflow_run":
            return self.on_workflow_run(body)
        else:
            return "Webhook Event Not Handled"

    def on_pull_request_comment(self, body):
        """
        Handle pull request comment event.

        :param body: payload of the webhook as JSON
        """
        if body["action"] == "deleted":
            return "Does nothing on comment deletion"

        pull_request = self.repo.get_pull(body["issue"]["number"])
        _, has_mention, command = self._parse_issue_comment(body["comment"])

        if not has_mention:
            return "mergequeue app not mentioned"
        elif has_mention and command not in self._available_commands:
            reason = "no command provided" if command is None else f"unknown command `{command}`"
            message = f"Failed to process command (reason: {reason})"
            self.send_message(pull_request.number, message)
            logger.info(f"[PR #{pull_request.number}] {message}")
            return f"Unknown command: {command}"

        # Check if a user has push access to master branch.
        user_push_access = self.repo.get_branch("master"). get_user_push_restrictions()
        user = pull_request.get_issue_comment(body["comment"]["id"]).user
        try:
            if user not in user_push_access:
                message = f"User @{user.name} hasn't push access on `master` branch."
                self.send_message(pull_request.number, message)
                logger.info(f"[PR #{pull_request.number}] {message}")
                return "User hasn't the push permission\n"
        except github.GithubException:
            # Branch restrictions are not available or not set, ignoring this exception.
            pass

        self._available_commands[command](pull_request)
        return f"Command `{command}` is being processed\n"

    def on_workflow_run(self, body):
        """
        Handle workflow run event.

        :param body: payload of the webhook as JSON
        """
        workflow_run = self.repo.get_workflow_run(body["workflow_run"]["id"])

        if workflow_run.status != "completed":
            return "Nothing done, workflow run is not completed"
        if workflow_run.head_branch != STAGING:
            return "Nothing done, workflow run is not against 'staging' branch"

        try:
            workflow_event = self._workflow_events[workflow_run.head_sha]
        except KeyError:
            pass
        else:
            logger.info(f"[PR #{workflow_event.pull_request_number}] Workflow completed")
            workflow_event.set_result(workflow_run.conclusion)
            self._workflow_events.pop(workflow_run.head_sha, None)

        return f"Workflow {workflow_run.id} has been handled"

    def _parse_issue_comment(self, comment):
        """
        Retrieve details about a ``comment``.

        :param comment: comment message as JSON

        :return: :class:`tuple` as ``(author, has_mention, command)``
        """
        author = comment["user"]["login"]
        result = self._parse_command(comment["body"])
        return (author, *result)

    def _parse_command(self, message):
        """
        Parse comment message to find a command when :const:`APP_ID` is mentioned.

        :param message: comment message as :class:`str`

        :return: :class:`tuple` as ``(has_mention, command)``
        """
        _, has_mention, remain = message.partition(APP_ID)
        command = None
        if has_mention and remain:
            command = remain.lstrip().split(maxsplit=1)[0] or None
        return (bool(has_mention), command)

    def try_merge(self, pull_request):
        """
        Add ``pull_request`` to the merge queue.

        :param pull_request: :class:`github.PullRequest.PullRequest`
        """
        self._merge_queue.put_nowait(pull_request)
        logger.info(f"Pull Request #{pull_request.number} put in queue")

    def try_batchmerge(self, pull_request):
        """
        Add ``pull_request`` to the batch merge queue. Once :const:`BATCH_SIZE`
        is reached, a batch merge is scheduled as a new pull request using a
        temporary branch.

        Pull requests are processed by order of arrival in a FIFO pattern.

        When batch merge pull request is created, all the pull requests included
        in it are notified via a PR comment.

        :param pull_request: :class:`github.PullRequest.PullRequest`
        """
        # Use a lock for the queue to avoid adding item while processing a batch
        with self._batch_merge_lock:
            # A pull request cannot be added to the batch queue twice.
            added_pr_numbers = [pr.number for pr in self._batch_merge_queue]
            if pull_request.number in added_pr_numbers:
                self.send_message(pull_request.number,
                                  "Pull request already added to batch merge queue.")
                return

            self._batch_merge_queue.append(pull_request)
            logger.info(f"[PR #{pull_request.number}] Pull request put in batch queue")

            if len(self._batch_merge_queue) >= BATCH_SIZE:
                batch_id = abs(hash(tuple(self._batch_merge_queue)))
                branch_name = f"batch-{batch_id}"
                self.repo.create_git_ref(f"refs/heads/{branch_name}",
                                         self._batch_merge_queue[0].head.sha)
                logger.debug(f"Batch mergue branch `{branch_name}` created")

                pr_added = []
                for pull_request in self._batch_merge_queue:
                    try:
                        self.repo.merge(branch_name, pull_request.head.ref)
                    except github.GithubException:
                        message = (f"Batch branch `{branch_name}` rebase onto"
                                   f" {pull_request.head.ref} failed (cannot fast-forward)")
                        logger.info(f"[PR #{pull_request.number}] {message}")
                        self.send_message(pull_request.number, message)
                    else:
                        pr_added.append(pull_request)
                        logger.debug(f"[PR #{pull_request.number}] PR added to"
                                     f" batch merge banch `{branch_name}`")

                if not pr_added:
                    self._batch_merge_queue.clear()
                    logger.info(f"No pull requests added to batch merge on branch '{branch_name}'")
                    return

                # Format pull request details to be printed in batch PR body
                pr_details = [f"- [#{pr.number}]({pr.html_url})\n" for pr in pr_added]
                pr_title = f"{APP_ID} Batch merge with `{branch_name}`"
                pr_body = (f"{APP_PREFIX} Batch merge attempt for the following"
                           f" pull requests:\n {''.join(pr_details)}")
                batch_pr = self.repo.create_pull(
                    title=pr_title, body=pr_body, head=branch_name, base="master")
                logger.info(f"[PR #{batch_pr.number}] Batch merge pull request"
                            f" created for branch `{branch_name}`")

                self._merge_queue.put_nowait(batch_pr)
                self._batch_merge_queue.clear()

                for pr in pr_added:
                    message = (f"Commits added to `{branch_name}` branch.\n"
                               f" Check batch merge pull request [#{batch_pr.number}]"
                               f"({batch_pr.html_url}) associated with"
                               " this branch to know merge status.")
                    self.send_message(pr.number, message)

            else:
                self.send_message(
                    pull_request.number,
                    "Pull request added to the batch merge queue. It will be processed soon.")

    def rebase_branch(self, base, head, force=False, log_prefix=""):
        """
        Rebase ``base`` branch on top of ``head`` branch.
        If ``base`` branch doesn't exist, it will be created. Conversely it
        assumes that ``head`` branch exists.

        :param base: name of the base branch as :class:`str`
        :param head: name of the head branch as :class:`str`
        :param force: :class:`bool` to force rebase
        :param log_prefix: prefix used in the log to identify a pull request
        """
        head_branch = self.repo.get_branch(head)
        try:
            self.repo.get_branch(base)
        except github.GithubException as err:
            if err.status == 404:
                logger.debug(f"{log_prefix} Branch `{base}` cannont be found, creating one")
                self.repo.create_git_ref(f"refs/heads/{base}", head_branch.commit.sha)
            elif err.status == 422:
                # Fast-forward failed
                raise
        else:
            ref = self.repo.get_git_ref(f"heads/{base}")
            ref.edit(head_branch.commit.sha, force=force)
            logger.debug(f"{log_prefix} `{base}` branch rebased on top of `{head}`")

    def update_pr_branch(self, pull_request, base, log_prefix=""):
        """
        :param pull_request: :class:`github.PullRequest.PullRequest`
        :param base: name of the base branch as :class:`str`
        :param log_prefix: prefix used in the log to identify a pull request
        """
        pull_request.edit(base=base)
        pull_request.update_branch()
        logger.debug(f"{log_prefix} Base set to `{base}` head")

    def get_tests_result(self, sha, pull_request_number):
        """
        Retrieve result of a test suite executed remotely.

        :param sha: commit SHA upon which test suite is run
        :param pull_request_number: PR number as :class:`str`

        :return: ``True`` if tests passed, ``False`` otherwise
        """
        workflow_event = WorkflowEvent(pull_request_number)
        self._workflow_events[sha] = workflow_event
        return workflow_event.get_result()

    def _process_queue(self):
        while True:
            # Wait until a merge is requested.
            pull_request = self._merge_queue.get()
            if pull_request is None:
                # Shutting down
                return
            prefix = f"[PR #{pull_request.number}]"

            self.rebase_branch(STAGING, "master")
            self.update_pr_branch(pull_request, "master", log_prefix=prefix)
            try:
                self.rebase_branch(STAGING, pull_request.head.ref, log_prefix=prefix)
                logger.debug(f"{prefix} `{pull_request.head.ref}` merged into `{STAGING}`")
            except github.GithubException:
                message = f"Rebasing `{pull_request.head.ref}` on top of `master` failed (cannot fast-forward)"
                logger.info(f"{prefix} {message}")
                self.send_message(pull_request.number, message)
                continue

            success = self.get_tests_result(
               self.repo.get_branch(pull_request.head.ref).commit.sha,
               pull_request.number)
            if success:
                pull_request.merge(merge_method="rebase")
                logger.info(f"{prefix} `{pull_request.head.ref}` successfully merged into `master`")
            else:
                message = f"Automated tests failed, `{pull_request.head.ref}` be merged into `master`"
                self.send_message(pull_request.number, message)
                logger.info(f"{prefix} {message}")

            # Set staging branch to master HEAD unconditonally. That way, further
            # merge attempts will begin with a clean state.
            self.rebase_branch(STAGING, "master", force=True, log_prefix=prefix)

    def send_message(self, issue_number, message):
        """
        Create an issue comment message in the pull request identified by
        ``issue_number``.

        :param issue_number: pull request unique number as :class:`int`
        :param message: body of issue comment
        """
        issue = self.repo.get_issue(number=issue_number)
        issue.create_comment(" ".join([APP_PREFIX, message]))


class WorkflowEvent:
    """
    Class that represent a workflow_run event. It allows one to wait on run
    result while another one is responsible to set this very result.

    :param pull_request_number: pull request unique number as :class:`int`
    """

    def __init__(self, pull_request_number):
        self._pull_request_number = pull_request_number
        self._success = False
        self._result = threading.Event()

    @property
    def pull_request_number(self):
        return self._pull_request_number

    @property
    def success(self):
        return self._success

    def get_result(self):
        self._result.wait()
        return self.success

    def set_result(self, message):
        if message == "success":
            self._success = True

        self._result.set()
