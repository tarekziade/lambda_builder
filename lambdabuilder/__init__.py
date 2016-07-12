import os
from lambdabuilder.builder import create_zip


def main():
    ssh_key = os.path.expanduser("~/.ssh/loads.pem")
    git_repo = 'https://github.com/tarekziade/update_service.git'
    project_root = 'update_service'
    zip_filename = 'update_service.zip'
    s3_bucket = 'tarekfiles'


    path = create_zip(git_repo, project_root, zip_filename, ssh_key, s3_bucket)
