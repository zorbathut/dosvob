dosvob
---

dosvob is a quick-and-dirty DigitalOcean image backup system. It is intended for people trying to back up relatively small amounts of high-speed online storage onto a local cheaper-per-gigabyte storage system, likely using hard drives.

If you have a million-dollar company that relies on dozens of terabytes of data, you should probably not use dosvob. If you have a small side project where it would be really annoying to lose a few dozen gigabytes, dosvob might be a good choice.

dosvob backs up into simple disk image files, suitable for mounting using a loopback device or for `dd`'ing onto a blank device. This is the most perfect reproduction possible, and tends to be both easy and reliable to restore in a disaster. It's also kind of a pain to do anything else with. YMMV.

### Usage

* Download the latest version of dosvob.
* Copy `conf.json.example` to `conf.json`.
* Visit the [DigitalOcean tokens page](https://cloud.digitalocean.com/account/api/tokens) and generate a token.
* Copy-paste that token into the `do_token` field in `conf.json`.
* Update the `region` field in `conf.json`.
* `python dosvob.py`

Wait. A sync takes about a minute of setup, plus maybe fifteen seconds of further setup per volume. On your first sync it will have to download the entire volume; on subsequent syncs it will have to read the entire volume from your disk and download only changed segments. Performance will vary roughly as expected based on amount of data, Internet speed, and disk speed.

Volumes are placed in the `backups` directory, named after the volume backed up. If you want to keep multiple revisions, that is currently up to you. Personally, I recommend storing the directory on ZFS and using snapshots.

You should probably set it up to run on a schedule. The details of this are left up to you, at least until I make a Dockerfile for it.

### Usage, Docker

* Download the latest version of dosvob.
* Copy `conf.json.example` to `conf.json`.
* Visit the [DigitalOcean tokens page](https://cloud.digitalocean.com/account/api/tokens) and generate a token.
* Copy-paste that token into the `do_token` field in `conf.json`.
* Update the `region` field in `conf.json`.
* `docker-compose up -d`

### How It Works

DigitalOcean volumes can only be read while mounted, and can be mounted to only one system at a time. I didn't want to require shutting down your servers and unmounting their volumes, but there's only one way to get data out of a mounted volume: snapshot it. You can't read a snapshot directly, but you can create a volume from it. You also can't read a volume directly, so dosvob spins up a small special-purpose droplet (cost as of this writing: approximately 0.7 cents per hour) solely to mount it and transfer data. Once this is done, the droplet, snapshot, and duplicated volume are deleted.

Technically this costs money, but given how quickly the whole process finishes, it doesn't cost a significant amount.

### Caveats

dosvob was written for my own purposes and currently contains the minimum required featureset for what I needed. Pull requests accepted graciously; feature-request issues may be handled based on how cheerful I'm feeling and how annoying it is. (Bribes accepted very graciously! But seriously, the code's documented, it'd probably be cheaper to do it yourself.)

dosvob creates snapshots, volumes, and a single droplet, all of which cost money. It cleans all of this up at the end, but if that's buggy, or gets interrupted by an Internet outage, power outage, or process termination, then it may keep costing you money until you notice. This is officially not my responsibility. It'll clean up old runs automatically on startup, but that of course won't refund your money. In theory, the worst-case scenario is a copy of your single largest volume, plus $5/mo for the droplet, but maybe something goes really wrong, I don't know.

dosvob will automatically delete things that have the `dosvob-ephemeral` tag or are prefixed with `dosvob-ephemeral`. If you have anything like that in your account, you probably shouldn't use this. Also, that's a *really* weird coincidence, seriously, man.

dosvob currently handles only a single region. This is entirely fixable, I just don't care right now because all my stuff is in a single region. I'd be happy to fix it if you need it fixed.

dosvob currently backs up all your volumes. There is no way to specify that a volume shouldn't be backed up.

dosvob doesn't back up droplets. I actually don't know if this is solvable. (Maybe?) Importantly, I don't need it, so I haven't looked into it.

dosvob does not deal well with volumes above 20gb. This is due to some limitations of rsync and an ugly workaround that I used due to being lazy. There's ways to fix this, I just haven't bothered. Let me know if this is a problem for you. A few months from now, I guarantee I'm going to forget about this, make a large volume, fail to back it up, and feel like an idiot, then have to fix it myself.

dosvob doesn't keep multiple versions in any useful way; that's currently left up to whoever is running it.

I give no guarantee that the disk format is stable. If you blindly sync a new version, it may have an entire new disk format that it starts from scratch without warning you. It won't clobber old data without warning (this *is* a guarantee!)

dosvob (intentionally!) does not shut down droplets before snapshotting volumes. This means your backup may be in an inconsistent state, roughly equivalent to what you'd get if you hard-shutdown a droplet instead of shutting it down gracefully. This is a thing you're not supposed to do and may result in a nonworking backup. In my experience, it works surprisingly often (I've never had a failure, in fact!), and also I'm pretty lazy and don't want to try figuring out a more reliable solution. Also, I run low-load servers without anything critical on them. I recommend keeping several recent versions, which will sharply mitigate the chance of not having a working backup; I also recommend testing your backups.

**This program was written by one dude over the course of one night when he should have been going to bed and one morning when he hadn't really gotten enough sleep and was scrambling to get it done before he had to get to work. There is no warranty. There are no guarantees. If it deletes all of your data, I'll shrug and say "sorry", and also kind of silently judge you behind my monitor. If you are using this for anything of importance, you should audit the code, test the backups, and continue to verify them regularly. To quote the end of the license: THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.**