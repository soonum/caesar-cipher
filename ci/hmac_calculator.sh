#!/usr/bin/env bash

#
# Compute a Hmac signature by providing a filepath and a secret key encoded as hexadecimal.
#

if [ $# -lt 2 ]; then
  echo "Not enough argument provided"
  echo "Usage: hmac_calculator.sh <Filepath> <SecretKey>"
  exit 1
fi

FILE_PROVIDED="$1"
SECRET_KEY="$2"

if [ ! -f "${FILE_PROVIDED}" ]; then
  echo "File $FILE_PROVIDED doesn't exist"
  exit 1
fi

if [ -z "$SECRET_KEY" ]; then
  echo "Hmac secret is empty"
  exit 1
fi

# Compute HMAC signature.
openssl sha256 -hmac "$SECRET_KEY" < "${FILE_PROVIDED}" | sed -e 's/^.* //'
