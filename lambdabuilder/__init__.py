import time
import os
import sys
import contextlib

from boto.ec2 import connect_to_region
from paramiko.client import SSHClient, AutoAddPolicy
from paramiko.sftp_client import SFTPClient
from paramiko.ssh_exception import NoValidConnectionsError

# http://docs.aws.amazon.com/lambda/latest/dg/current-supported-versions.html
AWS_REGION = "us-west-2"
AMI_ID = "ami-f0091d91"
KEY_PAIR = "loads"
INSTANCE_TYPE = "t2.micro"
INSTANCE_NAME = "amo2kinto-lambda-zip-builder"
INSTANCE_PROJECT = "amo2kinto-lambda"
GIT_REPO = 'https://github.com/tarekziade/update_service.git'
PROJECT_ROOT = 'update_service'
ZIP_FILENAME = 'update_service.zip'


@contextlib.contextmanager
def aws_instance():
    # 1. Connect on the AWS region
    print("Connecting to %s" % AWS_REGION)
    conn = connect_to_region(AWS_REGION, is_secure=True)

    # 2. Create a Amazon Lambda AMI EC2 instance
    print("Starting an new instance of %s" % AMI_ID)
    reservations = conn.run_instances(AMI_ID,
                                    min_count=1, max_count=1,
                                    key_name=KEY_PAIR,
                                    instance_type=INSTANCE_TYPE)

    instance = reservations.instances[0]

    # 3. Tag the instance
    conn.create_tags([instance.id], {
        "Name": INSTANCE_NAME,
        "Projects": INSTANCE_PROJECT,
    })
    print("Instance Name:", INSTANCE_NAME)

    # 4. Wait for running
    while instance.state != "running":
        print("\rInstance state: %s" % instance.state, end="")
        sys.stdout.flush()
        time.sleep(10)
        instance.update()

    print("\rInstance state: %s" % instance.state)
    print("Instance IP:", instance.ip_address)

    # ready.
    try:
        yield instance
    finally:
        # terminate the instance
        print("\rTerminating EC2 instance.")
        conn.terminate_instances(instance.id)
        print("OK.")


class CustomSSHClient(SSHClient):
    def execute(self, command, description=None):
        if description is not None:
            print(description)
        stdin, stdout, stderr = self.exec_command(command, get_pty=True)
        print(stdout.read().decode('utf8'))
        print(stderr.read().decode('utf8'), file=sys.stderr)


@contextlib.contextmanager
def ssh_session(ip, key_filename):
    client = CustomSSHClient()
    client.load_system_host_keys()
    client.set_missing_host_key_policy(AutoAddPolicy())

    connected = False
    while not connected:
        try:
            client.connect(instance.ip_address,
                        username="ec2-user",
                        key_filename=os.path.expanduser("~/.ssh/loads.pem"))
        except NoValidConnectionsError:
            print("\rSSH connection not yet available", end="")
            sys.stdout.flush()
            time.sleep(10)
        else:
            print()
            connected = True

    print("\rSSH connection now sucessfully established.")
    try:
        yield client
    finally:
        print("\rSSH connection closing")
        client.close()


if __name__ == '__main__':

    ssh_key = os.path.expanduser("~/.ssh/loads.pem")

    with aws_instance() as instance:
        with ssh_session(instance.ip_address, ssh_key) as client:

            print("Installing Rust")
            client.execute('curl -sSf https://static.rust-lang.org/rustup.sh | sh')

            print("Installing system dependencies")
            client.execute('sudo yum install -y git gcc openssl-devel')

            print("Cloning git repository...")
            client.execute('git clone %s' % GIT_REPO)

            print("Creating the zip file...")
            client.execute('cd %s; make zip' % PROJECT_ROOT)

            print("Downloading the zip file...")
            sftp_client = SFTPClient.from_transport(client.get_transport())
            sftp_client.get("%s/%s" % (PROJECT_ROOT, ZIP_FILENAME), ZIP_FILENAME)
            sftp_client.close()
