import argparse
import asana
import json
import os
import re
import requests

from pathlib import Path


def authorize(access_token):
    client = asana.Client.access_token(access_token)
    return client


def get_nice_json(object_to_dump):
    return json.dumps(object_to_dump, sort_keys=True, indent=2, ensure_ascii=False)


def export_data(access_token, destination):
    destination_path = destination

    if not os.path.isdir(destination):
        os.mkdir(destination)

    task_folder = destination_path + '/' + 'tasks'

    if not os.path.isdir(task_folder):
        os.mkdir(task_folder)

    attachment_path = destination_path + '/' + 'attachments'
    if not os.path.isdir(attachment_path):
        os.mkdir(attachment_path)

    client = authorize(access_token)

    workspaces = list(client.workspaces.find_all(expand=["this"]))
    for workspace in workspaces:
        process_workspace(workspace, destination_path, client)


def process_workspace(workspace, destination_path, client):
    metadata_path = Path(destination_path).joinpath('workspace_information.json')
    with metadata_path.open(mode='w', encoding='utf-8') as metadata_file:
        metadata_file.write(get_nice_json(workspace))

    print("Exporting workspace: ", workspace.get('name'))
    projects = client.projects.find_by_workspace(workspace['gid'], iterator_type=None, expand=["this"])
    for project in projects:
        process_project(destination_path, project, client)


def safe(input):
    return re.sub('[^\w\-_\.]', '_', input)


def process_project(base_path, project, client):
    print("Exporting project:", project.get('name'))

    tasks_folder = base_path + '/' + 'tasks'
    project_json_path = Path(base_path).joinpath(safe(project['name']) + '.json')

    tasks = list(client.projects.tasks(project['gid'], expand=["this", "subtasks+"]))

    for key, task in enumerate(tasks):
        task_gid = task.get('gid')
        print(task_gid + ': ' + task.get('name'))

        stories = client.stories.get_stories_for_task(task_gid, iterator_type=None, expand=["this"])
        tasks[key]['stories'] = stories
        result = client.attachments.find_by_task(task_gid, iterator_type=None, expand=["this"])

        for attachment in result:
            if attachment.get('download_url'):
                response = requests.get(attachment.get('download_url'))
                file_name = base_path + '/' + 'attachments' + '/' + attachment.get('gid') + '_' + safe(
                    attachment.get('name'))
                with open(file_name, 'wb') as f:
                    f.write(response.content)

        tasks[key]['attachment_data'] = result
        task_path = tasks_folder + '/' + str(task_gid) + '_' + safe(task.get('name')) + '.json'

        with open(task_path, 'w') as f:
            f.write(get_nice_json(tasks[key]))

    project['tasks'] = tasks
    with project_json_path.open(mode='w', encoding='utf-8') as project_file:
        project_file.write(get_nice_json(project))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Export your data from Asana.')
    parser.add_argument('--access_token')
    parser.add_argument('--destination')
    args = parser.parse_args()

    export_data(args.access_token, args.destination)
    print("Exported to:", destination)
