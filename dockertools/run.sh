#!/bin/sh
ssh-keygen -f ~/.ssh/id_rsa
crond -f -l 8
