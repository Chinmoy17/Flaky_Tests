FROM maven:3.9-eclipse-temurin-11

# git is needed to fetch target projects at a specific SHA.
# NonDex 2.2.1 requires JDK 9+ (JDK 8 fails with "Unrecognized option: --add-exports"),
# which is why this base image is JDK 11.
RUN apt-get update \
 && apt-get install -y --no-install-recommends git \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /work
COPY run-nondex.sh /usr/local/bin/run-nondex
# Strip any CRLF (in case the script is checked out on Windows) and make it executable.
RUN sed -i 's/\r$//' /usr/local/bin/run-nondex && chmod +x /usr/local/bin/run-nondex

# Args: <repo-url> <sha> <module> <test-filter> [nondex-version]
ENTRYPOINT ["run-nondex"]
