# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
"""
Support for running toolchain-building jobs via dedicated scripts
"""

from __future__ import absolute_import, print_function, unicode_literals

import time
from voluptuous import Schema, Required

from taskgraph.transforms.job import run_job_using
from taskgraph.transforms.job.common import (
    docker_worker_add_tc_vcs_cache,
    docker_worker_add_gecko_vcs_env_vars
)

toolchain_run_schema = Schema({
    Required('using'): 'toolchain-script',

    # the script (in taskcluster/scripts/misc) to run
    Required('script'): basestring,
})


@run_job_using("docker-worker", "toolchain-script", schema=toolchain_run_schema)
def docker_worker_toolchain(config, job, taskdesc):
    run = job['run']

    worker = taskdesc['worker']
    worker['artifacts'] = []
    worker['caches'] = []

    worker['artifacts'].append({
        'name': 'public',
        'path': '/home/worker/workspace/artifacts/',
        'type': 'directory',
    })

    docker_worker_add_tc_vcs_cache(config, job, taskdesc)
    docker_worker_add_gecko_vcs_env_vars(config, job, taskdesc)

    env = worker['env']
    env.update({
        'MOZ_BUILD_DATE': time.strftime("%Y%m%d%H%M%S", time.gmtime(config.params['pushdate'])),
        'MOZ_SCM_LEVEL': config.params['level'],
        'TOOLS_DISABLE': 'true',
    })

    # tooltool downloads; note that this downloads using the API endpoint directly,
    # rather than via relengapi-proxy
    worker['caches'].append({
        'type': 'persistent',
        'name': 'tooltool-cache',
        'mount-point': '/home/worker/tooltool-cache',
    })
    env['TOOLTOOL_CACHE'] = '/home/worker/tooltool-cache'
    env['TOOLTOOL_REPO'] = 'https://github.com/mozilla/build-tooltool'
    env['TOOLTOOL_REV'] = 'master'

    command = ' && '.join([
        "cd /home/worker/",
        "./bin/checkout-sources.sh",
        "./workspace/build/src/taskcluster/scripts/misc/" + run['script'],
    ])
    worker['command'] = ["/bin/bash", "-c", command]
