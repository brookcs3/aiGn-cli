#!/bin/bash
RESUME_FILE=$(./fuzzy-picker < /dev/tty)
echo "Captured: $RESUME_FILE"
