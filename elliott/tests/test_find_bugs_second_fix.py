import unittest

from click.testing import CliRunner
from elliottlib.bzutil import BugzillaBugTracker, JIRABugTracker
from elliottlib.cli.common import Runtime, cli
from flexmock import flexmock


class FindBugsSecondFixTestCase(unittest.TestCase):
    def test_find_bugs_second_fix(self):
        runner = CliRunner()
        jira_bug = flexmock(id='OCPBUGS-123', status="MODIFIED")

        flexmock(Runtime).should_receive("initialize").and_return(None)
        flexmock(Runtime).should_receive("get_major_minor").and_return(4, 16)
        flexmock(JIRABugTracker).should_receive("get_config").and_return(
            {
                'software_lifecycle': {'phase': 'pre-release'},
            }
        )
        client = flexmock()
        flexmock(client).should_receive("fields").and_return([])
        flexmock(JIRABugTracker).should_receive("login").and_return(client)
        flexmock(JIRABugTracker).should_receive("search").and_return([jira_bug])
        expected_comment = (
            "This CVE tracker was closed since it was not declared as first-fix for the"
            "recent OCP 4.16 version in pre-release"
        )
        flexmock(JIRABugTracker).should_receive("update_bug_status").with_args(
            jira_bug,
            target_status='CLOSED',
            comment=expected_comment,
            log_comment=True,
            noop=True,
        )

        result = runner.invoke(cli, ['-g', 'openshift-4.16', 'find-bugs:second-fix', '--noop'])
        print("CLI Output:", result.output)
        print("CLI Exception:", result.exception)
        self.assertEqual(result.exit_code, 0)


if __name__ == '__main__':
    unittest.main()
