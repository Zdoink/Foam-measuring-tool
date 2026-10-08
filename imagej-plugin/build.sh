#!/usr/bin/env bash
# Builds Foam_Binary_Ring.jar.
# Usage: ./build.sh path/to/ij.jar
# (ij.jar is in your ImageJ folder, or Fiji.app/jars/ij-*.jar)
set -e
cd "$(dirname "$0")"
IJ_JAR="${1:?Usage: ./build.sh path/to/ij.jar}"
rm -rf build && mkdir -p build
javac --release 8 -nowarn -cp "$IJ_JAR" -d build src/Foam_Binary_Ring.java
cp src/plugins.config build/
(cd build && jar cf ../Foam_Binary_Ring.jar plugins.config *.class)
rm -rf build
echo "Built Foam_Binary_Ring.jar"
