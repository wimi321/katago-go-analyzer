#!/bin/bash
python3 full_pipeline.py "$1" > pipeline_output.log 2> pipeline_error.log
echo $? > pipeline_exit_code.log