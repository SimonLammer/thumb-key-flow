#!/bin/sh

F="text.txt"

touch "$F"
for sample in german-tweet-sample-*; do
  unzip "$sample"
  for rec in recording-*.json.gz; do
    gunzip "$rec"
    jq -r '.[].text + "\n\n"' recording-*.json >> "$F"
    rm recording-*.json
  done
  rm recording-*
done

