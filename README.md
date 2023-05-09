## CloneGuard
### Monitoring and Reporting Tool for Cloned Vulnerabilities across Open-Source Projects
CloneGuard is a tool for detecting cloned vulnerabilities in open-source projects. To monitor or detect
cloned vulnerabilities in a project, it is required to register it in the internal database of the tool first.
Then, CloneGuard offers two modes for analysis of the project:

#### Targeted Detection
Runs a detection of a specific vulnerability in forked projects.

#### Discovery Scan
Scans the recent updates in watched parent projects for suspicious commits.

---

### Installation
CloneGuard consists of multiple services. To run them, you need to install Docker and Docker Compose.

* `docker-compose build` - build all services

---

### Usage
#### Prerequisites
Initialize environment variables in `.env` file:
* `GITHUB_API_ACCESS_TOKEN` - GitHub personal access token (see [GitHub Docs](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/creating-a-personal-access-token))
* `SMTP_LOGIN` - SMTP login for sending email notifications
* `SMTP_PASSWORD` - SMTP password for sending email notifications

#### Initialize the database
* `docker-compose run db` - start DB
* `docker-compose exec db sh` - connect to the container
* `pg_restore -U admin -W -d postgres -F t db_data/dump.tar` - run in the container, initialize DB with data from experimentation (use pass: postgres)

or

* `docker-compose run worker ./cli db-init` - initialize DB schema - fresh instance

#### Start up
* `docker-compose up` - start all services
* `docker-compose exec worker ./cli --help` - access CLI

#### Services
* `web` - web interface, available at `http://localhost:3000`
* `api` - API for web interface, available at `http://localhost:8000`
* `worker` - worker for processing tasks
* `db` - internal database
* `redis` - internal message broker

---

### External dependencies
#### Simian
Simian (Similarity Analyzer) is a tool for detecting code duplicates. CloneGuard uses it to find vulnerable
code clones in forked projects. Simian is written in Java and requires Java 8 or higher to run (installed in
the docker image).

Download [here](https://repo1.maven.org/maven2/com/github/jiangxincode/simian/2.5.10/).
