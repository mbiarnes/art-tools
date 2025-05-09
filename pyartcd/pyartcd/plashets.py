import asyncio
import logging
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Sequence, Optional, Tuple

from artcommonlib import exectools

from pyartcd import constants, util
from pyartcd.constants import PLASHET_REMOTES

working_dir = "plashet-working"

logger = logging.getLogger('pyartcd')

previous_packages = [
    "conmon",
    "cri-o",
    "cri-tools",
    "crun",
    "haproxy",
    "ignition",
    "kernel",
    "kernel-rt",
    "libreswan",  # can disappear after ovn dropped the pin in dockerfile
    "nmstate",
    "openshift",
    "openvswitch",
    "ovn",
    "podman",
    "python3-openvswitch",
    "spdlog",
]

ironic_previous_packages_for_4_15_plus = [
    "openstack-ironic",
    "openstack-ironic-inspector",
    "openstack-ironic-python-agent",
    "python-ironic-lib",
    "python-sushy",
]


def plashet_config_for_major_minor(major, minor):
    return {
        "rhel-10-server-ose-rpms-embargoed": {
            "slug": "el10-embargoed",
            "tag": f"rhaos-{major}.{minor}-rhel-10-candidate",
            "product_version": f"OSE-{major}.{minor}-RHEL-10",
            "include_embargoed": True,
            "embargoed_tags": [f"rhaos-{major}.{minor}-rhel-10-embargoed"],
            "include_previous_packages": previous_packages,
        },
        "rhel-10-server-ose-rpms": {
            "slug": "el10",
            "tag": f"rhaos-{major}.{minor}-rhel-10-candidate",
            "product_version": f"OSE-{major}.{minor}-RHEL-10",
            "include_embargoed": False,
            "embargoed_tags": [f"rhaos-{major}.{minor}-rhel-10-embargoed"],
            "include_previous_packages": previous_packages,
        },
        "rhel-9-server-ose-rpms-embargoed": {
            "slug": "el9-embargoed",
            "tag": f"rhaos-{major}.{minor}-rhel-9-candidate",
            "product_version": f"OSE-{major}.{minor}-RHEL-9",
            "include_embargoed": True,
            "embargoed_tags": [f"rhaos-{major}.{minor}-rhel-9-embargoed"],
            "include_previous_packages": previous_packages,
        },
        "rhel-9-server-ose-rpms": {
            "slug": "el9",
            "tag": f"rhaos-{major}.{minor}-rhel-9-candidate",
            "product_version": f"OSE-{major}.{minor}-RHEL-9",
            "include_embargoed": False,
            "embargoed_tags": [f"rhaos-{major}.{minor}-rhel-9-embargoed"],
            "include_previous_packages": previous_packages,
        },
        "rhel-9-server-ironic-rpms": {
            "slug": "ironic-el9",
            "tag": f"rhaos-{major}.{minor}-ironic-rhel-9-candidate",
            "product_version": f"OSE-IRONIC-{major}.{minor}-RHEL-9",
            "include_embargoed": False,
            "embargoed_tags": [],  # unlikely to exist until we begin using -gating tag
            # FIXME: This is a short-term workaround for 4.15+ until prevalidation repo is in use
            # For more info about why this is needed, see https://github.com/openshift-eng/aos-cd-jobs/pull/3920
            "include_previous_packages": ironic_previous_packages_for_4_15_plus
            if (int(major), int(minor)) >= (4, 15)
            else [],
        },
        "rhel-8-server-ose-rpms-embargoed": {
            "slug": "el8-embargoed",
            "tag": f"rhaos-{major}.{minor}-rhel-8-candidate",
            "product_version": f"OSE-{major}.{minor}-RHEL-8",
            "include_embargoed": True,
            "embargoed_tags": [f"rhaos-{major}.{minor}-rhel-8-embargoed"],
            "include_previous_packages": previous_packages,
        },
        "rhel-8-server-ose-rpms": {
            "slug": "el8",
            "tag": f"rhaos-{major}.{minor}-rhel-8-candidate",
            "product_version": f"OSE-{major}.{minor}-RHEL-8",
            "include_embargoed": False,
            "embargoed_tags": [f"rhaos-{major}.{minor}-rhel-8-embargoed"],
            "include_previous_packages": previous_packages,
        },
        "rhel-8-server-ironic-rpms": {
            "slug": "ironic-el8",
            "tag": f"rhaos-{major}.{minor}-ironic-rhel-8-candidate",
            "product_version": f"OSE-IRONIC-{major}.{minor}-RHEL-8",
            "include_embargoed": False,
            "embargoed_tags": [],  # unlikely to exist until we begin using -gating tag
            "include_previous_packages": [],
        },
        "rhel-server-ose-rpms-embargoed": {
            "slug": "el7-embargoed",
            "tag": f"rhaos-{major}.{minor}-rhel-7-candidate",
            "product_version": f"RHEL-7-OSE-{major}.{minor}",
            "include_embargoed": True,
            "embargoed_tags": [f"rhaos-{major}.{minor}-rhel-7-embargoed"],
            "include_previous_packages": previous_packages,
        },
        "rhel-server-ose-rpms": {
            "slug": "el7",
            "tag": f"rhaos-{major}.{minor}-rhel-7-candidate",
            "product_version": f"RHEL-7-OSE-{major}.{minor}",
            "include_embargoed": False,
            "embargoed_tags": [f"rhaos-{major}.{minor}-rhel-7-embargoed"],
            "include_previous_packages": previous_packages,
        },
        "rhel-9-server-microshift-rpms": {
            "slug": "microshift-el9",
            "tag": f"rhaos-{major}.{minor}-rhel-9-candidate",
            "product_version": f"OSE-{major}.{minor}-RHEL-9",
            "include_embargoed": False,
            "embargoed_tags": [],
            "include_previous_packages": [],
        },
    }


async def build_plashets(
    stream: str,
    release: str,
    assembly: str = 'stream',
    repos: Sequence[str] = (),
    doozer_working: str = 'doozer-working',
    data_path: str = constants.OCP_BUILD_DATA_URL,
    data_gitref: str = '',
    copy_links: bool = False,
    dry_run: bool = False,
) -> dict:
    """
    Unless no RPMs have changed, create multiple yum repos (one for each arch) of RPMs
    based on -candidate tags. Based on release state, those repos can be signed
    (release state) or unsigned (pre-release state)

    :param stream: e.g. 4.14
    :param release: e.g. 202304181947.p?
    :param assembly: e.g. assembly name, defaults to 'stream'
    :param repos: (optional) limit the repos to build to this list. If empty, build all repos. e.g. ['rhel-8-server-ose-rpms']
    :param doozer_working: Doozer working dir
    :param data_path: ocp-build-data fork to use
    :param data_gitref: Doozer data path git [branch / tag / sha] to use
    :param dry_run: do not actually run the command, just log it
    :param copy_links: transform symlink into referent file/dir

    Returns a list describing the plashets that have been built. The dict will look like this:
    {
        'repo-name-1': {
            'plashetDirName': str,
            'localPlashetPath: str
        },

        ...

        'repo-name-n': {
            'plashetDirName': str,
            'localPlashetPath: str
        },
    }
    """

    major, minor = stream.split('.')  # e.g. ('4', '14') from '4.14'
    revision = release.replace('.p?', '')  # e.g. '202304181947' from '202304181947.p?'

    # Load group config
    group_config = await util.load_group_config(
        group=f'openshift-{stream}', assembly=assembly, doozer_data_path=data_path, doozer_data_gitref=data_gitref
    )

    # Check if assemblies are enabled for current group
    if not group_config.get('assemblies', {}).get('enabled'):
        assembly = 'stream'
        logger.warning("Assembly name reset to 'stream' because assemblies are not enabled in ocp-build-data.")

    # Get plashet repos
    group_repos = group_config.get('repos', {}).keys()
    if repos:
        logger.info(f"Filtering plashet repos to only the given ones: {repos}")
        group_repos = [repo for repo in group_repos if repo in repos]
    group_plashet_config = plashet_config_for_major_minor(major, minor)
    plashet_config = {repo: group_plashet_config[repo] for repo in group_plashet_config if repo in group_repos}
    logger.info("Building plashet repos: %s", ", ".join(plashet_config.keys()))

    # Check release state
    signing_mode = await util.get_signing_mode(group_config=group_config)

    # Create plashet repos on ocp-artifacts
    # We can't safely run doozer config:plashet from-tags in parallel as this moment.
    # Build plashet repos one by one.
    plashets_built = {}  # hold the information of all built plashet repos
    timestamp = datetime.strptime(revision, '%Y%m%d%H%M%S')
    signing_advisory = group_config.get('signing_advisory', '0')
    arches = group_config['arches']
    group_param = f'openshift-{stream}'
    if data_gitref:
        group_param += f'@{data_gitref}'

    for repo_type, config in plashet_config.items():
        logger.info('Building plashet repo for %s', repo_type)
        slug = config['slug']
        name = f'{timestamp.year}-{timestamp.month:02}/{revision}'
        base_dir = Path(working_dir, f'plashets/{major}.{minor}/{assembly}/{slug}')
        local_path = await build_plashet_from_tags(
            group_param=group_param,
            assembly=assembly,
            base_dir=base_dir,
            name=name,
            arches=arches,
            include_embargoed=config['include_embargoed'],
            signing_mode=signing_mode,
            signing_advisory=signing_advisory,
            embargoed_tags=config['embargoed_tags'],
            tag_pvs=((config["tag"], config['product_version']),),
            include_previous_packages=config['include_previous_packages'],
            data_path=data_path,
            dry_run=dry_run,
            doozer_working=doozer_working,
        )

        logger.info('Plashet repo for %s created: %s', repo_type, local_path)
        symlink_path = create_latest_symlink(base_dir=base_dir, plashet_name=name)
        logger.info('Symlink for %s created: %s', repo_type, symlink_path)

        remote_base_dir = Path(f'/mnt/data/pub/RHOCP/plashets/{major}.{minor}/{assembly}/{slug}')
        logger.info('Copying %s to remote host...', base_dir)

        await asyncio.gather(
            *[
                copy_to_remote(
                    plashet_remote['host'], base_dir, remote_base_dir, dry_run=dry_run, copy_links=copy_links
                )
                for plashet_remote in PLASHET_REMOTES
            ]
        )

        plashets_built[repo_type] = {
            'plashetDirName': revision,
            'localPlashetPath': str(local_path),
        }

    return plashets_built


async def build_plashet_from_tags(
    group_param: str,
    assembly: str,
    base_dir: os.PathLike,
    name: str,
    arches: Sequence[str],
    include_embargoed: bool,
    signing_mode: str,
    signing_advisory: int,
    tag_pvs: Sequence[Tuple[str, str]],
    embargoed_tags: Optional[Sequence[str]],
    include_previous_packages: Optional[Sequence[str]] = None,
    poll_for: int = 0,
    data_path: str = constants.OCP_BUILD_DATA_URL,
    doozer_working: str = 'doozer-working',
    dry_run: bool = False,
):
    """
    Builds Plashet repo with "from-tags"
    """

    repo_path = Path(base_dir, name)
    if repo_path.exists():
        shutil.rmtree(repo_path)
    cmd = [
        "doozer",
        f'--data-path={data_path}',
        "--working-dir",
        doozer_working,
        "--group",
        group_param,
        "--assembly",
        assembly,
        "config:plashet",
        "--base-dir",
        str(base_dir),
        "--name",
        name,
        "--repo-subdir",
        "os",
    ]
    for arch in arches:
        cmd.extend(["--arch", arch, signing_mode])
    cmd.extend(
        [
            "from-tags",
            "--signing-advisory-id",
            f"{signing_advisory or 54765}",
            "--signing-advisory-mode",
            "clean",
            "--inherit",
        ]
    )
    if include_embargoed:
        cmd.append("--include-embargoed")
    if embargoed_tags:
        for t in embargoed_tags:
            cmd.extend(["--embargoed-brew-tag", t])
    for tag, pv in tag_pvs:
        cmd.extend(["--brew-tag", tag, pv])
    for pkg in include_previous_packages:
        cmd.extend(["--include-previous-for", pkg])
    if poll_for:
        cmd.extend(["--poll-for", str(poll_for)])

    if dry_run:
        repo_path.mkdir(parents=True)
        logger.warning("[Dry run] Would have run %s", cmd)
    else:
        logger.info("Executing %s", cmd)
        await exectools.cmd_assert_async(cmd, env=os.environ.copy())
    return os.path.abspath(Path(base_dir, name))


def create_latest_symlink(base_dir: os.PathLike, plashet_name: str):
    symlink_path = Path(base_dir, "latest")
    if symlink_path.is_symlink():
        symlink_path.unlink()
    symlink_path.symlink_to(plashet_name, target_is_directory=True)
    return symlink_path


async def copy_to_remote(
    plashet_remote_host: str,
    local_base_dir: os.PathLike,
    remote_base_dir: os.PathLike,
    dry_run: bool = False,
    copy_links: bool = False,
):
    """
    Copies plashet out to remote host (ocp-artifacts)
    """

    # Make sure the remote base dir exist
    local_base_dir = Path(local_base_dir)
    remote_base_dir = Path(remote_base_dir)
    cmd = [
        "ssh",
        plashet_remote_host,
        "--",
        "mkdir",
        "-p",
        "--",
        f"{remote_base_dir}",
    ]
    if dry_run:
        logger.warning("[DRY RUN] Would have run %s", cmd)
    else:
        logger.info("Executing %s", ' '.join(cmd))
        await exectools.cmd_assert_async(cmd, env=os.environ.copy())

    # Copy local dir to remote
    cmd = ["rsync", "-av"]
    if copy_links:
        cmd.append('--copy-links')
    else:
        cmd.append('--links')
    cmd.extend(
        [
            "--progress",
            "-h",
            "--no-g",
            "--omit-dir-times",
            "--chmod=Dug=rwX,ugo+r",
            "--perms",
            "--",
            f"{local_base_dir}/",
            f"{plashet_remote_host}:{remote_base_dir}",
        ]
    )

    if dry_run:
        logger.warning("[DRY RUN] Would have run %s", cmd)
    else:
        logger.info("Executing %s", ' '.join(cmd))
        await exectools.cmd_assert_async(cmd, env=os.environ.copy())
