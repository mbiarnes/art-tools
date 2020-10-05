from unittest import TestCase
from unittest.mock import MagicMock, patch

import yaml

from doozerlib.cli import scan_sources


class TestScanSourcesCli(TestCase):

    @patch("doozerlib.exectools.cmd_assert")
    def test_tagged_mosc_id(self, mock_cmd):
        mock_cmd.return_value = ("id-1", "stderr")
        self.assertEqual("id-1", scan_sources._tagged_mosc_id("kc.conf", "4.2", "s390x", True))
        self.assertIn("--kubeconfig 'kc.conf'", mock_cmd.call_args_list[0][0][0])
        self.assertIn("--namespace 'ocp-s390x-priv'", mock_cmd.call_args_list[0][0][0])
        self.assertIn("istag '4.2-art-latest-s390x-priv", mock_cmd.call_args_list[0][0][0])

    @patch("doozerlib.cli.scan_sources._tagged_mosc_id")
    @patch("doozerlib.cli.scan_sources._latest_rhcos_build_id")
    def test_tagged_mosc_id(self, mock_latest, mock_tagged):
        mock_tagged.return_value = "id-1"
        mock_latest.return_value = "id-2"
        runtime = MagicMock()
        runtime.get_minor_version.return_value = "4.2"
        runtime.arches = ['s390x']

        statuses = scan_sources._detect_rhcos_status(runtime, kubeconfig="dummy")
        self.assertEqual(2, len(statuses), "expect public and private status reported")
        self.assertTrue(all(s['changed'] for s in statuses), "expect changed status reported")
        self.assertTrue(all("id-1" in s['reason'] for s in statuses), "expect previous id in reason")
        self.assertTrue(all("id-2" in s['reason'] for s in statuses), "expect changed id in reason")
