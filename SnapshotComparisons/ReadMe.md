# SnapshotComparison

A small python tool to allow the user to check/verify the service limits, usages, and quota policies of an OCI tenancy. The tool will also take snapshots of the tenancy's service limits and check if any services have been provisioned or removed.

## Getting Started

These instructions will get you a copy of the project up and running on your local machine for development and testing purposes.

### Prerequisites

To use this tool, you will need to generate API keys and retrieve the OCIDs of the user and tenancy you will be accessing.
Instructions on how to do so can be found here: https://docs.cloud.oracle.com/en-us/iaas/Content/API/Concepts/apisigningkey.htm


You will also need to create a config file. Instructions can be found in the link above.
When you are done, your config file should look something like this.
```
[DEFAULT]
tenancy = ocid1.tenancy.oc1..xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
user = ocid1.user.oc1..xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
fingerprint = 00:00:00:xx:00:00:0x:00:00:x0:00:00:0x:00:0x:00
key_file = ~\.oci\oci_api_key.pem
region = eu-frankfurt-1
pass_phrase = password
```

### Installing

Download the project from GitHub with your prefered IDE and run.
Make sure you change the location variable in Snapshot to point to a local directory where the limit snapshots will be saved/retrieved

## Built With

* Python3

# Author
* **Shem Cheng** - [Jeshem] (https://github.com/Jeshem)