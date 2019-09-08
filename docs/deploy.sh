#!/bin/sh

last_commit_hash=`git log --format=%H -1`

setup_git() {
  git config --global user.email "travis@travis-ci.org"
  git config --global user.name "Travis CI"
}

commit_website_files() {
  pip install sphinx
  cd ../../
  git clone --branch=master https://github.com/mccartnm/hivemind-docs.git mccartnm/hivemind-docs
  cd mccartnm/hivemind/docs
  make github
  cd ../../hivemind-docs
  git remote rm origin
  git remote add origin https://user:${GH_TOKEN}@github.com/mccartnm/hivemind-docs.git
  git add -A
  git commit --message "Travis build: $TRAVIS_BUILD_NUMBER - From Hash: $last_commit_hash"
  git push --quiet origin master
}

setup_git
commit_website_files
