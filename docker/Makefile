VERSION := $(shell git rev-parse HEAD)
TAG := docker.mujin.co.jp/jhbuild/jhbuild:${VERSION}

.PHONY: all
all: build

.PHONY: build
build:
	@set -e; \
	T=$$(mktemp -d); \
	echo "Building docker image in $$T ..."; \
	cat Dockerfile | sed 's/{{VERSION}}/${VERSION}/g' > $$T/Dockerfile; \
	rsync -a entrypoint.sh $$T/ && \
	docker build -t ${TAG} $$T; \
	rm -rf $$T

.PHONY: push
push: build
	docker push ${TAG}
