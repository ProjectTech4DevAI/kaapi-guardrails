# FastAPI Project - Backend

## Requirements

* [Docker](https://www.docker.com/).
* [uv](https://docs.astral.sh/uv/) for Python package and environment management.

## Docker Compose

Start the local development environment with Docker Compose following the guide in [../development.md](../development.md).

## General Workflow

By default, the dependencies are managed with [uv](https://docs.astral.sh/uv/), go there and install it.

From `./backend/` you can install all the dependencies with:

```console
$ uv sync
```

Then you can activate the virtual environment with:

```console
$ source .venv/bin/activate
```

Make sure your editor is using the correct Python virtual environment, with the interpreter at `backend/.venv/bin/python`.

Modify or add SQLModel models for data and SQL tables in `./backend/app/models/`, API endpoints in `./backend/app/api/`.

## VS Code

There are already configurations in place to run the backend through the VS Code debugger, so that you can use breakpoints, pause and explore variables, etc.

The setup is also already configured so you can run the tests through the VS Code Python tests tab.

There is also a command override that runs `fastapi run --reload` instead of the default `fastapi run`. It starts a single server process (instead of multiple, as would be for production) and reloads the process whenever the code changes. Have in mind that if you have a syntax error and save the Python file, it will break and exit, and the container will stop. After that, you can restart the container by fixing the error and running again:

```console
$ docker compose watch
```

There is also a commented out `command` override, you can uncomment it and comment the default one. It makes the backend container run a process that does "nothing", but keeps the container alive. That allows you to get inside your running container and execute commands inside, for example a Python interpreter to test installed dependencies, or start the development server that reloads when it detects changes.

To get inside the container with a `bash` session you can start the stack with:

```console
$ docker compose watch
```

and then in another terminal, `exec` inside the running container:

```console
$ docker compose exec backend bash
```

You should see an output like:

```console
root@7f2607af31c3:/app#
```

that means that you are in a `bash` session inside your container, as a `root` user, under the `/app` directory, this directory has another directory called "app" inside, that's where your code lives inside the container: `/app/app`.

There you can use the `fastapi run --reload` command to run the debug live reloading server.

```console
$ fastapi run --reload app/main.py
```

...it will look like:

```console
root@7f2607af31c3:/app# fastapi run --reload app/main.py
```

and then hit enter. That runs the live reloading server that auto reloads when it detects code changes.

Nevertheless, if it doesn't detect a change but a syntax error, it will just stop with an error. But as the container is still alive and you are in a Bash session, you can quickly restart it after fixing the error, running the same command ("up arrow" and "Enter").

...this previous detail is what makes it useful to have the container alive doing nothing and then, in a Bash session, make it run the live reload server.

## Backend tests

To test the backend run:

```console
$ bash ./scripts/test.sh
```

The tests run with Pytest, modify and add tests to `./backend/app/tests/`.

If you use GitHub Actions the tests will run automatically.

## Running evaluation tests

We can benchmark validators on curated datasets.

Download the dataset from [Google Drive](https://drive.google.com/drive/u/0/folders/1Rd1LH-oEwCkU0pBDRrYYedExorwmXA89).This contains multiple folders, one for each validator. Each folder contains a testing dataset in csv format for the validator. Download these csv files and store them in `backend/app/evaluation/datasets/`.

Important: each `run.py` expects a specific filename, so dataset files must be named exactly as below:
- `app/evaluation/lexical_slur/run.py` expects `lexical_slur_testing_dataset.csv`
- `app/evaluation/pii/run.py` expects `pii_detection_testing_dataset.csv`
- `app/evaluation/gender_assumption_bias/run.py` expects `gender_bias_assumption_dataset.csv`
- `app/evaluation/ban_list/run.py` expects `ban_list_testing_dataset.csv`

Once these files are in place with the exact names above, run the evaluation scripts.

Unit tests for lexical slur match, ban list, and gender assumption bias validators have limited value because their logic is deterministic. Curated datasets are used to benchmark accuracy and latency for lexical slur, gender assumption bias, and ban list. The lexical slur dataset will also be used in future toxicity detection workflows.

Each validator produces:
- predictions.csv – row-level outputs for debugging and analysis
- metrics.json – aggregated accuracy + performance metrics (latency and peak memory)

Standardized output structure:
```text
app/evaluation/outputs/
  lexical_slur/
    predictions.csv
    metrics.json
  gender_assumption_bias/
    predictions.csv
    metrics.json
  ban_list/
    predictions.csv
    metrics.json
  pii_remover/
    predictions.csv
    metrics.json
```

- To run all evaluation scripts together, use:
```bash
BAN_LIST_WORDS="word1,word2" bash scripts/run_all_evaluations.sh
```
or
```bash
bash scripts/run_all_evaluations.sh BAN_LIST_WORDS="word1,word2"
```

`BAN_LIST_WORDS` is required for the `ban_list` evaluator and should be a comma-separated list.

This script runs the evaluators in sequence:
- `app/evaluation/lexical_slur/run.py`
- `app/evaluation/pii/run.py`
- `app/evaluation/gender_assumption_bias/run.py`
- `app/evaluation/ban_list/run.py`

To evaluate any specific evaluator, run the offline evaluation script: `python <validator's eval script path>` 

## Validator configuration guide

Detailed validator configuration reference:
`backend/app/core/validators/README.md`

## API usage guide

Detailed API usage and end-to-end request examples:
`backend/app/api/API_USAGE.md`

### Test running stack

If your stack is already up and you just want to run the tests, you can use:

```bash
docker compose exec backend bash scripts/tests-start.sh
```

That `/app/scripts/tests-start.sh` script just calls `pytest` after making sure that the rest of the stack is running. If you need to pass extra arguments to `pytest`, you can pass them to that command and they will be forwarded.

For example, to stop on first error:

```bash
docker compose exec backend bash scripts/tests-start.sh -x
```

### Test Coverage

When the tests are run, a file `htmlcov/index.html` is generated, you can open it in your browser to see the coverage of the tests.

## Migrations

As during local development your app directory is mounted as a volume inside the container, you can also run the migrations with `alembic` commands inside the container and the migration code will be in your app directory (instead of being only inside the container). So you can add it to your git repository.

Make sure you create a "revision" of your models and that you "upgrade" your database with that revision every time you change them. As this is what will update the tables in your database. Otherwise, your application will have errors.

* Start an interactive session in the backend container:

```console
$ docker compose exec backend bash
```

* Alembic is configured with SQLModel models under `./backend/app/models/`.

* After changing a model (for example, adding a column), inside the container, create a revision, e.g.:

```console
$ alembic revision --autogenerate -m "Add column last_name to User model"
```

* Commit to the git repository the files generated in the alembic directory.

* After creating the revision, run the migration in the database (this is what will actually change the database):

```console
$ alembic upgrade head
```

If you don't want to use migrations at all, uncomment the lines in the file at `./backend/app/core/db.py` that end in:

```python
SQLModel.metadata.create_all(engine)
```

and comment the line in the file `scripts/prestart.sh` that contains:

```console
$ alembic upgrade head
```

If you don't want to start with the default models and want to remove them / modify them, from the beginning, without having any previous revision, you can remove the revision files (`.py` Python files) under `./backend/app/alembic/versions/`. And then create a first migration as described above.

# Guardrails AI

## Auth Token Configuration

`AUTH_TOKEN` must be the SHA-256 hex digest (64 lowercase hex characters) of the bearer token clients will send in the `Authorization: Bearer <token>` header.

Example to generate the digest:

```bash
echo -n "your-plain-text-token" | shasum -a 256
```

Set the resulting digest as `AUTH_TOKEN` in your `.env` / `.env.test`.

## Multi-tenant API Key Configuration

Ban List APIs use `X-API-KEY` auth instead of bearer token auth.

Required environment variables:
- `KAAPI_AUTH_URL`: Base URL of the Kaapi auth service used to verify API keys.
- `KAAPI_AUTH_TIMEOUT`: Timeout in seconds for auth verification calls.

At runtime, the backend calls:
- `GET {KAAPI_AUTH_URL}/apikeys/verify`
- Header: `X-API-KEY: ApiKey <token>`

If verification succeeds, tenant's scope (`organization_id`, `project_id`) is resolved from the auth response and applied to Ban List CRUD operations.

## Guardrails AI Setup
1. Ensure that the .env file contains the correct value from `GUARDRAILS_HUB_API_KEY`. The key can be fetched from [here](https://hub.guardrailsai.com/keys).

2. Make the `install_guardrails_from_hub.sh` script executable using this command (run this from the `backend` folder) -

```bash
chmod +x scripts/install_guardrails_from_hub.sh
```
3. Run this command to configure Guardrails AI -

```bash
scripts/install_guardrails_from_hub.sh;        
```

### Alternate Method
Run the following commands inside your virtual environment:

```bash
uv sync
guardrails configure

Enable anonymous metrics reporting? [Y/n]: Y
Do you wish to use remote inferencing? [Y/n]: Y
Enter API Key below leave empty if you want to keep existing token [HBPo]
👉 You can find your API Key at https://hub.guardrailsai.com/keys
```

To install any validator from Guardrails Hub:
```bash
guardrails hub install hub://guardrails/<validator-name>

Example -
guardrails hub install hub://guardrails/ban_list
```

## Adding a new validator from Guardrails Hub
To add a new validator from the Guardrails Hub to this project, follow the steps below.

1. In the `backend/app/core/validators/config` folder, create a new Python file called `<validator_name>_safety_validator_config.py`. Add the following code there:

```python
from guardrails.hub import # validator name from Guardrails Hub
from typing import List, Literal

from app.core.validators.config.base_validator_config import BaseValidatorConfig

class <Validator-name>SafetyValidatorConfig(BaseValidatorConfig):
    type: Literal["<validator-name>"]
    banned_words: List[str]

    # This method returns the validator constructor.
    def build(self):
```

For example, this is the code for [BanList validator](https://guardrailsai.com/hub/validator/guardrails/ban_list).

```python
from guardrails.hub import BanList
from typing import List, Literal

from app.core.validators.config.base_validator_config import BaseValidatorConfig


class BanListSafetyValidatorConfig(BaseValidatorConfig):
    type: Literal["ban_list"]
    banned_words: List[str]

    def build(self):
        return BanList(
            banned_words=self.banned_words,
            on_fail=self.resolve_on_fail(),
        )

```

2. In `backend/app/schemas/guardrail_config.py`, add the newly created config class to `ValidatorConfigItem`.

## How to add custom validators?
To add a custom validator to this project, follow the steps below.

1. Create the custom validator class. Take a look at the `backend/app/core/validators/gender_assumption_bias.py` as an example. Each custom validator should contain an `__init__` and `_validator` method. For example,

```python
from guardrails import OnFailAction
from guardrails.validators import (
    FailResult,
    PassResult,
    register_validator,
    ValidationResult,
    Validator
)
from typing import Callable, List, Optional

@register_validator(name="<validator-name>", data_type="string")
class <Validator-Name>(Validator):

    def __init__(
        self,
        # any parameters required while initializing the validator 
        on_fail: Optional[Callable] = OnFailAction.FIX #can be changed
    ):
        # Initialize the required variables
        super().__init__(on_fail=on_fail)

    def _validate(self, value: str, metadata: dict = None) -> ValidationResult:
        # add logic for validation
```

2. In the `backend/app/core/validators/config` folder, create a new Python file called `<validator_name>_safety_validator_config.py`. Add the following code there:

```python
from typing import List, Literal

from app.core.validators.config.base_validator_config import BaseValidatorConfig

class <Validator-name>SafetyValidatorConfig(BaseValidatorConfig):
    type: Literal["<validator-name>"]
    banned_words: List[str]

    # This method returns the validator constructor.
    def build(self):
```

For example, this is the code for GenderAssumptionBias validator.

```python
from typing import ClassVar, List, Literal, Optional
from app.core.validators.config.base_validator_config import BaseValidatorConfig
from app.core.enum import BiasCategories
from app.core.validators.gender_assumption_bias import GenderAssumptionBias

class GenderAssumptionBiasSafetyValidatorConfig(BaseValidatorConfig):
    type: Literal["gender_assumption_bias"]
    categories: Optional[List[BiasCategories]] = [BiasCategories.All]

    def build(self):
        return GenderAssumptionBias(
            categories=self.categories,
            on_fail=self.resolve_on_fail(),
        )
```

3. In `backend/app/schemas/guardrail_config.py`, add the newly created config class to `ValidatorConfigItem`.
