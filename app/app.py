"""
Copyright 2021 Amazon.com, Inc. or its affiliates. All Rights Reserved.
Permission is hereby granted, free of charge, to any person obtaining a copy of this
software and associated documentation files (the "Software"), to deal in the Software
without restriction, including without limitation the rights to use, copy, modify,
merge, publish, distribute, sublicense, and/or sell copies of the Software, and to
permit persons to whom the Software is furnished to do so.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A
PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""

import json
import logging
import os
import subprocess
import jinja2
import sys


# Logger
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

# Jinja configs
templateLoader = jinja2.FileSystemLoader(searchpath="./")
templateEnv = jinja2.Environment(loader=templateLoader, trim_blocks=True)


def get_stdout(output):
    """
    Validates command output returncode and returns stdout
    :param output: the output of a subprocess
    :return the stdout of the subprocess output
    """
    logger.info(output)
    if output.returncode == 0:
        command_output = output.stdout
    else:
        raise Exception(f'Command failed for - stderr: {output.stderr} - '
                        f'returncode: {output.returncode}')

    return command_output


def create_kubeconfig(cluster_name):
    """
    Updates the kubernetes context on the `kubeconfig` file.
    :param cluster_name: the name of the EKS cluster
    """
    logger.info('Create kube config file.')
    configure_cli = f'aws eks --region ap-northeast-1 update-kubeconfig --name {cluster_name}'
    output = subprocess.run(
        f'{configure_cli}',
        encoding='utf-8',
        capture_output=True,
        shell=True,
        check=False
    )
    if output.returncode != 0:
        raise RuntimeError(f'Failed to create kube config file {output.stderr}.')
    
    logger.info('Successfully created kubeconfig file.')


def update_identity_mappings(event, action):
    """
    Uses the `action` parameter to run an `kubectl apply` or
    `kubectl delete` command.
    :param event: the CFN event
    :param action: `apply` to create/update the config map, or `delete` to delete it
    """

    commands = {
        "apply": "kubectl get pod -n webrtcnttcom --kubeconfig /tmp/kubeconfig",
        "delete": "kubectl version"
    }

   
    output = subprocess.run(
        args=commands[action],
        encoding='utf-8',
        capture_output=True,
        shell=True,
        check=False
    )
    if output.returncode != 0:    
        raise RuntimeError(f'Failed to update identity mappings: {output.stderr}.')

    logger.info('Successfully updated identity mappings.')
    command_output = get_stdout(output)
    logger.info('output: %s', command_output)
    return 



def handler(event, _):
    """
    Entry point for the lambda.
    :param event: the CFN event
    :param context: the lambda context
    """

    kube_config_path = '/tmp/kubeconfig'
    os.environ['KUBECONFIG'] = kube_config_path

    cluster_name = event["ResourceProperties"]['ClusterName']

    try:
        create_kubeconfig(cluster_name)
        if event['RequestType'] == 'Create' or event['RequestType'] == 'Update':
            create(event)
        elif event['RequestType'] == 'Delete':
            delete(event)
    except Exception as ex:
        logger.error('Signaling failure')
        logger.error(ex)
        sys.exit(1)
    else:
        return "Success!"


def create(event):
    """
    Handles the `create` event.
    :param event: the CFN event
    :param context: the lambda context
    """
    logger.info(f"Creating identity mapping... event: {event}")
    update_identity_mappings(event=event, action="apply")

def delete(event):
    """
    Handles the `delete` event.
    :param event: the CFN event
    :param context: the lambda context
    """
    logger.info(f"Deleting identity mapping... event: {event}")
    update_identity_mappings(event=event, action="delete")
