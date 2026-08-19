FROM maven:3.9-eclipse-temurin-11

# git is needed to fetch target projects at a specific SHA.
RUN apt-get update \
 && apt-get install -y --no-install-recommends git \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /work
COPY run-idflakies.sh /usr/local/bin/run-idflakies
# Strip any CRLF (in case the script is checked out on Windows) and make it executable.
RUN sed -i 's/\r$//' /usr/local/bin/run-idflakies && chmod +x /usr/local/bin/run-idflakies

# Args: <repo-url> <sha> <module> [rounds] [detector-type]
ENTRYPOINT ["run-idflakies"]
