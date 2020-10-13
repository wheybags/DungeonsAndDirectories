#!/usr/bin/env bash

set -euxo pipefail

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$DIR"

make_zip() {
  dir="$1"
  zipfile="$2"


  if [ "$(expr substr $(uname -s) 1 5)" == "MINGW" ]; then
    zipfile=`cygpath -w "$zipfile"`
    dir=`cygpath -w "$dir"`

    "$DIR/7z1900-extra/7za.exe" a "$zipfile" "$dir"
  else
    zip -r "$zipfile" "$dir"
  fi
}

package_common() {
  cp -r "$DIR/images" .
  cp -r "$DIR/resources" .
  cp "$DIR/"*.py .
}

package_win() {
  mkdir -p packages/windows/dungeons_and_directories/assets
  pushd packages/windows/dungeons_and_directories/assets

  mkdir python
  cd python
  unzip ../../../../../python-3.8.3-embed-amd64.zip
  cd ..

  package_common

  cd ..
  cp -r ../../../run_windows.bat run_dungeons_and_directories.bat

  popd

  cd packages/windows
  make_zip dungeons_and_directories "$DIR/packages/dungeons_and_directories_windows_amd64.zip"
  cd ..
  rm -rf windows
}

package_linux() {
  mkdir -p packages/linux/dungeons_and_directories/assets
  pushd packages/linux/dungeons_and_directories/assets

  package_common

  cd ..
  echo '#!/bin/bash' >> run_dungeons_and_directories.sh
  echo 'DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"' >> run_dungeons_and_directories.sh
  echo 'cd "$DIR"' >> run_dungeons_and_directories.sh
  echo './assets/game.py' >> run_dungeons_and_directories.sh
  chmod +x run_dungeons_and_directories.sh

  popd

  cd packages/linux
  make_zip dungeons_and_directories "$DIR/packages/dungeons_and_directories_linux_amd64.zip"
  cd ..
  rm -rf linux
}

package_osx() {
  mkdir -p packages/osx/dungeons_and_directories.app/Contents/MacOS/assets
  pushd packages/osx/dungeons_and_directories.app/Contents/MacOS/assets

  package_common

  cd ..
  
  echo '#!/bin/bash' >> dungeons_and_directories
  echo 'DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"' >> dungeons_and_directories
  echo 'cd "$DIR"' >> dungeons_and_directories
  echo 'open -a Terminal ./assets/game.py' >> dungeons_and_directories

  chmod +x dungeons_and_directories

  popd

  cd packages/osx
  make_zip dungeons_and_directories.app "$DIR/packages/dungeons_and_directories_osx.zip"
  cd ..
  rm -rf osx
}



if [ -e packages ]; then rm -rf packages; fi

package_win
package_linux
package_osx
