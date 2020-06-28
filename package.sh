#!/usr/bin/env bash

set -ex

if [ -e packages ]; then rm -rf packages; fi
mkdir packages

cd packages


mkdir -p windows/dungeons_and_directories/assets
pushd windows/dungeons_and_directories/assets

mkdir python
cd python
unzip ../../../../../python-3.8.3-embed-amd64.zip
cd ..

cp -r ../../../../images .
cp ../../../../*.py .

cd ..
cp -r ../../../run_windows.bat run_dungeons_and_directories.bat

cd ..
zip -r dungeons_and_directories/ dungeons_and_directories_win64.zip

popd