from lambdabuilder.builder import create_zip


if __name__ == '__main__':

    ssh_key = os.path.expanduser("~/.ssh/loads.pem")

    git_repo = 'https://github.com/tarekziade/update_service.git'
    project_root = 'update_service'
    zip_filename = 'update_service.zip'


    path = create_zip(git_repo, project_root, zip_filename, ssh_key)
