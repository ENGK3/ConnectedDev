docker run --rm -it --name dey-4.0-container \
                   --security-opt seccomp=unconfined \
                   --volume $HOST_ABSOLUTE_PATH_TO_WORKSPACE:/home/dey/workspace \
                   digidotcom/dey:dey-4.0 bash
