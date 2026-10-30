# Locations of the BEAST jar, the two BEAGLE builds and EigenJNI.
# Source this file (". scripts/env.sh") after editing the paths for a global
# installation; the defaults are the paths inside the Docker image.
export BEAST_JAR="${BEAST_JAR:-/app/beast-mcmc/build/dist/beast.jar}"
export BEAGLE_FAST_LIB="${BEAGLE_FAST_LIB:-/opt/beagle-fast/lib}"
export BEAGLE_SLOW_LIB="${BEAGLE_SLOW_LIB:-/opt/beagle-slow/lib}"
export EIGENJNI_LIB="${EIGENJNI_LIB:-/opt/eigenjni/lib}"
