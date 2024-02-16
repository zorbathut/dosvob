
import hashlib
import subprocess
import time
import os

from datetime import datetime, timedelta
from util import execute

def parse_duration(duration_str):
    """Convert a duration string into a timedelta object."""
    number, unit = duration_str.split()

    unit = unit.lower()
    number = int(number)

    if unit == "hour" or unit == "hr" or unit == "h" or unit == "hours":
        return timedelta(hours=number)
    elif unit == "day" or unit == "d" or unit == "days":
        return timedelta(days=number)
    elif unit == "week" or unit == "w" or unit == "weeks":
        return timedelta(weeks=number)
    elif unit == "month" or unit == "mo" or unit == "months":
        # Approximating a month as 30 days
        return timedelta(days=number * 30)
    elif unit == "year" or unit == "yr" or unit == "years":
        # Approximating a year as 365 days
        return timedelta(days=number * 365)
    else:
        raise ValueError(f"Unsupported time unit: {unit}")

def filter_snapshots(snapshots, kept_ids, retention_policy):
    """Filter snapshots based on the retention policy."""
    now = datetime.now()
    
    if 'last' in retention_policy:
        # just shove the recent ones in, done
        kept_ids.update([snapshot[1] for snapshot in snapshots[-retention_policy['last']:]])
    else:
        frequency = parse_duration(retention_policy['frequency'])
        duration = parse_duration(retention_policy['duration'])
        print("====== ", frequency, duration, "======")
        print(retention_policy)
        
        last_kept = None
        last_seen = None

        for snapshot in snapshots:
            if now - snapshot[0] > duration:
                # we're done here
                break

            if snapshot[1] in kept_ids:
                last_kept = snapshot
                last_seen = snapshot
                continue

            print(last_kept, snapshot, last_seen, frequency)
            if last_kept is not None:
                print(last_kept[0] - snapshot[0])
            
            if last_kept is None or last_kept[0] - snapshot[0] > frequency:
                # we need to add something!
                if last_seen is None or last_seen == last_kept:
                    # we *want* to add one in the middle, but we don't have one, so we'll add this one I guess
                    last_seen = snapshot
                
                # add last_seen
                print("yoink")
                kept_ids.add(last_seen[1])
                last_kept = last_seen
            
            last_seen = snapshot

    return kept_ids

def get_kept_snapshot_ids(snapshots, retention_policies):
    """Determine which snapshots to keep based on retention policies."""
    kept_ids = set()

    for policy in retention_policies:
        filter_snapshots(snapshots, kept_ids, policy)

    return kept_ids

def clear_git_retention(gitdir, retention_policies):
    """Retrieve git commits as (timestamp, commit hash) tuples."""
    # Define the command to get commit hashes and their author date in UNIX timestamp format
    command = ['git', '-C', gitdir, '--no-replace-objects', 'log', '--pretty=format:%at %H']
    result = subprocess.run(command, capture_output=True, text=True, check=True)
    
    # Parse the output
    snapshots = []
    for line in result.stdout.split('\n'):
        if line:
            timestamp, commit_hash = line.split()
            timestamp = datetime.fromtimestamp(int(timestamp))
            snapshots.append((timestamp, commit_hash))
    
    # Get the commit hashes
    to_keep = get_kept_snapshot_ids(snapshots, retention_policies)

    # sort to_keep by timestamp, so we can see what's going on
    to_keep = sorted(to_keep, key=lambda commit: snapshots[[snapshot[1] for snapshot in snapshots].index(commit)][0])

    # now print them all, including the time since the last timestamp
    last_timestamp = None
    for commit in to_keep:
        timestamp = snapshots[[snapshot[1] for snapshot in snapshots].index(commit)][0]
        if last_timestamp is not None:
            print(f"{commit} ({timestamp - last_timestamp})")
        else:
            print(f"{commit}")
        last_timestamp = timestamp

    # Convert the list into a format suitable for the git filter-repo command
    commits_to_keep_str = ','.join([f"'{tk}'" for tk in to_keep])

    # Command to run git filter-repo with a commit callback
    filter_repo_command = f"""
        git filter-repo --force --commit-callback "if commit.original_id.decode('utf-8') not in {{{commits_to_keep_str}}}:
            commit.skip()
        "
    """

    print(filter_repo_command)

    # Execute the git filter-repo command
    subprocess.run(filter_repo_command, cwd=gitdir, shell=True, check=True)

def hash_chunk(chunk):
    """Hash a chunk of data using SHA256."""
    hasher = hashlib.sha256()
    hasher.update(chunk)
    return hasher.hexdigest()

def chunkify_file(file_path, chunk_size=1024*1024):
    """Generator that reads a file in chunks."""
    with open(file_path, 'rb') as file:
        while True:
            chunk = file.read(chunk_size)
            if not chunk:
                break
            yield chunk

def store_chunk(chunk, hash, backupname):
    """Store chunk under backupname/chunks/hash."""
    chunks_dir = os.path.join(backupname, "glacier", "chunks", hash[:2])
    os.makedirs(chunks_dir, exist_ok=True)
    chunk_path = os.path.join(chunks_dir, hash)
    # if it already exists, we're good
    if os.path.exists(chunk_path):
        return
    
    with open(chunk_path, 'wb') as chunk_file:
        chunk_file.write(chunk)

def do_glacier_pass(backupname, retention_policies):
    # for every file in backupname, not recursively, break it into 1mb chunks, hash each chunk, store the chunk under backupname/chunks/hash, and append the hash to backupname/glacier/history
    for item in os.listdir(backupname):
        item_path = os.path.join(backupname, item)
        history_file_path = os.path.join(backupname, "glacier", "history", item)
        with open(history_file_path, 'w') as history_file:
            if os.path.isfile(item_path):
                for chunk in chunkify_file(item_path):
                    hash = hash_chunk(chunk)
                    store_chunk(chunk, hash, backupname)
                    history_file.write(hash + '\n')

    execute(f"git -C {backupname}/glacier/history add .")
    execute(f"git -C {backupname}/glacier/history commit -m 'dosvob backup'")

    # cull retention
    # currently disabled
    #clear_git_retention(f"{backupname}/glacier/history", retention_policies)

    # later we'll start GC'ing it, but for now we're just going to leave it
