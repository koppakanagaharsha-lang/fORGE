#!/usr/bin/env bash
npm install -g clawhub-cli -q 2>&1 | tail -2
command -v claw && claw --version || echo "claw install failed"
