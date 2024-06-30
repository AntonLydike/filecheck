#!/usr/bin/env bash
# simple script to strip check lines out of test files so that we can use them for tests

sed '/^\/\//d' < "$@"
