# Updating the spot AMI


### Launching a temporary instance
1. Go to AWS console --> EC2 --> AMIs

2. Grab the current AMI id from the [spotutil repo](https://github.com/wri/spotutil/). This is likely in spotutil/spotutil.py, where it's stored as the default argument for the `spotutil new` command.

3. Filter the list of AMIs in the AWS console by this ID.

4. Right click on the AMI id, and select launch. we're going to launch a regular (non-spot) machine from our current AMI

5. this will bring us to the instance type screen- pick `m4.large` with:
- network: WRI-MAIN
- subnet: subnet-c9679abe | us-east-1c

6. hit the add storage button and then accept the default (should be 8 gb or 16 gb- we want to keep this small)

7. go to add tags, then continue (no tags necessary)

8. go to add security group, then select CUSTOM-TERRA-ANALYSIS-SERVER

9. then REVIEW AND LAUNCH & LAUNCH

10. choose an existing key pair that you have access to (likely chofmann_wri)

### connect to the instance

You should be redirected to the EC2 page of the AWS console. once there, click on your instance in the table and give it a temporary name.

Now ssh / putty in using the public IP listed for your instance 


### Installing various software packages

Install 'em!

### create the AMI

1. go back to the EC2 console, and stop the instance you just created
2. right click on it --> Image --> Create image
3. in the create image view, name it something like `GDAL-PROCESSOR-20181108`


### Test AMI & update spotutil
Wait until the AMI is created, then go back to the spotutil repo and find where the default AMI id is set. Add your new AMI id, and then reinstall the library on your machine:

`pip install .`

Create a new test machine `spotutil new m4.large`, then ssh in and check to be sure your libraries have been installed properly.

### Clean up + commit

Terminate your spot machine and your temporary EC2 instance from which you made the image.

Commit your updates to spotutil and ask your coworkers to please reinstall so they have the latest AMI (either git pull and then reinstall if they have it locally, or pip install git+https://github.com/wri/spotutil/). Fun!


