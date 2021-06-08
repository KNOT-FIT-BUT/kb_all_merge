#!/bin/bash
# Author: Tomas Volf, ivolf@fit.vutbr.cz

# default values
SAVE_PARAMS=$*

# saved values
LAUNCHED=$0

#=====================================================================
# nastavovani parametru prikazove radky

usage()
{
  echo "Usage: deploy.sh -v <KB version> -u [<login>] [--dev]"
  echo ""
  echo -e "\t-h, --help             Show this help help message and exit."
  echo -e "\t-u [<login>=${USER}]   Upload (deploy) KB to webstorage via given login (default current user)."
  echo -e "\t-v <version>           Select specific version of KB to work with."
  echo -e "\t--dev                  Development mode (upload to separate space to prevent forming a new production version of KB)."
  echo ""
}

DEPLOY=false

if test $# -eq 0
then
  usage
  exit
fi

while [ "$1" != "" ]; do
  PARAM=`echo $1 | awk -F= '{print $1}'`
  # VALUE=`echo $1 | awk -F= '{print $2}'`
  case $PARAM in
    -h | --help)
      usage
      exit
    ;;
    -u)
      DEPLOY=true
      VALUE=`echo $2`
      if test "${VALUE}" != "" -a "${VALUE:0:1}" != "-"
      then
        DEPLOY_USER=$VALUE
        shift
      else
        DEPLOY_USER=$USER
      fi
    ;;
    -v)
      KB_VERSION=`echo $2`
      shift
    ;;
    --dev)
      DEPLOY_DEV_SUBDIR=dev
    ;;
    *)
      >&2 echo "ERROR: unknown parameter \"$PARAM\""
      usage
      exit 1
    ;;
  esac
  shift
done


if test -t "${KB_VERSION}"
then
  >&2 echo "ERROR: Unspecified KB version."
  usage
  exit 10
fi

# Deploy new KB to server if it is required
if $DEPLOY
then
  VERSION_PARTS=(${KB_VERSION//_/ })
  DEPLOY_LANG=${VERSION_PARTS[0]}

  # Change directory to outputs
  DIR_LAUNCHED=`dirname "${LAUNCHED}"`
  if test "${DIR_LAUNCHED::1}" != "/"
  then
    DIR_LAUNCHED=`readlink -f "${DIR_LAUNCHED}"`
  fi
  DIR_WORKING="${DIR_LAUNCHED}/outputs/${DEPLOY_LANG}"
  cd "${DIR_WORKING}" 2>/dev/null

  if test $? != 0
  then
    >&2 echo "ERROR: Missing output files directory."
    usage
    exit 20
  fi

  DEPLOY_WPEDIA_KB_BASEPATH=${DIR_WORKING}/../../kb_resources/kb_cs_wikipedia/outputs
  DEPLOY_MERGED_KB_BASEPATH=${DIR_WORKING}
  DEPLOY_VERSION_OLD=`cat ${DEPLOY_WPEDIA_KB_BASEPATH}/VERSION`
  DEPLOY_CONNECTION="${DEPLOY_USER}@minerva3.fit.vutbr.cz"
  DEPLOY_FOLDER_OLD="/mnt/knot/www/NAKI_CPK/${DEPLOY_DEV_SUBDIR}/NER_CZ_inputs/kb/${DEPLOY_VERSION_OLD}"
  DEPLOY_FOLDER_GKB="/mnt/knot/www/NAKI_CPK/${DEPLOY_DEV_SUBDIR}/NER_ML_inputs/KB/KB_${DEPLOY_LANG}/KB_${KB_VERSION}"

  echo "### Old Wikipedia KB ###"
  echo "Creating new folder: ${DEPLOY_FOLDER_OLD}"
  ssh "${DEPLOY_CONNECTION}" "mkdir -p \"${DEPLOY_FOLDER_OLD}\""
  echo "Upload files to new folder: ${DEPLOY_FOLDER_OLD}"
  scp ${DEPLOY_WPEDIA_KB_BASEPATH}/VERSION ${DEPLOY_WPEDIA_KB_BASEPATH}/HEAD-KB ${DEPLOY_WPEDIA_KB_BASEPATH}/KBstatsMetrics.all "${DEPLOY_CONNECTION}:${DEPLOY_FOLDER_OLD}"
  echo "Change symlink of new to this latest version of KB"
  ssh "${DEPLOY_CONNECTION}" "cd \"`dirname "${DEPLOY_FOLDER_OLD}"`\"; ln -sfT \"${DEPLOY_VERSION_OLD}\" new"
  echo
  echo "### GENERIC KB ###"
  echo "Creating new folder: ${DEPLOY_FOLDER_GKB}"
  ssh "${DEPLOY_CONNECTION}" "mkdir -p \"${DEPLOY_FOLDER_GKB}\""
  echo "Upload files to new folder: ${DEPLOY_FOLDER_GKB}"
  scp ${DEPLOY_MERGED_KB_BASEPATH}/KB_${KB_VERSION}.tsv "${DEPLOY_CONNECTION}:${DEPLOY_FOLDER_GKB}/KB+versions.tsv"
  scp ${DEPLOY_MERGED_KB_BASEPATH}/KB_${KB_VERSION}_without_versions.tsv "${DEPLOY_CONNECTION}:${DEPLOY_FOLDER_GKB}/KB.tsv"
  echo "Change symlink of new to this latest version of KB"
  ssh "${DEPLOY_CONNECTION}" "cd \"`dirname "${DEPLOY_FOLDER_GKB}"`\"; ln -sfT \"KB_${KB_VERSION}\" new"
fi