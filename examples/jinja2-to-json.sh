#!/usr/bin/env bash
# removes comment lines
# escapes " double quotes
# removes newlines

< "$1" sed 's/^##.*$//gm' | sed 's/"/\\"/gm' | tr -d '\n'
