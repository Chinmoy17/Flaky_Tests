FROM maven:3.9-eclipse-temurin-11

# git is needed to fetch target projects at a specific SHA.
# jq is needed to trim flaky-lists.json for the mini "minimize" runner.
RUN apt-get update \
 && apt-get install -y --no-install-recommends git jq \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /work
COPY run-idflakies.sh /usr/local/bin/run-idflakies
COPY run-idflakies-minimize.sh /usr/local/bin/run-idflakies-minimize
# Strip any CRLF (in case the scripts are checked out on Windows) and make them executable.
RUN sed -i 's/\r$//' /usr/local/bin/run-idflakies /usr/local/bin/run-idflakies-minimize \
 && chmod +x /usr/local/bin/run-idflakies /usr/local/bin/run-idflakies-minimize

# Args: <repo-url> <sha> <module> [rounds] [detector-type]
ENTRYPOINT ["run-idflakies"]
