from boto.awslambda import connect_to_region


def upload_function(zipfile, execution_role, funcname, account_id,
                    handler, region="us-west-2"):

    print("Connecting to %s" % region)
    conn = connect_to_region(region, is_secure=True)

    with open(zipfile) as f:
        role_arn = 'arn:aws:iam::%s:role/%s' (account_id, execution_role)


        aws_lambda.upload_function(funcname, f.read(), "python", role_arn,
                                   handler, "event", description=None,
                                   timeout=60, memory_size=128)
