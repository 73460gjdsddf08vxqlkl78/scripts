#!/bin/bash
WORKSPACE=$1

cp src/scf_bootstrap $WORKSPACE
pushd $WORKSPACE
    zip -r package.zip *
popd