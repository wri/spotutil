# gfw_create_spot_worker
CLI tool to create a spot worker on AWS and launch processes

Used by GFW staff to create / manage spot instances. Default instance ID is updated frequently to point at our preferred analysis AMI, which includes GDAL, gmt, and other common OSGEO packages.

Requires a `tokens` dir with .pem file to allow fab to enter the machine, in addition to proper AWS / EC2 permissions.

First time users: Try running

`aws s3 ls s3://gfw2-data/`

If this works, you should be good to go. If this does not work, you'll need to install aws command line client. This will put your aws credentials somewhere accessible by the tool.

Run
`pip install awscli`

When that completes, use your aws key and secret access key to establish aws credentials:
`aws configure`

Default region name: us-east-1
Default output format: json

```
usage: kickoff-spot-process.py [-h] [--ami-id AMI_ID] --instance-type
                               INSTANCE_TYPE [--price PRICE]
                               [--disk-size DISK_SIZE] [--tag TAG] [--putty]
                               [--prep-script PREP_SCRIPT]
                               [--main-script MAIN_SCRIPT]
```
