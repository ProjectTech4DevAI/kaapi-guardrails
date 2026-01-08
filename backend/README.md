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

The tests run with Pytest, modify and add tests to `./backend/tests/`.

If you use GitHub Actions the tests will run automatically.

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

* Alembic is already configured to import your SQLModel models from `./backend/app/models.py`.

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

## Guardrails AI Setup
1. Ensure that the .env.example file contains the correct value from `GUARDRAILS_HUB_API_KEY`. The key can be fetched from [here](https://hub.guardrailsai.com/keys).

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
```
guardrails hub install hub://guardrails/<validator-name>

Example -
guardrails hub install hub://guardrails/ban_list
```

## Adding a new validator from Guardrails Hub
To add a new validator from the Guardrails Hub to this project, follow the steps below.

1. In the `backend/app/models` folder, create a new Python file called `<validator_name>_safety_validator_config.py`. Add the following code there:

```
from guardrails.hub import # validator name from Guardrails Hub
from typing import List, Literal

from app.models.base_validator_config import BaseValidatorConfig

class <Validator-name>SafetyValidatorConfig(BaseValidatorConfig):
    type: Literal["<validator-name>"]
    banned_words: List[str]

    # This method returns the validator constructor.
    def build(self):
```

For example, this is the code for [BanList validator](https://guardrailsai.com/hub/validator/guardrails/ban_list).

```
from guardrails.hub import BanList
from typing import List, Literal

from app.models.base_validator_config import BaseValidatorConfig


class BanListSafetyValidatorConfig(BaseValidatorConfig):
    type: Literal["ban_list"]
    banned_words: List[str]

    def build(self):
        return BanList(
            banned_words=self.banned_words,
            on_fail=self.resolve_on_fail(),
        )

```

2. In `backend/app/guardrail_config.py`, add the newly created config class to `ValidatorConfigItem`.

## How to add custom validators?
To add a custom validator to this project, follow the steps below.

1. Create the custom validator class. Take a look at the `backend/app/core/validators/gender_assumption_bias.py` as an example. Each custom validator should contain an `__init__` and `_validator` method. For example,

```
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

2. In the `backend/app/models` folder, create a new Python file called `<validator_name>_safety_validator_config.py`. Add the following code there:

```
from typing import List, Literal

from app.models.base_validator_config import BaseValidatorConfig

class <Validator-name>SafetyValidatorConfig(BaseValidatorConfig):
    type: Literal["<validator-name>"]
    banned_words: List[str]

    # This method returns the validator constructor.
    def build(self):
```

For example, this is the code for GenderAssumptionBias validator.

```
from typing import ClassVar, List, Literal, Optional
from app.models.base_validator_config import BaseValidatorConfig
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

2. In `backend/app/guardrail_config.py`, add the newly created config class to `ValidatorConfigItem`.
