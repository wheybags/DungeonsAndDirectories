#!/usr/bin/env bash

set -ex

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

make_zip() {
  dir="$1"
  zipfile="$2"


  if [ "$(expr substr $(uname -s) 1 5)" == "MINGW" ]; then
    zipfile=`cygpath -w "$zipfile"`
    dir=`cygpath -w "$dir"`

    "$DIR/7z1900-extra/7za.exe" a "$zipfile" "$dir"
  else
    zip -r "$dir" "$zipfile"
  fi
}


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
make_zip dungeons_and_directories/ dungeons_and_directories_win64.zip

popd