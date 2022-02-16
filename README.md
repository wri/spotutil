# spotutil

## Introduction
Command line tool to create, kill and list ec2 spot workers on AWS

Used by GFW staff to create / manage spot instances. 
Default instance ID depends on the instance type created. 
For most instance types, a generic analysis AMI, which includes GDAL and other common OSGEO packages, is used.
For r5d instances, a specific AMI and launch template are used that are configured to run the forest carbon flux model
(https://github.com/wri/carbon-budget).

## Requirements
Requires a `tokens` dir with .pem file to allow fab to enter (SSH into) the machine, in addition to proper AWS / EC2 permissions.


## Set-up
Try running

`aws s3 ls s3://gfw2-data/`

If this works, you should be good to go to continue to the **Install spotutil** section. If this does not work, you'll need to install aws command line client. This will put your aws credentials somewhere accessible by the tool.

Run

`pip install awscli`

When that completes, use your aws key and secret access key to establish aws credentials:

`aws configure`

Default region name: us-east-1

Default output format: json

## Install spotutil

The tool is written to be run from any directory. There are two ways to install it as a system command that can be run from anywhere.

1. `pip install git+http://github.com/wri/spotutil`
2. In the folder where spotutil is located on your computer (e.g., C:\Users\xyz\Git\spotutil): `pip install .` (requires pip)

Once setup is complete, the tool can be run from any directory.

## Using spotutil

###Create a spot instance

`spotutil new <instance_type> <key_pair>`

Instance types commonly used: m4.large, m4.xlarge, m4.2xlarge, m4.4xlarge, m4.10xlarge, m4.16xlarge,
r4.large, r4.xlarge, r4.2xlarge, r4.4xlarge, r4.8xlarge, r4.16xlarge,
r5d.large, r5d.xlarge, r5d.2xlarge, r5d.4xlarge, r5d.8xlarge, r5d.12xlarge, r5d.16xlarge, r5d.24xlarge.

For `<key_pair>` use name for any key pair registered with your AWS account. 
Make sure you are in possession of the private key. You will need it to SSH into the machine


####Creating and Puttying into r5d instances

Providing an r5d instance type automatically launches an instance configured to run the forest carbon flux model,
including all the user data found in the launch template.
The `--carbon-flux` flag can optionally be added to r5d instances. The `--carbon-flux` flag cannot be added to other
instance type requests. (e.g., m4 and r4). For flux model runs, `--launch-template` and `--launch-template-version` can
also optionally be specified if the user does not want to use the default template or version. The current template is
carbon_flux_model_python3_v2 
(https://console.aws.amazon.com/ec2/v2/home?region=us-east-1#LaunchTemplateDetails:launchTemplateId=lt-00205de607ab6d4d9).

If you create an r5d instance, you must Putty into it within the first two or three minutes after it is created.
For unclear reasons, r5d instances block new Putty connections after a few minutes.
(The error box says: "Network error: Software caused connection abort.")

Also, when Puttying into r5d instances, supply the r5d_ec2.ppk for Connection -> SSH -> Auth -> Private Key File  
instead of your `<username>_wri.ppk`. r5d instances require r5d_ec2.ppk instead of `<username>_wri.ppk`
due to the launch template being used. Still use your personal key_pair in the command line
when you create the spot instance, though; this is just a change to what is supplied to Putty. Ask David Gibbs or Erin
Glen for this specific ppk.

### List the active spots instances

`spotutil ls`

This shows a table of all active spot instances, with columns showing the user,
instance type, internal IP address, external IP address, and up time. 

### Remove an active spot instance

Multiple instances can be deleted at the same time using the username or instance type arguments. 

`spotutil rm [--username][--interal_ip][--external_ip][--instance_type]`

Example: `spotutil rm --username David.Gibbs`
Example: `spotutil rm --internal_ip 192.168.80.30`
Example: `spotutil rm --instance_type m4.2xlarge`


