import api
import datetime
import json
import os
import pathlib
import requests
import time

from glacier import do_glacier_pass
from util import execute
    
dosvob_ephemeral_tag = "dosvob-ephemeral"
has_dosvob_ephemeral_tag = lambda item: dosvob_ephemeral_tag in item["tags"]
conf = json.loads(pathlib.Path("conf.json").read_text())
token = conf["do_token"]
region = conf["region"]

dosvob_key_name = f"{dosvob_ephemeral_tag}-key"

# Healthchecks
if conf["healthchecks"] != "":
    requests.get(f"{conf['healthchecks']}/start", timeout=10)

# Setup
manager = api.BaseAPI(token = token)
pathlib.Path('backups/glacier/history').mkdir(parents=True, exist_ok=True)
if not os.path.exists("backups/glacier/history/.git"):
    execute("git -C backups/glacier/history init")

# Cleans up everything related to dosvob's execution
def cleanup():
    # Clear droplets first because they might mount volumes
    for droplet in manager.request("droplets", "GET", { 'tag_name': dosvob_ephemeral_tag })["droplets"]:
        manager.request(f"droplets/{droplet['id']}", "DELETE")

    # Clear snapshots next to give volumes time to demount properly (this may or may not be helpful; if it is, solve it better)
    for snapshot in filter(has_dosvob_ephemeral_tag, manager.request("snapshots", "GET")["snapshots"]):
        manager.request(f"snapshots/{snapshot['id']}", "DELETE")

    # Clear volumes once the droplet is probably shut down
    # For some reason, tagging volumes doesn't seem to work right, so we do it with name prefixes instead
    for volume in filter(lambda item: item["name"].startswith(dosvob_ephemeral_tag), manager.request("volumes", "GET")["volumes"]):
        manager.request(f"volumes/{volume['id']}", "DELETE")
    
    # Clear SSH keys that we inserted
    actionresult = manager.request(f"account/keys", "GET")
    for key in actionresult["ssh_keys"]:
        if key["name"] == dosvob_key_name:
            manager.request(f"account/keys/{key['id']}", "DELETE")

try:
    # Waits for an action to be complete
    def waitfor(id):
        while True:
            actionresult = manager.request(f"actions/{id}", "GET")
            if actionresult["action"]["status"] == "completed":
                return
            elif actionresult["action"]["status"] == "in-progress":
                time.sleep(5)
            else:
                raise RuntimeError

    # Clean up first, just so we're not stomping all over an old process
    cleanup()

    # Insert our SSH key
    sshkeyid = manager.request(f"account/keys", "POST", {
            'name': dosvob_key_name,
            'public_key': pathlib.Path("~/.ssh/id_rsa.pub").expanduser().read_text(),
        })["ssh_key"]["id"]

    # Build the droplet that we'll be using for rsync
    workerresponse = manager.request("droplets", "POST", {
            'name': f'{dosvob_ephemeral_tag}-worker',
            'region': region,
            'image': 'debian-10-x64',
            'size': 's-1vcpu-1gb',
            'tags': [ dosvob_ephemeral_tag ],
            'ssh_keys': [ sshkeyid ],
        })
    workerid = workerresponse["droplet"]["id"]
    waitfor(workerresponse["links"]["actions"][0]["id"])

    # Droplet starts in a powered-on state

    # Get the external IP so we can connect to it
    workeriplist = manager.request(f"droplets/{workerid}", "GET")["droplet"]["networks"]["v4"]
    workerip = next(x for x in workeriplist if x["type"] == "public")["ip_address"]
    print(f"Worker found at IP {workerip}")

    # Install go, which we need for diskrsync; this also accepts our ssh key
    # we actually need to retry every second until we succeed because it now takes a bit for the server to come up
    while True:
        try:
            execute(f"ssh -o StrictHostKeyChecking=no root@{workerip} apt install -y golang")
            break
        except:
            time.sleep(1)
    
    # And now get diskrsync copied over
    execute(f"scp /usr/local/bin/diskrsync root@{workerip}:/usr/local/bin/diskrsync")

    snapshotslug = datetime.datetime.utcnow().strftime("%Y%m%d-%H%M%S")

    # Traverse over all volumes
    volumes = manager.request("volumes", "GET")["volumes"]
    for volume in volumes:
        # Snapshot a volume
        # Volume name length limited to 64 so we unfortunately have to limit our embedded name
        name = f"dosvob-ephemeral--{volume['name'][:12]}--{snapshotslug}"
        result = manager.request(f"volumes/{volume['id']}/snapshots", "POST", {
                'name': name,
                'tags': [ dosvob_ephemeral_tag ],
            })["snapshot"]
        
        # Make a volume from our snapshot
        snapshotid = result["id"]
        volumecopy = manager.request("volumes", "POST", {
                'name': name,
                'size_gigabytes': result["min_disk_size"],
                'snapshot_id': snapshotid,
                'tags': [ dosvob_ephemeral_tag ],
            })["volume"]
        volumecopyid = volumecopy["id"]
        
        # Wipe the snapshot
        manager.request(f"snapshots/{snapshotid}", "DELETE")

        # Attach the volume to our worker
        waitfor(manager.request(f"volumes/{volumecopyid}/actions", "POST", {
                'type': 'attach',
                'droplet_id': workerid,
            })["action"]["id"])
        
        # Volume always shows up as sda, so let's sync it over
        execute(f"diskrsync --verbose --calc-progress --sync-progress --no-compress root@{workerip}:/dev/sda backups/{volume['name']}")

        # Detach volume
        waitfor(manager.request(f"volumes/{volumecopyid}/actions", "POST", {
                'type': 'detach',
                'droplet_id': workerid,
            })["action"]["id"])
        
        # Delete volume
        manager.request(f"volumes/{volumecopyid}", "DELETE")

    do_glacier_pass("backups", conf["snapshot_retention"])

    if conf["healthchecks"] != "":
        requests.get(f"{conf['healthchecks']}", timeout=10)

except:
    print("Error! Cleaning up before returning.")
    if conf["healthchecks"] != "":
        requests.get(f"{conf['healthchecks']}/fail", timeout=10)
    raise
finally:
    # Cleanup everything remaining
    cleanup()

    # this is here entirely so I can easily comment out the cleanup when I'm developing :V
    pass
