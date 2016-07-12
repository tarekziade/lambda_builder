import time
import os
import sys
import contextlib
import json

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
INSTANCE_ARN = 'arn:aws:iam::927034868273:instance-profile/tarekLambda'


@contextlib.contextmanager
def aws_instance(region, ami_id, key_pair, instance_type,
                 instance_name, instance_project,
                 instance_profile_arn):
    # Connect to the AWS region
    print("Connecting to %s" % region)
    conn = connect_to_region(region, is_secure=True)

    # Create a Amazon Lambda AMI EC2 instance
    print("Starting an new instance of %s" % ami_id)
    reservations = conn.run_instances(ami_id,
                                    min_count=1, max_count=1,
                                    key_name=key_pair,
                                    instance_type=instance_type,
                                    instance_profile_arn=instance_profile_arn)

    instance = reservations.instances[0]

    # Tag the instance
    conn.create_tags([instance.id], {
        "Name": instance_name,
        "Projects": instance_project,
    })
    print("Instance Name:", instance_name)

    # Wait for the instance to be ready
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
            client.connect(ip,
                        username="ec2-user",
                        key_filename=key_filename)
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



def create_zip(git_repo, project_root, zip_filename, ssh_key,
               s3_bucket, aws_region=AWS_REGION, ami_id=AMI_ID,
               key_pair=KEY_PAIR,
               instance_type=INSTANCE_TYPE, instance_name=INSTANCE_NAME,
               instance_project=INSTANCE_PROJECT,
               instance_profile_arn=INSTANCE_ARN):

    with aws_instance(aws_region, ami_id, key_pair, instance_type,
                      instance_name, instance_project,
                      instance_profile_arn) as instance:
        with ssh_session(instance.ip_address, ssh_key) as client:
            print("Installing Rust")
            client.execute('curl -sSf https://static.rust-lang.org/rustup.sh | sh')

            print("Installing system dependencies")
            client.execute('sudo yum install -y git gcc openssl-devel')

            print("Cloning git repository...")
            client.execute('git clone %s' % git_repo)

            print("Creating the zip file...")
            client.execute('cd %s; make zip' % project_root)

            print("Uploading the zip file to S3...")
            client.execute('cd %s; aws s3 cp %s s3://%s/%s --acl public-read' % (project_root,
                zip_filename, s3_bucket, zip_filename))

            print("File URL: https://%s.s3.amazonaws.com/%s" % (
                    s3_bucket, zip_filename))

            print("Updating the Lambda function")
            cmd = ("aws lambda update-function-code --s3-bucket %s --s3-key %s "
                   "--function-name tarekPoll --region us-west-2")
            client.execute(cmd % (s3_bucket, zip_filename))

            print("Run it!")

            # XXX put in an option
            payload = {"s3_bucket": "firefoxpoll",
                       "s3_filename": "updates.json",
                       "kinto_url":
                       "https://firefox.settings.services.mozilla.com/v1/buckets/monitor/collections/changes/records"}

            cmd = ("aws lambda invoke --function-name tarekPoll "
                   "--region us-west-2 --payload '%s' output.txt" %
                   json.dumps(payload))
            client.execute(cmd)
            client.execute("cat output.txt")

            return zip_filename
