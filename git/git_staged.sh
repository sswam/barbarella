#!/bin/sh
git diff --cached --name-status | kut_perl.pl -o 1 | tr '\t' '\n'