# Usage:
#
# make config=/path/to/config.yaml			# Build and deploy with config
# make build config=/path/to/config.yaml	# Build and push images, compile jinja templates
# make deploy config=/path/to/config.yaml	# Deploy docker-compose
#
#
# The following don't have any arguments.
#
# make setup-ubuntu		# Install some prereq software (not including docker) on ubuntu
# make setup-ec2		# Install some prereq software (not including docker) on Amazon Linux 2 EC2
# make check			# Display `docker ps`
# make clean			# Take down docker-compose and prune local images
# make local-registry	# Make image registry on localhost 
# make help				# Reminder of options 
#

all: build deploy

help:
	@echo Please select: setup-ubuntu, setup-ec2, build, deploy, check, clean, local-registry, logs, revert, prune

setup-ubuntu:
	@bash makes/setup-ubuntu.sh

setup-ec2:
	@bash makes/setup-ec2.sh

build:
	cp ${config} labs.run.yaml
	@bash makes/build.sh

deploy:
	@bash makes/deploy.sh

check:
	@docker ps

clean:
	@bash makes/clean.sh

local-registry:
	docker run -d -p 5000:5000 --restart=always --name registry registry:2

logs:
	cd services && docker compose logs -f

revert:
	@bash makes/revert.sh

prune:
	@bash makes/prune.sh
