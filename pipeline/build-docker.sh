#!/bin/bash

# Get image repository.
REPO=$1
if [ -z "$REPO" ]; then
  echo "Usage: $0 <repository> [tag]"
  exit 1
fi

# Get image tag.
TAG=$2
if [ -z "$TAG" ]; then
  TAG=v$(date +%Y%m%d%H%M)
fi

# Build image.
docker build -t $REPO:$TAG .
docker tag $REPO:$TAG $REPO:latest

# Push image.
docker push $REPO:$TAG
docker push $REPO:latest