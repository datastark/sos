#!/usr/bin/env python3
#
# Copyright (c) Bo Peng and the University of Texas MD Anderson Cancer Center
# Distributed under the terms of the 3-clause BSD License.

import os
import subprocess
import pytest

from sos.targets import file_target
from sos import execute_workflow

has_docker = True
try:
    subprocess.check_output("docker ps | grep test_sos", shell=True).decode()
except subprocess.CalledProcessError:
    subprocess.call("sh build_test_docker.sh", shell=True)
    try:
        subprocess.check_output("docker ps | grep test_sos", shell=True).decode()
    except subprocess.CalledProcessError:
        print("Failed to set up a docker machine with sos")
        has_docker = False


@pytest.mark.skipif(not has_docker, reason="Docker container not usable")
def test_from_host_option(clear_now_and_after):
    """Test from_remote option"""
    clear_now_and_after("llp")
    execute_workflow(
        """
        [10]
        task: from_host='llp'
        with open('llp', 'w') as llp:
            llp.write("LLP")
        """,
        options={
            "config_file": "~/docker.yml",
            "wait_for_task": True,
            "default_queue": "docker",
            "sig_mode": "force",
        },
    )
    assert os.path.isfile("llp")


@pytest.mark.skipif(not has_docker, reason="Docker container not usable")
def test_local_from_host_option(clear_now_and_after):
    """Test from_remote option"""
    clear_now_and_after("llp")
    execute_workflow(
        """
        [10]
        task: from_host='llp'
        sh:
        echo "LLP" > llp
        """,
        options={
            "config_file": "~/docker.yml",
            # do not wait for jobs
            "wait_for_task": True,
            "sig_mode": "force",
            "default_queue": "localhost",
        },
    )
    assert os.path.isfile("llp")


def test_worker_procs():
    # test -j option
    execute_workflow(
        """
        [1]
        input: for_each=dict(i=range(10))

        bash: expand=True
        echo {i}
        """,
        options={"sig_mode": "force", "worker_proces": ["1", "localhost:2"]},
    )


def test_worker_procs_with_task():
    # test -j option
    execute_workflow(
        """
        [1]
        input: for_each=dict(i=range(10))

        task: trunk_size = 0

        bash: expand=True
        echo {i}
        """,
        options={
            "sig_mode": "force",
            "default_queue": "localhost",
            "worker_proces": ["1", "localhost:2"],
        },
    )


@pytest.mark.skipif(not has_docker, reason="Docker container not usable")
def test_remote_execute(clear_now_and_after):
    clear_now_and_after("result_remote.txt", "local.txt")

    with open("local.txt", "w") as w:
        w.write("something")

    assert 0 == subprocess.call(
        "sos remote push docker --files local.txt -c ~/docker.yml", shell=True
    )

    with open("test_remote.sos", "w") as tr:
        tr.write(
            """
[10]
input: 'local.txt'
output: 'result_remote.txt'
task:

run:
cp local.txt result_remote.txt
echo 'adf' >> 'result_remote.txt'

"""
        )
    assert 0 == subprocess.call(
        "sos run test_remote.sos -c ~/docker.yml -r docker -s force -q localhost",
        shell=True,
    )

    assert not file_target("result_remote.txt").target_exists()

    # self.assertEqual(subprocess.call('sos preview result_remote.txt -c ~/docker.yml -r docker', shell=True), 0)
    # self.assertNotEqual(subprocess.call('sos preview result_remote.txt', shell=True), 0)
    assert 0 == subprocess.call(
        "sos remote pull docker --files result_remote.txt -c ~/docker.yml", shell=True
    )

    assert file_target("result_remote.txt").target_exists()

    # self.assertEqual(subprocess.call('sos preview result_remote.txt', shell=True), 0)
    with open("result_remote.txt") as w:
        content = w.read()
        assert "something" in content
        assert "adf" in content

    # test sos remote run
    assert 0 == subprocess.call(
        "sos remote run docker -c  ~/docker.yml --cmd cp result_remote.txt result_remote1.txt ",
        shell=True,
    )
    assert 0 == subprocess.call(
        "sos remote pull docker --files result_remote1.txt -c ~/docker.yml", shell=True
    )

    assert file_target("result_remote1.txt").target_exists()
