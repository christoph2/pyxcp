#!/bin/env bash
git shortlog -sne --all | cut -f2,3 | sort > CONTRIBUTORS
