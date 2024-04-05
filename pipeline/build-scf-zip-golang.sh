#!/bin/bash
WORKSPACE=bin
export GOOS=linux
export GOARCH=amd64
export CGO_ENABLED=0

# Cleanup build folder.
rm -rf $WORKSPACE
mkdir -p $WORKSPACE

# Build Go binary.
pushd src
    go build -ldflags "-s -w" -o ../$WORKSPACE .
popd

# Pack files.
cp src/scf_bootstrap $WORKSPACE
pushd $WORKSPACE
    zip bin.zip *
popd